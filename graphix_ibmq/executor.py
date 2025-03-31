from qiskit import transpile
from qiskit.result import Result
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from typing import Optional

class IBMQJobExecutor:
    def __init__(self, circuit):
        self.circuit = circuit
        self.backend = None
        self.service = None
        self.job_id = None

    def select_backend(self, instance: str, system: Optional[str] = None):
        self.service = QiskitRuntimeService(instance=instance)
        if system:
            self.backend = self.service.backend(system)
        else:
            self.backend = self.service.least_busy(min_num_qubits=self.circuit.num_qubits, operational=True)

    def run(self, shots: int, optimization_level: int = 1) -> Result:
        transpiled = transpile(self.circuit, backend=self.backend, optimization_level=optimization_level)
        sampler = SamplerV2(service=self.service)
        job = sampler.run([transpiled], shots=shots, backend=self.backend)
        result = job.result()
        self.job_id = job.job_id()
        return result

    def simulate(self, shots: int = 1024, noise_model: NoiseModel = None) -> Result:
        simulator = AerSimulator(noise_model=noise_model) if noise_model else AerSimulator()
        transpiled = transpile(self.circuit, simulator)
        job = simulator.run(transpiled, shots=shots)
        return job.result()

