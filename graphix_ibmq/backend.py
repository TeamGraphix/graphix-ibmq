from graphix.device_interface import DeviceBackend, CompileOptions, JobHandle
from graphix_ibmq.compiler import IBMQPatternCompiler
from graphix_ibmq.executor import IBMQJobExecutor
from graphix_ibmq.job_handle import IBMQJobHandle
from graphix_ibmq.compile_options import IBMQCompileOptions
from graphix_ibmq.result_utils import format_result


class IBMQBackend(DeviceBackend):
    def __init__(self, instance: str = "ibm-q/open/main", resource: str = None):
        super().__init__()
        self.instance = instance
        self.resource = resource
        self._compiled_circuit = None
        self._executor = None
        self._register_dict = None
        self._options = None

    def compile(self, options: CompileOptions = None) -> None:
        if self.pattern is None:
            raise ValueError("Pattern not set.")
        if not isinstance(options, IBMQCompileOptions):
            raise TypeError("Expected IBMQCompileOptions")

        self._options = options
        compiler = IBMQPatternCompiler(self.pattern)
        self._compiled_circuit = compiler.to_qiskit_circuit(
            save_statevector=options.save_statevector,
            layout_method=options.layout_method
        )
        self._register_dict = compiler.register_dict

    def submit_job(self, shots: int = 1024) -> JobHandle:
        if self._compiled_circuit is None:
            raise RuntimeError("Pattern must be compiled before submission.")

        self._executor = IBMQJobExecutor(self._compiled_circuit)
        self._executor.select_backend(self.instance, self.resource)

        job_result = self._executor.run(shots=shots, optimization_level=self._options.optimization_level)
        return IBMQJobHandle(job_result)

    def retrieve_result(self, job_handle: JobHandle, raw_result: bool = False):
        if not isinstance(job_handle, IBMQJobHandle):
            raise TypeError("Expected IBMQJobHandle")

        result = job_handle.job.result()
        counts = result[0].data.get_counts()

        if not raw_result:
            return format_result(counts, self.pattern, self._register_dict)
        return counts