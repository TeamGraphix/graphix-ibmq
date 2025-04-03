from typing import Optional

from graphix.device_interface import DeviceBackend, CompileOptions, JobHandler
from graphix_ibmq.compiler import IBMQPatternCompiler
from graphix_ibmq.job_handler import IBMQJobHandler
from graphix_ibmq.compile_options import IBMQCompileOptions
from graphix_ibmq.result_utils import format_result

from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel
from qiskit.providers.backend import BackendV2
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2 as Sampler


class IBMQBackend(DeviceBackend):
    """IBMQ backend implementation for compiling and executing quantum patterns."""

    def __init__(self) -> None:
        """Initialize the IBMQ backend."""
        super().__init__()
        self._compiler: Optional[IBMQPatternCompiler] = None
        self._options: Optional[IBMQCompileOptions] = None
        self._compiled_circuit: Optional[QuantumCircuit] = None
        self._execution_mode: Optional[str] = None

    def compile(self, options: Optional[CompileOptions] = None) -> None:
        """Compile the assigned pattern using IBMQ options.

        Parameters
        ----------
        options : CompileOptions, optional
            Compilation options. Must be of type IBMQCompileOptions.
        """
        if self.pattern is None:
            raise ValueError("Pattern not set.")
        if options is None:
            self._options = IBMQCompileOptions()
        elif not isinstance(options, IBMQCompileOptions):
            raise TypeError("Expected IBMQCompileOptions")
        else:
            self._options = options

        self._compiler = IBMQPatternCompiler(self.pattern)
        self._compiled_circuit = self._compiler.to_qiskit_circuit(
            save_statevector=self._options.save_statevector,
            layout_method=self._options.layout_method,
        )

    def set_simulator(
        self,
        noise_model: Optional[NoiseModel] = None,
        based_on: Optional[BackendV2] = None,
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

    def select_backend(
        self,
        name: Optional[str] = None,
        least_busy: bool = False,
        min_qubits: int = 1,
    ) -> None:
        """Select a hardware backend from IBMQ.

        Parameters
        ----------
        name : str, optional
            Specific backend name to use.
        least_busy : bool, optional
            If True, select the least busy backend that meets requirements.
        min_qubits : int, optional
            Minimum number of qubits required.
        """
        from qiskit_ibm_runtime import QiskitRuntimeService

        self._execution_mode = "hardware"
        service = QiskitRuntimeService()

        if least_busy or name is None:
            self._resource = service.least_busy(
                min_num_qubits=min_qubits, operational=True
            )
        else:
            self._resource = service.backend(name)

    def submit_job(self, shots: int = 1024) -> JobHandler:
        """Submit the compiled circuit to either simulator or hardware backend.

        Parameters
        ----------
        shots : int, optional
            Number of execution shots. Defaults to 1024.

        Returns
        -------
        JobHandler
            A handle to monitor the job status and retrieve results.

        Raises
        ------
        RuntimeError
            If the pattern has not been compiled or execution mode is not set.
        """
        if self._compiled_circuit is None:
            raise RuntimeError("Pattern must be compiled before submission.")

        if self._execution_mode is None:
            raise RuntimeError(
                "Execution mode is not configured. Use select_backend() or set_simulator()."
            )

        if self._execution_mode == "simulation":
            pm = generate_preset_pass_manager(
                backend=self._simulator,
                optimization_level=self._options.optimization_level,
            )
            transpiled = pm.run(self._compiled_circuit)
            sampler = Sampler(mode=self._simulator)
            job = sampler.run([transpiled], shots=shots)
            return IBMQJobHandler(job)

        elif self._execution_mode == "hardware":
            pm = generate_preset_pass_manager(
                backend=self._resource,
                optimization_level=self._options.optimization_level,
            )
            transpiled = pm.run(self._compiled_circuit)
            sampler = Sampler(mode=self._resource)
            job = sampler.run([transpiled], shots=shots)
            return IBMQJobHandler(job)

        else:
            raise RuntimeError(
                "Execution mode is not configured. Use select_backend() or set_simulator()."
            )

    def retrieve_result(self, job_handle: JobHandler, raw_result: bool = False):
        """Retrieve the result from a completed job.

        Parameters
        ----------
        job_handle : JobHandler
            Handle to the executed job.
        raw_result : bool, optional
            If True, return raw counts; otherwise, return formatted results.

        Returns
        -------
        dict or Any
            Formatted result or raw counts from the job.

        Raises
        ------
        TypeError
            If the job handle is not an instance of IBMQJobHandler.
        """
        if not isinstance(job_handle, IBMQJobHandler):
            raise TypeError("Expected IBMQJobHandler")

        if not job_handle.is_done():
            print("Job not done.")
            return None

        result = job_handle.job.result()
        counts = result[0].data.meas.get_counts()

        if not raw_result:
            return format_result(counts, self.pattern, self._compiler.register_dict)
        return counts
