import pytest
from unittest.mock import MagicMock

from graphix_ibmq.backend import IBMQBackend
from graphix_ibmq.compile_options import IBMQCompileOptions

from graphix_ibmq.compiler import IBMQCompiledCircuit
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

class MockCompiler:
    def __init__(self, pattern):
        self._pattern = pattern

    def compile(self, save_statevector: bool):
        return IBMQCompiledCircuit(
            circuit=QuantumCircuit(1),
            pattern=self._pattern,
            register_dict={},
            circ_output=[],
        )

def test_compile_with_default_options(monkeypatch):
    monkeypatch.setattr("graphix_ibmq.backend.IBMQPatternCompiler", MockCompiler)
    backend = IBMQBackend()
    dummy_pattern = object()

    compiled_circuit = backend.compile(dummy_pattern)

    assert isinstance(compiled_circuit, IBMQCompiledCircuit)
    assert compiled_circuit.pattern is dummy_pattern
    assert isinstance(backend._options, IBMQCompileOptions)


def test_compile_with_invalid_options():
    backend = IBMQBackend()
    with pytest.raises(TypeError, match="options must be an instance of IBMQCompileOptions"):
        backend.compile(object(), options="not-a-valid-option")


def test_set_simulator():
    backend = IBMQBackend()
    backend.set_simulator()

    assert isinstance(backend._backend, AerSimulator)
    assert backend._backend.options.noise_model is None


def test_set_hardware(monkeypatch):
    backend = IBMQBackend()

    mock_service_instance = MagicMock()
    mock_backend_obj = MagicMock()
    mock_backend_obj.name = "mock_hardware_backend"
    mock_service_instance.backend.return_value = mock_backend_obj

    monkeypatch.setattr(
        "graphix_ibmq.backend.QiskitRuntimeService", lambda: mock_service_instance
    )

    backend.set_hardware(name="mock_hardware_backend")

    assert backend._backend is mock_backend_obj
    mock_service_instance.backend.assert_called_once_with("mock_hardware_backend")


def test_submit_job_without_backend_configured():
    backend = IBMQBackend()
    dummy_compiled_circuit = IBMQCompiledCircuit(
        circuit=QuantumCircuit(1), pattern=object(), register_dict={}, circ_output=[]
    )
    
    with pytest.raises(RuntimeError) as exc_info:
        backend.submit_job(dummy_compiled_circuit)
    
    assert "Backend not set" in str(exc_info.value)
