"""Interface for MBQC pattern execution on IBM quantum devices."""

from __future__ import annotations

import enum
from enum import Enum
from typing import TYPE_CHECKING, assert_never

import numpy as np
from graphix.command import CommandKind
from graphix.fundamentals import Plane
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime import IBMBackend, QiskitRuntimeService, SamplerV2

if TYPE_CHECKING:
    from graphix.pattern import Pattern


class QiskitUGate(Enum):
    """Single-qubit gate."""

    ID = enum.auto()
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()
    S = enum.auto()
    SDG = enum.auto()
    H = enum.auto()

    def perform(self, circ: QuantumCircuit, idx: int) -> None:
        """Perform the gate."""
        if self == QiskitUGate.ID:
            pass
        elif self == QiskitUGate.X:
            circ.x(idx)
        elif self == QiskitUGate.Y:
            circ.y(idx)
        elif self == QiskitUGate.Z:
            circ.z(idx)
        elif self == QiskitUGate.S:
            circ.s(idx)
        elif self == QiskitUGate.SDG:
            circ.sdg(idx)
        elif self == QiskitUGate.H:
            circ.h(idx)
        else:
            assert_never(self)


# qiskit representation of Clifford gates above.
# see graphix.clifford module for the definitions and details of Clifford operatos for each index.
CLIFFORD_TO_QISKIT = [
    [QiskitUGate.ID],
    [QiskitUGate.X],
    [QiskitUGate.Y],
    [QiskitUGate.Z],
    [QiskitUGate.S],
    [QiskitUGate.SDG],
    [QiskitUGate.H],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.SDG],
    [QiskitUGate.H, QiskitUGate.X],
    [QiskitUGate.SDG, QiskitUGate.Y],
    [QiskitUGate.SDG, QiskitUGate.X],
    [QiskitUGate.H, QiskitUGate.Y],
    [QiskitUGate.H, QiskitUGate.Z],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.SDG, QiskitUGate.Y],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.S],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.SDG, QiskitUGate.X],
    [QiskitUGate.SDG, QiskitUGate.H],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.Y],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.Z],
    [QiskitUGate.SDG, QiskitUGate.H, QiskitUGate.X],
    [QiskitUGate.H, QiskitUGate.S],
    [QiskitUGate.H, QiskitUGate.SDG],
    [QiskitUGate.H, QiskitUGate.X, QiskitUGate.SDG],
    [QiskitUGate.H, QiskitUGate.X, QiskitUGate.S],
]


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
        """Initialize interface.

        Parameters
        ----------
        pattern: graphix.Pattern object
            MBQC pattern to be run on the IBMQ device or Aer simulator.

        """
        self.pattern = pattern
        self.to_qiskit()

    def get_system(self, service: QiskitRuntimeService, system: str | None = None):
        """Get the system to be used for the execution.

        Parameters
        ----------
        service: qiskit_ibm_runtime.qiskit_runtime_service.QiskitRuntimeService object
            the runtime service object.
        system: str, optional
            the system name to be used. If None, the least busy system is used.

        """
        self.service = service
        if system is not None:
            if system not in [system_cand.name for system_cand in self.service.backends()]:
                raise ValueError(f"{system} is not available.")
            self.system = self.service.backend(system)
        else:
            self.system = self.service.least_busy(min_num_qubits=self.pattern.max_space(), operational=True)

        print(f"Using system {self.system.name}")

    def to_qiskit(self, save_statevector: bool = False):
        """Convert the MBQC pattern to the qiskit cuicuit and add to attributes.

        Parameters
        ----------
        save_statevector : bool, optional
            whether to save the statevector before the measurements of output qubits.

        """
        n = self.pattern.max_space()
        n_node = self.pattern.n_node

        qr = QuantumRegister(n)
        cr = ClassicalRegister(n_node)
        circ = QuantumCircuit(qr, cr)

        empty_qubit = list(range(n))  # list of free qubit indices
        qubit_dict = {}  # dictionary to record the correspondance of pattern nodes and circuit qubits
        register_dict = {}  # dictionary to record the correspondance of pattern nodes and classical registers
        reg_idx = 0  # index of classical register

        def signal_process(op, signal):
            if op == "X":
                for s in signal:
                    if s in register_dict:
                        s_idx = register_dict[s]
                        with circ.if_test((cr[s_idx], 1)):
                            circ.x(circ_idx)
                    elif self.pattern.results[s] == 1:
                        circ.x(circ_idx)
            if op == "Z":
                for s in signal:
                    if s in register_dict:
                        s_idx = register_dict[s]
                        with circ.if_test((cr[s_idx], 1)):
                            circ.z(circ_idx)
                    elif self.pattern.results[s] == 1:
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
                u, v = cmd.nodes
                circ.cz(qubit_dict[u], qubit_dict[v])

            if cmd.kind == CommandKind.M:
                circ_idx = qubit_dict[cmd.node]
                plane = cmd.plane
                alpha = cmd.angle * np.pi
                s_list = cmd.s_domain
                t_list = cmd.t_domain

                signal_process("X", s_list)
                signal_process("Z", t_list)

                if plane == Plane.XY:
                    circ.rz(-alpha, circ_idx)
                    circ.h(circ_idx)
                elif plane == Plane.YZ:
                    circ.rx(alpha, circ_idx)
                elif plane == Plane.XZ:
                    circ.ry(alpha, circ_idx)
                else:
                    assert_never(plane)
                circ.measure(circ_idx, reg_idx)  # measure and store the result
                register_dict[cmd.node] = reg_idx
                reg_idx += 1
                empty_qubit.append(circ_idx)  # liberate the circuit qubit

            if cmd.kind == CommandKind.X:
                circ_idx = qubit_dict[cmd.node]
                s_list = cmd.domain
                signal_process("X", s_list)

            if cmd.kind == CommandKind.Z:
                circ_idx = qubit_dict[cmd.node]
                s_list = cmd.domain
                signal_process("Z", s_list)

            if cmd.kind == CommandKind.C:
                circ_idx = qubit_dict[cmd.node]
                cid = cmd.clifford
                for op in CLIFFORD_TO_QISKIT[cid.value]:
                    op.perform(circ, circ_idx)

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
        """Set the input state of the circuit.

        The input states are set to the circuit qubits corresponding to the first n nodes prepared in the pattern.

        Parameters
        ----------
        psi : list[list[complex]]
            list of the input states for each input.
            Each input state is a list of complex of length 2, representing the coefficient of |0> and |1>.

        """
        input_nodes = list(self.pattern.input_nodes)
        n = len(input_nodes)
        if n != len(psi):
            raise ValueError("Invalid input state.")

        for k, ope in enumerate(self.circ.data):
            if k >= n:
                break
            if ope[0].name == "reset":
                qubit_idx = ope[1][0]._index
                i = input_nodes[k]
                self.circ.initialize(psi[i], qubit_idx)

    def transpile(self, system: IBMBackend = None, optimization_level: int = 1):
        """Transpile the circuit for the designated resource.

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

    def simulate(
        self,
        shots: int = 1024,
        noise_model: NoiseModel = None,
        format_result: bool = True,
    ):
        """Simulate the circuit with Aer.

        Parameters
        ----------
        shots : int, optional
            the number of shots.
        noise_model : :class:`qiskit_aer.backends.aer_simulator.AerSimulator` object, optional
            noise model to be used in the simulation.
        format_result : bool, optional
            whether to format the result so that only the result corresponding to the output qubit is taken out.

        Returns
        -------
        result : dict
            the measurement result.

        """
        if noise_model is not None:
            if type(noise_model) is NoiseModel:
                simulator = AerSimulator(noise_model=noise_model)
            else:
                try:
                    simulator = AerSimulator.from_backend(noise_model)
                except NotImplementedError as exc:
                    raise ValueError("Invalid noise model.") from exc
        else:
            simulator = AerSimulator()
        circ_sim = transpile(self.circ, simulator)
        job = simulator.run(circ_sim, shots=shots)
        result = job.result()
        if format_result:
            result = self.format_result(result)

        return result

    def run(self, shots: int = 1024, format_result: bool = True, optimization_level: int = 1):
        """Run the MBQC pattern on IBMQ devices.

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
        n_node = self.pattern.Nnode

        # Iterate over original measurement results
        for key, value in result.get_counts().items():
            masked_key = ""
            for idx in self.pattern.output_nodes:
                reg_idx = self.register_dict[idx]
                masked_key += key[n_node - reg_idx - 1]
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
