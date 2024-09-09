from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphix.pattern import Pattern

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime import QiskitRuntimeService, IBMBackend, SamplerV2

from graphix_ibmq.clifford import CLIFFORD_CONJ, CLIFFORD_TO_QISKIT


class IBMQBackend:
    """Interface for MBQC pattern execution on IBM quantum devices.

    Attributes
    ----------
    pattern: graphix.Pattern object
        MBQC pattern to be run on the device
    circ: qiskit.circuit.quantumcircuit.QuantumCircuit object
        qiskit circuit corresponding to the pattern.
    service: qiskit_ibm_runtime.qiskit_runtime_service.QiskitRuntimeService object
        the runtime service object.
    system: qiskit_ibm_runtime.ibm_backend.IBMBackend object
        the system to be used for the execution.
    """

    def __init__(self, pattern: Pattern):
        """

        Parameters
        ----------
        pattern: graphix.Pattern object
            MBQC pattern to be run on the IBMQ device or Aer simulator.
        """
        self.pattern = pattern
        self.to_qiskit()

    def get_system(self, service: QiskitRuntimeService, system: str = None):
        """Get the system to be used for the execution.

        Parameters
        ----------
        service: qiskit_ibm_runtime.qiskit_runtime_service.QiskitRuntimeService object
            the runtime service object.
        system: str, optional
            the system name to be used. If None, the least busy system is used.
        """
        if not isinstance(service, QiskitRuntimeService):
            raise ValueError("Invalid service object.")
        self.service = service
        if system is not None:
            if system not in [system_cand.name for system_cand in self.service.backends()]:
                raise ValueError(f"{system} is not available.")
            self.system = self.service.backend(system)
        else:
            self.system = self.service.least_busy(min_num_qubits=self.pattern.max_space(), operational=True)

        print(f"Using system {self.system.name}")

    def to_qiskit(self, save_statevector: bool = False):
        """convert the MBQC pattern to the qiskit cuicuit and add to attributes.

        Parameters
        ----------
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

        for i in self.pattern.input_nodes:
            circ_idx = empty_qubit[0]
            empty_qubit.pop(0)
            circ.reset(circ_idx)
            circ.h(circ_idx)
            qubit_dict[i] = circ_idx

        for cmd in self.pattern:

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

    def set_input(self, psi: list[list[complex]]):
        """set the input state of the circuit.
        The input states are set to the circuit qubits corresponding to the first n nodes prepared in the pattern.

        Parameters
        ----------
        psi : list[list[complex]]
            list of the input states for each input.
            Each input state is a list of complex of length 2, representing the coefficient of |0> and |1>.
        """
        n = len(self.pattern.input_nodes)
        if n != len(psi):
            raise ValueError("Invalid input state.")
        input_order = {i: self.pattern.input_nodes[i] for i in range(n)}

        idx = 0
        for k, ope in enumerate(self.circ.data):
            if ope[0].name == "reset":
                if idx in input_order.keys():
                    qubit_idx = ope[1][0]._index
                    i = input_order[idx]
                    self.circ.initialize(psi[i], qubit_idx)
                    self.circ.data[k + 1] = self.circ.data.pop(-1)
                idx += 1
            if idx >= max(input_order.keys()) + 1:
                break

    def transpile(self, system: IBMBackend = None, optimization_level: int = 1):
        """transpile the circuit for the designated resource.

        Parameters
        ----------
        system: qiskit_ibm_runtime.ibm_backend.IBMBackend object, optional
            system to be used for transpilation.
        optimization_level : int, optional
            the optimization level of the transpilation.
        """
        if system is None:
            if not hasattr(self, "system"):
                raise ValueError("No system is set.")
            system = self.system
        self.circ = transpile(self.circ, backend=system, optimization_level=optimization_level)

    def simulate(self, shots: int = 1024, noise_model: NoiseModel = None, format_result: bool = True):
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
                try:
                    simulator = AerSimulator.from_backend(noise_model)
                except:
                    raise ValueError("Invalid noise model.")
        else:
            simulator = AerSimulator()
        circ_sim = transpile(self.circ, simulator)
        job = simulator.run(circ_sim, shots=shots)
        result = job.result()
        if format_result:
            result = self.format_result(result)

        return result

    def run(self, shots: int = 1024, format_result: bool = True, optimization_level: int = 1):
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
        if not hasattr(self, "system"):
            raise ValueError("No system is set.")
        sampler = SamplerV2(backend=self.system)
        job = sampler.run([self.circ], shots=shots)  # Pass the circuit and shot count to the run method
        print(f"Your job's id: {job.job_id()}")
        result = job.result()
        result = next(
            (
                getattr(result[0].data, attr_name)
                for attr_name in dir(result[0].data)
                if attr_name.startswith("c") and attr_name[1:].isdigit()
            ),
            None,
        )
        if format_result:
            result = self.format_result(result)

        return result

    def format_result(self, result: dict[str, int]):
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

    def retrieve_result(self, job_id: str, format_result: bool = True):
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
        if not hasattr(self, "service"):
            raise ValueError("No service is set.")
        job = self.service.job(job_id)
        result = job.result()
        result = next(
            (
                getattr(result[0].data, attr_name)
                for attr_name in dir(result[0].data)
                if attr_name.startswith("c") and attr_name[1:].isdigit()
            ),
            None,
        )
        if format_result:
            result = self.format_result(result)

        return result
