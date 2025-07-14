from __future__ import annotations
from typing import TYPE_CHECKING

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler, QiskitRuntimeService

from graphix_ibmq.compile_options import IBMQCompileOptions
from graphix_ibmq.compiler import IBMQPatternCompiler, IBMQCompiledCircuit
from graphix_ibmq.job import IBMQJob

if TYPE_CHECKING:
    from graphix.pattern import Pattern
    from qiskit.providers.backend import BackendV2, Backend


class IBMQBackend:
    """
    Manages compilation and execution on IBMQ simulators or hardware.

    This class configures the execution target and provides methods to compile
    a graphix Pattern and submit it as a job.
    """

    def __init__(self) -> None:
        self._options = IBMQCompileOptions()
        # The target backend, either a simulator or a real hardware device.
        self._backend: Backend | None = None

    def compile(self, pattern: Pattern, options: IBMQCompileOptions | None = None) -> IBMQCompiledCircuit:
        """
        Compiles the given pattern into a Qiskit QuantumCircuit.

        Parameters
        ----------
        pattern : Pattern
            The graphix pattern to compile.
        options : IBMQCompileOptions, optional
            Compilation options. If not provided, default options are used.

        Returns
        -------
        IBMQCompiledCircuit
            An object containing the compiled circuit and related metadata.
        """
        if options is None:
            self._options = IBMQCompileOptions()
        elif not isinstance(options, IBMQCompileOptions):
            raise TypeError("options must be an instance of IBMQCompileOptions")
        else:
            self._options = options

        compiler = IBMQPatternCompiler(pattern)
        return compiler.compile(save_statevector=self._options.save_statevector)

    def set_simulator(self, noise_model: NoiseModel | None = None, from_backend: BackendV2 | None = None) -> None:
        """
        Configures the backend to use a local Aer simulator.

        Parameters
        ----------
        noise_model : NoiseModel, optional
            A custom noise model for the simulation.
        from_backend : BackendV2, optional
            A hardware backend to base the noise model on. Ignored if `noise_model` is provided.
        """
        if noise_model is None and from_backend is not None:
            noise_model = NoiseModel.from_backend(from_backend)

        self._backend = AerSimulator(noise_model=noise_model)
        print("Backend set to local AerSimulator.")

    def set_hardware(self, name: str | None = None, least_busy: bool = False, min_qubits: int = 1) -> None:
        """
        Selects a real hardware backend from IBM Quantum.

        Parameters
        ----------
        name : str, optional
            The specific name of the device (e.g., 'ibm_brisbane').
        least_busy : bool
            If True, selects the least busy device meeting the criteria.
        min_qubits : int
            The minimum number of qubits required.
        """
        service = QiskitRuntimeService()

        if name:
            backend = service.backend(name)
        else:
            backend = service.least_busy(min_num_qubits=min_qubits, operational=True)

        self._backend = backend
        # Note: In a production library, consider using the `logging` module instead of `print`.
        print(f"Selected hardware backend: {self._backend.name}")

    def submit_job(self, compiled_circuit: IBMQCompiledCircuit, shots: int = 1024) -> IBMQJob:
        """
        Submits the compiled circuit to the configured backend for execution.

        Parameters
        ----------
        compiled_circuit : IBMQCompiledCircuit
            The compiled circuit object from the `compile` method.
        shots : int, optional
            The number of execution shots. Defaults to 1024.

        Returns
        -------
        IBMQJob
            A job object to monitor execution and retrieve results.
        """
        if self._backend is None:
            raise RuntimeError("Backend not set. Call 'set_simulator()' or 'set_hardware()' before submitting a job.")

        pass_manager = generate_preset_pass_manager(
            backend=self._backend,
            optimization_level=self._options.optimization_level,
        )
        transpiled_circuit = pass_manager.run(compiled_circuit.circuit)

        sampler = Sampler(mode=self._backend)
        job = sampler.run([transpiled_circuit], shots=shots)

        return IBMQJob(job, compiled_circuit)
