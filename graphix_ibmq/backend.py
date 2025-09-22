from __future__ import annotations
from typing import TYPE_CHECKING
import logging

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler, QiskitRuntimeService

from graphix_ibmq.compile_options import IBMQCompileOptions
from graphix_ibmq.compiler import IBMQPatternCompiler, IBMQCompiledCircuit
from graphix_ibmq.job import IBMQJob

if TYPE_CHECKING:
    from graphix.pattern import Pattern
    from qiskit.providers.backend import BackendV2

logger = logging.getLogger(__name__)


class IBMQBackend:
    """
    Manages compilation and execution on IBMQ simulators or hardware.

    This class configures the execution target and provides methods to compile
    a graphix Pattern and submit it as a job. Instances should be created using
    the `from_simulator` or `from_hardware` classmethods.
    """

    def __init__(self, backend: BackendV2 | None = None, options: IBMQCompileOptions | None = None) -> None:
        if backend is None or options is None:
            raise TypeError(
                "IBMQBackend cannot be instantiated directly. "
                "Please use the classmethods `IBMQBackend.from_simulator()` "
                "or `IBMQBackend.from_hardware()`."
            )
        self._backend: BackendV2 = backend
        self._options: IBMQCompileOptions = options

    @classmethod
    def from_simulator(
        cls,
        noise_model: NoiseModel | None = None,
        from_backend: BackendV2 | None = None,
        options: IBMQCompileOptions | None = None,
    ) -> IBMQBackend:
        """Creates an instance with a local Aer simulator as the backend.

        Parameters
        ----------
        noise_model : NoiseModel, optional
            A custom noise model for the simulation.
        from_backend : BackendV2, optional
            A hardware backend to base the noise model on.
            Ignored if `noise_model` is provided.
        options : IBMQCompileOptions, optional
            Compilation and execution options.
        """
        if noise_model is None and from_backend is not None:
            noise_model = NoiseModel.from_backend(from_backend)

        aer_backend = AerSimulator(noise_model=noise_model)
        compile_options = options if options is not None else IBMQCompileOptions()

        logger.info("Backend set to local AerSimulator.")
        return cls(backend=aer_backend, options=compile_options)

    @classmethod
    def from_hardware(
        cls,
        name: str | None = None,
        min_qubits: int = 1,
        options: IBMQCompileOptions | None = None,
    ) -> IBMQBackend:
        """Creates an instance with a real IBM Quantum hardware device as the backend.

        Parameters
        ----------
        name : str, optional
            The specific name of the device (e.g., 'ibm_brisbane'). If None,
            the least busy backend with at least `min_qubits` will be selected.
        min_qubits : int
            The minimum number of qubits required.
        options : IBMQCompileOptions, optional
            Compilation and execution options.
        """
        service = QiskitRuntimeService()
        if name:
            hw_backend = service.backend(name)
        else:
            hw_backend = service.least_busy(min_num_qubits=min_qubits, operational=True)

        compile_options = options if options is not None else IBMQCompileOptions()

        logger.info("Selected hardware backend: %s", hw_backend.name)
        return cls(backend=hw_backend, options=compile_options)

    @staticmethod
    def compile(pattern: Pattern, save_statevector: bool = False) -> IBMQCompiledCircuit:
        """Compiles a graphix pattern into a Qiskit QuantumCircuit.

        This method is provided as a staticmethod because it does not depend
        on the backend's state.

        Parameters
        ----------
        pattern : Pattern
            The graphix pattern to compile.
        save_statevector : bool
            If True, saves the statevector before the final measurement.

        Returns
        -------
        IBMQCompiledCircuit
            An object containing the compiled circuit and related metadata.
        """
        compiler = IBMQPatternCompiler(pattern)
        return compiler.compile(save_statevector=save_statevector)

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
        pass_manager = generate_preset_pass_manager(
            backend=self._backend,
            optimization_level=self._options.optimization_level,
        )
        transpiled_circuit = pass_manager.run(compiled_circuit.circuit)

        sampler = Sampler(mode=self._backend)
        job = sampler.run([transpiled_circuit], shots=shots)

        return IBMQJob(job, compiled_circuit)
