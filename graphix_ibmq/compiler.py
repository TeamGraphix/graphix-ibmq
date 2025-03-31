import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from graphix_ibmq.clifford import CLIFFORD_CONJ, CLIFFORD_TO_QISKIT
from graphix.pattern import Pattern
from graphix.command import CommandKind
from graphix.fundamentals import Plane

class IBMQPatternCompiler:
    def __init__(self, pattern: Pattern):
        self.pattern = pattern
        self.register_dict = {}

    def to_qiskit_circuit(self, save_statevector: bool, layout_method: str):
        from qiskit import QuantumCircuit
        """convert the MBQC pattern to the qiskit cuicuit and add to attributes.

        Parameters
        ----------
        save_statevector : bool, optional
            whether to save the statevector before the measurements of output qubits.
        """
        n = self.pattern.max_space()
        N_node = self.pattern.n_node

        qr = QuantumRegister(n)
        cr = ClassicalRegister(N_node)
        circ = QuantumCircuit(qr, cr)

        empty_qubit = [i for i in range(n)]  # list of free qubit indices
        qubit_dict = {}  # dictionary to record the correspondance of pattern nodes and circuit qubits
        register_dict = {}  # dictionary to record the correspondance of pattern nodes and classical registers
        reg_idx = 0  # index of classical register

        def signal_process(op, circ_idx, signal):
            if op == "X":
                for s in signal:
                    if s in register_dict.keys():
                        s_idx = register_dict[s]
                        with circ.if_test((cr[s_idx], 1)):
                            circ.x(circ_idx)
                    else:
                        if self.pattern.results[s] == 1:
                            circ.x(circ_idx)
            if op == "Z":
                for s in signal:
                    if s in register_dict.keys():
                        s_idx = register_dict[s]
                        with circ.if_test((cr[s_idx], 1)):
                            circ.z(circ_idx)
                    else:
                        if self.pattern.results[s] == 1:
                            circ.z(circ_idx)

        for i in self.pattern.input_nodes:
            circ_idx = empty_qubit[0]
            empty_qubit.pop(0)
            circ.reset(circ_idx)
            circ.h(circ_idx)
            qubit_dict[i] = circ_idx

        for cmd in self.pattern:

            if cmd.kind == CommandKind.N:
                circ_idx = empty_qubit[0]
                empty_qubit.pop(0)
                circ.reset(circ_idx)
                circ.h(circ_idx)
                qubit_dict[cmd.node] = circ_idx

            if cmd.kind == CommandKind.E:
                circ.cz(qubit_dict[cmd.nodes[0]], qubit_dict[cmd.nodes[1]])

            if cmd.kind == CommandKind.M:
                circ_idx = qubit_dict[cmd.node]
                plane = cmd.plane
                alpha = cmd.angle * np.pi
                s_list = cmd.s_domain
                t_list = cmd.t_domain

                if plane == Plane.XY:
                    # act p and h to implement non-Z-basis measurement
                    if alpha != 0:
                        signal_process("X", circ_idx, s_list)
                        circ.p(-alpha, circ_idx)  # align |+_alpha> (or |+_-alpha>) with |+>

                    signal_process("Z", circ_idx, t_list)

                    circ.h(circ_idx)  # align |+> with |0>
                    circ.measure(circ_idx, reg_idx)  # measure and store the result
                    register_dict[cmd.node] = reg_idx
                    reg_idx += 1
                    empty_qubit.append(circ_idx)  # liberate the circuit qubit

                else:
                    raise NotImplementedError("Non-XY plane is not supported.")

            if cmd.kind == CommandKind.X:
                circ_idx = qubit_dict[cmd.node]
                s_list = cmd.domain
                signal_process("X", circ_idx, s_list)

            if cmd.kind == CommandKind.Z:
                circ_idx = qubit_dict[cmd.node]
                s_list = cmd.domain
                signal_process("Z", circ_idx, s_list)

            if cmd.kind == CommandKind.C:
                circ_idx = qubit_dict[cmd.node]
                cid = cmd.clifford
                for op in CLIFFORD_TO_QISKIT[cid]:
                    exec(f"circ.{op}({circ_idx})")

        if save_statevector:
            circ.save_statevector()
            output_qubit = []
            for node in self.pattern.output_nodes:
                circ_idx = qubit_dict[node]
                circ.measure(circ_idx, reg_idx)
                register_dict[node] = reg_idx
                reg_idx += 1
                output_qubit.append(circ_idx)

            # self.circ_output = output_qubit

        else:
            for node in self.pattern.output_nodes:
                circ_idx = qubit_dict[node]
                circ.measure(circ_idx, reg_idx)
                register_dict[node] = reg_idx
                reg_idx += 1

            self.register_dict = register_dict
            # self.circ = circ

        return circ