import pytest
from graphix_ibmq.backend import IBMQBackend
from graphix_ibmq.compile_options import IBMQCompileOptions
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


class DummyCompiler:
    def __init__(self, pattern):
        self.pattern = pattern

    def to_qiskit_circuit(self, save_statevector, layout_method):
        return QuantumCircuit(1)


def test_compile_default(monkeypatch):
    monkeypatch.setattr("graphix_ibmq.backend.IBMQPatternCompiler", DummyCompiler)
    backend = IBMQBackend()
    dummy_pattern = object()

    backend.compile(dummy_pattern)

    assert backend._pattern is dummy_pattern
    assert isinstance(backend._compiled_circuit, QuantumCircuit)
    assert isinstance(backend._options, IBMQCompileOptions)


def test_compile_invalid_options(monkeypatch):
    monkeypatch.setattr("graphix_ibmq.backend.IBMQPatternCompiler", DummyCompiler)
    backend = IBMQBackend()
    with pytest.raises(TypeError):
        backend.compile(object(), options="not-an-options")


def test_set_simulator():
    backend = IBMQBackend()
    backend.set_simulator()
    assert backend._execution_mode == "simulation"
    assert isinstance(backend._simulator, AerSimulator)
    assert backend._noise_model is None


def test_submit_job_not_compiled():
    backend = IBMQBackend()
    with pytest.raises(RuntimeError) as e:
        backend.submit_job()
    assert "Pattern must be compiled" in str(e.value)


def test_submit_job_without_execution_mode(monkeypatch):
    monkeypatch.setattr("graphix_ibmq.backend.IBMQPatternCompiler", DummyCompiler)
    backend = IBMQBackend()
    backend.compile(object())
    with pytest.raises(RuntimeError) as e:
        backend.submit_job()
    assert "Execution mode is not configured" in str(e.value)
