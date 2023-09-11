import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_ibm_provider import IBMProvider, least_busy
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from graphix_ibmq.clifford import (
    CLIFFORD_CONJ,
    CLIFFORD_TO_QISKIT,
)


class IBMQBackend:
    """Interface for MBQC pattern execution on IBM quantum devices.

    Attributes
    ----------
    pattern: :class:`graphix.pattern.Pattern` object
        MBQC pattern to be run on the device
    circ: :class:`qiskit.circuit.quantumcircuit.QuantumCircuit` object
        qiskit circuit corresponding to the pattern.
    job: :class:`qiskit_ibm_provider.job.ibm_circuit_job.IBMCircuitJob` object
        job object of the execution.
    instance : str
        instance name of IBMQ provider.
    resource : str
        resource name of IBMQ provider.
    backend : :class:`qiskit_ibm_provider.ibm_backend.IBMBackend` object
        IBMQ device backend
    """

    def __init__(self, pattern):
        """

        Parameters
        ----------
        pattern: :class:`graphix.pattern.Pattern` object
            MBQC pattern to be run on the IBMQ device or Aer simulator.
        """
        self.pattern = pattern

    def get_backend(self, instance="ibm-q/open/main", resource=None):
        """get the backend object

        Parameters
        ----------
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
                    filters=lambda b: b.configuration().n_qubits >= self.pattern.max_space()
                    and not b.configuration().simulator
                    and b.status().operational == True
                )
            )
            self.resource = self.backend.name
        print(f"Using backend {self.backend.name}")

    def to_qiskit(self, save_statevector=False):
        """convert the MBQC pattern to the qiskit cuicuit and add to attributes.

        Parameters
        ----------
        pattern : :class:`graphix.pattern.Pattern` object
            MBQC pattern to be converted to qiskit circuit.
        save_statevector : bool, optional
            whether to save the statevector before the measurements of output qubits.
        """
        n = self.pattern.max_space()
        N_node = self.pattern.Nnode

        qr = QuantumRegister(n)
        cr = ClassicalRegister(N_node)
        circ = QuantumCircuit(qr, cr)

        empty_qubit = [i for i in range(n)]  # list of free qubit indices
        qubit_dict = {}  # dictionary to record the correspondance of pattern nodes and circuit qubits
        register_dict = {}  # dictionary to record the correspondance of pattern nodes and classical registers
        reg_idx = 0  # index of classical register

        def signal_process(op, signal):
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

        for cmd in self.pattern.seq:

            if cmd[0] == "N":
                circ_idx = empty_qubit[0]
                empty_qubit.pop(0)
                circ.reset(circ_idx)
                circ.h(circ_idx)
                qubit_dict[cmd[1]] = circ_idx

            if cmd[0] == "E":
                circ.cz(qubit_dict[cmd[1][0]], qubit_dict[cmd[1][1]])

            if cmd[0] == "M":
                circ_idx = qubit_dict[cmd[1]]
                plane = cmd[2]
                alpha = cmd[3] * np.pi
                s_list = cmd[4]
                t_list = cmd[5]

                if len(cmd) == 6:
                    if plane == "XY":
                        # act p and h to implement non-Z-basis measurement
                        if alpha != 0:
                            signal_process("X", s_list)
                            circ.p(-alpha, circ_idx)  # align |+_alpha> (or |+_-alpha>) with |+>

                        signal_process("Z", t_list)

                        circ.h(circ_idx)  # align |+> with |0>
                        circ.measure(circ_idx, reg_idx)  # measure and store the result
                        register_dict[cmd[1]] = reg_idx
                        reg_idx += 1
                        empty_qubit.append(circ_idx)  # liberate the circuit qubit

                elif len(cmd) == 7:
                    cid = cmd[6]
                    for op in CLIFFORD_TO_QISKIT[CLIFFORD_CONJ[cid]]:
                        exec(f"circ.{op}({circ_idx})")

                    if plane == "XY":
                        # act p and h to implement non-Z-basis measurement
                        if alpha != 0:
                            signal_process("X", s_list)
                            circ.p(-alpha, circ_idx)  # align |+_alpha> (or |+_-alpha>) with |+>

                        signal_process("Z", t_list)

                        circ.h(circ_idx)  # align |+> with |0>
                        circ.measure(circ_idx, reg_idx)  # measure and store the result
                        register_dict[cmd[1]] = reg_idx
                        reg_idx += 1
                        circ.measure(circ_idx, reg_idx)  # measure and store the result
                        empty_qubit.append(circ_idx)  # liberate the circuit qubit

            if cmd[0] == "X":
                circ_idx = qubit_dict[cmd[1]]
                s_list = cmd[2]
                signal_process("X", s_list)

            if cmd[0] == "Z":
                circ_idx = qubit_dict[cmd[1]]
                s_list = cmd[2]
                signal_process("Z", s_list)

            if cmd[0] == "C":
                circ_idx = qubit_dict[cmd[1]]
                cid = cmd[2]
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

            self.circ = circ
            self.circ_output = output_qubit

        else:
            for node in self.pattern.output_nodes:
                circ_idx = qubit_dict[node]
                circ.measure(circ_idx, reg_idx)
                register_dict[node] = reg_idx
                reg_idx += 1

            self.register_dict = register_dict
            self.circ = circ

    def set_input(self, psi):
        """set the input state of the circuit.
        The input states are set to the circuit qubits corresponding to the first n nodes prepared in the pattern.

        Parameters
        ----------
        psi : list of list of complex
            list of the input states for each input.
            Each input state is a list of complex of length 2, representing the coefficient of |0> and |1>.
        """
        n = len(self.pattern.output_nodes)
        input_order = {}
        idx = 0
        for cmd in self.pattern.seq:
            if cmd[0] == "N":
                if cmd[1] < n:
                    input_order[idx] = cmd[1]
                idx += 1
            if len(input_order) == n:
                break

        idx = 0
        for k, ope in enumerate(self.circ.data):
            if ope[0].name == "reset":
                if idx in input_order.keys():
                    qubit_idx = ope[1][0].index
                    i = input_order[idx]
                    self.circ.initialize(psi[i], qubit_idx)
                    self.circ.data[k + 1] = self.circ.data.pop(-1)
                idx += 1
            if idx >= max(input_order.keys()) + 1:
                break

    def transpile(self, backend=None, optimization_level=1):
        """transpile the circuit for the designated resource.

        Parameters
        ----------
        backend : :class:`qiskit_ibm_provider.ibm_backend.IBMBackend` object, optional
            backend to be used for transpilation.
        optimization_level : int, optional
            the optimization level of the transpilation.
        """
        if backend is None:
            backend = self.backend
        self.circ = transpile(self.circ, backend=backend, optimization_level=optimization_level)

    def simulate(self, shots=1024, noise_model=None, format_result=True):
        """simulate the circuit with Aer.

        Parameters
        ----------
        shots : int, optional
            the number of shots.
        noise_model : :class:`qiskit_aer.backends.aer_simulator.AerSimulator` object, optional
            noise model to be used in the simulation.
        format_result : bool, optional
            whether to format the result so that only the result corresponding to the output qubit is taken out.

        Returns
        ----------
        result : dict
            the measurement result.
        """
        if noise_model is not None:
            if type(noise_model) is NoiseModel:
                simulator = AerSimulator(noise_model=noise_model)
            else:
                simulator = AerSimulator.from_backend(noise_model)
        else:
            simulator = AerSimulator()
        circ_sim = transpile(self.circ, simulator)
        result = simulator.run(circ_sim, shots=shots).result()
        if format_result:
            result = self.format_result(result)

        return result

    def run(self, shots=1024, format_result=True, optimization_level=1):
        """Run the MBQC pattern on IBMQ devices

        Parameters
        ----------
        shots : int, optional
            the number of shots.
        format_result : bool, optional
            whether to format the result so that only the result corresponding to the output qubit is taken out.
        optimization_level : int, optional
            the optimization level of the transpilation.

        Returns
        -------
        result : dict
            the measurement result.
        """
        self.transpile(optimization_level=optimization_level)
        self.job = self.backend.run(self.circ, shots=shots, dynamic=True)
        print(f"Your job's id: {self.job.job_id()}")
        result = self.job.result()
        if format_result:
            result = self.format_result(result)

        return result

    def format_result(self, result):
        """Format the result so that only the result corresponding to the output qubit is taken out.

        Returns
        -------
        masked_results : dict
            Dictionary of formatted results.
        """
        masked_results = {}
        N_node = self.pattern.Nnode

        # Iterate over original measurement results
        for key, value in result.get_counts().items():
            masked_key = ""
            for idx in self.pattern.output_nodes:
                reg_idx = self.register_dict[idx]
                masked_key += key[N_node - reg_idx - 1]
            if masked_key in masked_results:
                masked_results[masked_key] += value
            else:
                masked_results[masked_key] = value

        return masked_results

    def retrieve_result(self, job_id, format_result=True):
        """Retrieve the measurement results.

        Parameters
        ----------
        job_id : str
            the id of the job.
        format_result : bool, optional
            whether to format the result so that only the result corresponding to the output qubit is taken out.

        Returns
        -------
        result : dict
            the measurement result.
        """
        self.job = self.provider.retrieve_job(job_id)
        result = self.job.result()
        if format_result:
            result = self.format_result(result)

        return result
