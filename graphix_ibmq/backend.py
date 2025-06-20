from __future__ import annotations

from graphix_ibmq.compiler import IBMQPatternCompiler
from graphix_ibmq.job import IBMQJob
from graphix_ibmq.compile_options import IBMQCompileOptions

from qiskit_aer.noise import NoiseModel
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphix.pattern import Pattern
    from qiskit import QuantumCircuit
    from qiskit.providers.backend import BackendV2


class IBMQBackend:
    """IBMQ backend implementation for compiling and executing quantum patterns."""

    _options: IBMQCompileOptions
    _compiled_circuit: QuantumCircuit | None
    _execution_mode: str | None
    _noise_model: NoiseModel | None
    _simulator: AerSimulator | None
    _resource: BackendV2 | None
    _compiler: IBMQPatternCompiler | None

    def __init__(self) -> None:
        self._compiler = None
        self._options = IBMQCompileOptions()
        self._compiled_circuit = None
        self._execution_mode = None
        self._noise_model = None
        self._simulator = None
        self._resource = None

    def compile(self, pattern: Pattern, options: IBMQCompileOptions | None = None) -> None:
        """Compile the assigned pattern using IBMQ options.

        Parameters
        ----------
        options : CompileOptions, optional
            Compilation options. Must be of type IBMQCompileOptions.
        """
        if options is None:
            self._options = IBMQCompileOptions()
        elif not isinstance(options, IBMQCompileOptions):
            raise TypeError("Expected IBMQCompileOptions")
        else:
            self._options = options

        self._compiler = IBMQPatternCompiler(pattern)
        self._compiled_circuit = self._compiler.to_qiskit_circuit(
            save_statevector=self._options.save_statevector,
            layout_method=self._options.layout_method,
        )

    def set_simulator(
        self,
        noise_model: NoiseModel | None = None,
        based_on: BackendV2 | None = None,
    ) -> None:
        """Configure the backend to use a simulator.

        Parameters
        ----------
        noise_model : NoiseModel, optional
            Noise model to apply to the simulator.
        based_on : BackendV2, optional
            Backend to base the noise model on.
        """
        if noise_model is None and based_on is not None:
            noise_model = NoiseModel.from_backend(based_on)

        self._execution_mode = "simulation"
        self._noise_model = noise_model
        self._simulator = AerSimulator(noise_model=noise_model)

    def select_device(
        self,
        name: str | None = None,
        least_busy: bool = False,
        min_qubits: int = 1,
    ) -> None:
        """Select a hardware backend from IBMQ.

        Parameters
        ----------
        name : str, optional
            Specific device name to use.
        least_busy : bool, optional
            If True, select the least busy device that meets requirements.
        min_qubits : int, optional
            Minimum number of qubits required.
        """
        from qiskit_ibm_runtime import QiskitRuntimeService

        self._execution_mode = "hardware"
        service = QiskitRuntimeService()

        if least_busy or name is None:
            self._resource = service.least_busy(min_num_qubits=min_qubits, operational=True)
        else:
            self._resource = service.backend(name)

        print(f"Selected device: {self._resource.name}")

    def submit_job(self, shots: int = 1024) -> IBMQJob:
        """Submit the compiled circuit to either simulator or hardware backend.

        Parameters
        ----------
        shots : int, optional
            Number of execution shots. Defaults to 1024.

        Returns
        -------
        Job
            A handle to monitor the job status and retrieve results.

        Raises
        ------
        RuntimeError
            If the pattern has not been compiled or execution mode is not set.
        """
        if self._compiled_circuit is None:
            raise RuntimeError("Pattern must be compiled before submission.")

        if self._execution_mode is None:
            raise RuntimeError("Execution mode is not configured. Use select_backend() or set_simulator().")

        if not hasattr(self, "_options") or self._options is None:
            raise RuntimeError("Compile options are not set.")

        if self._execution_mode == "simulation":
            pm = generate_preset_pass_manager(
                backend=self._simulator,
                optimization_level=self._options.optimization_level,
            )
            transpiled = pm.run(self._compiled_circuit)
            sampler = Sampler(mode=self._simulator)
            job = sampler.run([transpiled], shots=shots)
            return IBMQJob(job, self._compiler)

        elif self._execution_mode == "hardware":
            pm = generate_preset_pass_manager(
                backend=self._resource,
                optimization_level=self._options.optimization_level,
            )
            transpiled = pm.run(self._compiled_circuit)
            sampler = Sampler(mode=self._resource)
            job = sampler.run([transpiled], shots=shots)
            return IBMQJob(job, self._compiler)

        else:
            raise RuntimeError("Execution mode is not configured. Use select_backend() or set_simulator().")
