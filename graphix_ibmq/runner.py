import numpy as np
from qiskit_ibm_provider import IBMProvider
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit import transpile
from qiskit.providers.ibmq import least_busy
from graphix.clifford import CLIFFORD_CONJ


class IBMQBackend:
    """runs MBQC pattern with IBM quantum device."""

    def __init__(self, pattern):
        """
        Parameteres
        -----------
        pattern: :class:`graphix.pattern.Pattern` object
            MBQC pattern to be executed.
        """
        self.pattern = pattern

    def get_backend(self, instance="ibm-q/open/main", resource=None):
        """get the backend object
        Parameteres
        -----------
        instance : str
            instance name of IBMQ provider.
        resource : str
            resource name of IBMQ provider.
        """
        self.instance = instance
        self.provider = IBMProvider(instance=self.instance)
        if resource is not None:
            self.resource = resource
            self.backend = self.provider.get_backend(self.resource)
        else:
            self.backend = least_busy(
                self.provider.backends(
                    filters=lambda b: b.configuration().n_qubits >= 1
                    and not b.configuration().simulator
                    and b.status().operational == True
                )
            )
            self.resource = self.backend.name
        print(f"Using backend {self.backend.name}")

    def to_qiskit(self, save_statevector=False):
        """convert the MBQC pattern to the qiskit cuicuit and add to attributes.
        Parameteres
        -----------
        pattern : :class:`graphix.pattern.Pattern` object
            MBQC pattern to be converted to qiskit circuit.
        save_statevector (False) : bool, optional
            whether to save the statevector before the measurements of output qubits.
        """
        n = self.pattern.max_space()
        N_node = self.pattern.Nnode

        qr = QuantumRegister(n)
        cr = ClassicalRegister(N_node)
        circ = QuantumCircuit(qr, cr)

        empty_qubit = [i for i in range(n)]  # list indicating the free circuit qubits
        qubit_dict = {}  # dictionary to record the correspondance of pattern nodes and circuit qubits

        for cmd in self.pattern.seq:

            if cmd[0] == "N":
                circ_ind = empty_qubit[0]
                empty_qubit.pop(0)
                circ.reset(circ_ind)
                circ.h(circ_ind)
                qubit_dict[cmd[1]] = circ_ind

            if cmd[0] == "E":
                circ.cz(qubit_dict[cmd[1][0]], qubit_dict[cmd[1][1]])

            if cmd[0] == "M":
                circ_ind = qubit_dict[cmd[1]]
                plane = cmd[2]
                alpha = cmd[3] * np.pi
                s_list = cmd[4]
                t_list = cmd[5]

                if len(cmd) == 6:
                    if plane == "XY":
                        # act p and h to implement non-Z-basis measurement
                        if alpha != 0:
                            for s in s_list:  # act x every time 1 comes in the s_list
                                with circ.if_test((cr[s], 1)):
                                    circ.x(circ_ind)
                            circ.p(-alpha, circ_ind)  # align |+_alpha> (or |+_-alpha>) with |+>

                        for t in t_list:  # act z every time 1 comes in the t_list
                            with circ.if_test((cr[t], 1)):
                                circ.z(circ_ind)

                        circ.h(circ_ind)  # align |+> with |0>

                        circ.measure(circ_ind, cmd[1])  # measure and store the result
                        empty_qubit.append(circ_ind)  # liberate the circuit qubit

                elif len(cmd) == 7:
                    cid = cmd[6]
                    for op in CLIFFORD_TO_QISKIT[CLIFFORD_CONJ[cid]]:
                        exec(f"circ.{op}({circ_ind})")

                    if plane == "XY":
                        # act p and h to implement non-Z-basis measurement
                        if alpha != 0:
                            for s in s_list:  # act x every time 1 comes in the s_list
                                with circ.if_test((cr[s], 1)):
                                    circ.x(circ_ind)
                            circ.p(-alpha, circ_ind)  # align |+_alpha> (or |+_-alpha>) with |+>

                        for t in t_list:  # act z every time 1 comes in the t_list
                            with circ.if_test((cr[t], 1)):
                                circ.z(circ_ind)

                        circ.h(circ_ind)  # align |+> with |0>

                        circ.measure(circ_ind, cmd[1])  # measure and store the result
                        empty_qubit.append(circ_ind)  # liberate the circuit qubit

            if cmd[0] == "X":
                circ_ind = qubit_dict[cmd[1]]
                s_list = cmd[2]
                for s in s_list:
                    with circ.if_test((cr[s], 1)):
                        circ.x(circ_ind)

            if cmd[0] == "Z":
                circ_ind = qubit_dict[cmd[1]]
                s_list = cmd[2]
                for s in s_list:
                    with circ.if_test((cr[s], 1)):
                        circ.z(circ_ind)

            if cmd[0] == "C":
                circ_ind = qubit_dict[cmd[1]]
                cid = cmd[2]
                for op in CLIFFORD_TO_QISKIT[cid]:
                    exec(f"circ.{op}({circ_ind})")

        if save_statevector:
            circ.save_statevector()
            output_qubit = []
            for node in self.pattern.output_nodes:
                circ_ind = qubit_dict[node]
                circ.measure(circ_ind, node)
                output_qubit.append(circ_ind)

            self.circ = circ
            self.circ_output = output_qubit

        else:
            for node in self.pattern.output_nodes:
                circ_ind = qubit_dict[node]
                circ.measure(circ_ind, node)

            self.circ = circ

    def transpile(self, optimization_level=1):
        """transpile the circuit for the designated resource.
        Parameteres
        -----------
        optimization_level (1) : int, optional
            the optimization level of the transpilation.
        """
        self.circ = transpile(self.circ, backend=self.backend, optimization_level=optimization_level)


CLIFFORD_TO_QISKIT = [
    ["id"],
    ["x"],
    ["y"],
    ["z"],
    ["s"],
    ["sdg"],
    ["h"],
    ["sdg", "h", "sdg"],
    ["h", "x"],
    ["sdg", "y"],
    ["sdg", "x"],
    ["h", "y"],
    ["h", "z"],
    ["sdg", "h", "sdg", "y"],
    ["sdg", "h", "s"],
    ["sdg", "h", "sdg", "x"],
    ["sdg", "h"],
    ["sdg", "h", "y"],
    ["sdg", "h", "z"],
    ["sdg", "h", "x"],
    ["h", "s"],
    ["h", "sdg"],
    ["h", "x", "sdg"],
    ["h", "x", "s"],
]
