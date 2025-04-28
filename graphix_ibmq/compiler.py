import numpy as np
from qiskit import ClassicalRegister, QuantumRegister, QuantumCircuit

from graphix_ibmq.clifford import CLIFFORD_TO_QISKIT
from graphix.pattern import Pattern
from graphix.command import CommandKind
from graphix.fundamentals import Plane


class IBMQPatternCompiler:
    """Compiler that translates a Graphix Pattern into a Qiskit QuantumCircuit."""

    def __init__(self, pattern: Pattern) -> None:
        """
        Initialize the compiler with a given pattern.

        Parameters
        ----------
        pattern : Pattern
            The measurement-based quantum computation pattern.
        """
        self._pattern = pattern
        self._register_dict: dict[int, int] = {}
        self._circ_output: list[int] = []

    def to_qiskit_circuit(
        self, save_statevector: bool, layout_method: str
    ) -> QuantumCircuit:
        """
        Convert the MBQC pattern into a Qiskit QuantumCircuit.

        Parameters
        ----------
        save_statevector : bool
            Whether to save the statevector before output measurement (for testing).
        layout_method : str
            (Currently unused) Layout method for mapping.

        Returns
        -------
        QuantumCircuit
            The compiled Qiskit circuit.
        """
        n = self._pattern.max_space()
        N_node = self._pattern.n_node

        qr = QuantumRegister(n)
        cr = ClassicalRegister(N_node, name="meas")
        circ = QuantumCircuit(qr, cr)

        empty_qubit = list(range(n))  # available qubit indices
        qubit_dict: dict[int, int] = {}  # pattern node -> circuit qubit
        register_dict: dict[int, int] = {}  # pattern node -> classical register
        reg_idx = 0

        def signal_process(op: str, circ_idx: int, signal: list[int]) -> None:
            """Apply classically-controlled X or Z gates based on measurement outcomes."""
            if op == "X":
                for s in signal:
                    if s in register_dict:
                        s_idx = register_dict[s]
                        with circ.if_test((cr[s_idx], 1)):
                            circ.x(circ_idx)
                    else:
                        if self._pattern.results[s] == 1:
                            circ.x(circ_idx)
            if op == "Z":
                for s in signal:
                    if s in register_dict:
                        s_idx = register_dict[s]
                        with circ.if_test((cr[s_idx], 1)):
                            circ.z(circ_idx)
                    else:
                        if self._pattern.results[s] == 1:
                            circ.z(circ_idx)

        # Prepare input qubits
        for i in self._pattern.input_nodes:
            circ_idx = empty_qubit.pop(0)
            circ.reset(circ_idx)
            circ.h(circ_idx)
            qubit_dict[i] = circ_idx

        # Compile pattern commands
        for cmd in self._pattern:
            if cmd.kind == CommandKind.N:
                circ_idx = empty_qubit.pop(0)
                circ.reset(circ_idx)
                circ.h(circ_idx)
                qubit_dict[cmd.node] = circ_idx

            elif cmd.kind == CommandKind.E:
                circ.cz(qubit_dict[cmd.nodes[0]], qubit_dict[cmd.nodes[1]])

            elif cmd.kind == CommandKind.M:
                circ_idx = qubit_dict[cmd.node]
                plane = cmd.plane
                alpha = cmd.angle * np.pi
                s_list = cmd.s_domain
                t_list = cmd.t_domain

                if plane == Plane.XY:
                    if alpha != 0:
                        signal_process("X", circ_idx, s_list)
                        circ.p(-alpha, circ_idx)
                    signal_process("Z", circ_idx, t_list)
                    circ.h(circ_idx)
                    circ.measure(circ_idx, reg_idx)
                    register_dict[cmd.node] = reg_idx
                    reg_idx += 1
                    empty_qubit.append(circ_idx)
                else:
                    raise NotImplementedError("Non-XY plane is not supported.")

            elif cmd.kind == CommandKind.X:
                circ_idx = qubit_dict[cmd.node]
                s_list = cmd.domain
                signal_process("X", circ_idx, s_list)

            elif cmd.kind == CommandKind.Z:
                circ_idx = qubit_dict[cmd.node]
                s_list = cmd.domain
                signal_process("Z", circ_idx, s_list)

            elif cmd.kind == CommandKind.C:
                circ_idx = qubit_dict[cmd.node]
                cid = cmd.clifford
                for op in CLIFFORD_TO_QISKIT[cid]:
                    exec(f"circ.{op}({circ_idx})")

        # Handle output measurements
        if save_statevector:
            circ.save_statevector()
            output_qubit: list[int] = []
            for node in self._pattern.output_nodes:
                circ_idx = qubit_dict[node]
                circ.measure(circ_idx, reg_idx)
                register_dict[node] = reg_idx
                reg_idx += 1
                output_qubit.append(circ_idx)
            self._circ_output = output_qubit
        else:
            for node in self._pattern.output_nodes:
                circ_idx = qubit_dict[node]
                circ.measure(circ_idx, reg_idx)
                register_dict[node] = reg_idx
                reg_idx += 1

        self._register_dict = register_dict
        return circ
