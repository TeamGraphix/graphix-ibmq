import pytest
from unittest.mock import MagicMock, patch

from graphix_ibmq.backend import IBMQBackend
from graphix_ibmq.compile_options import IBMQCompileOptions
from graphix_ibmq.compiler import IBMQCompiledCircuit
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# A dummy pattern object for tests
DUMMY_PATTERN = object()


def test_compile_is_static_and_works(monkeypatch):
    """
    Verify that `compile` is a static method and works without an instance.
    """
    # Arrange
    mock_compiler_instance = MagicMock()
    mock_compiled_circuit = IBMQCompiledCircuit(
        circuit=QuantumCircuit(1), pattern=DUMMY_PATTERN, register_dict={}, circ_output=[]
    )
    mock_compiler_instance.compile.return_value = mock_compiled_circuit

    # Mock the compiler class to return our mock instance
    mock_compiler_class = MagicMock(return_value=mock_compiler_instance)
    monkeypatch.setattr("graphix_ibmq.backend.IBMQPatternCompiler", mock_compiler_class)

    # Act
    compiled_circuit = IBMQBackend.compile(DUMMY_PATTERN)

    # Assert
    assert compiled_circuit is mock_compiled_circuit
    mock_compiler_class.assert_called_once_with(DUMMY_PATTERN)
    mock_compiler_instance.compile.assert_called_once()


def test_from_simulator_creates_instance():
    """
    Verify that the `from_simulator` factory method creates a valid instance.
    """
    # Act
    backend = IBMQBackend.from_simulator()

    # Assert
    assert isinstance(backend, IBMQBackend)
    assert isinstance(backend._backend, AerSimulator)
    assert backend._backend.options.noise_model is None


def test_from_hardware_creates_instance(monkeypatch):
    """
    Verify that the `from_hardware` factory method creates a valid instance.
    """
    # Arrange
    mock_service_instance = MagicMock()
    mock_backend_obj = MagicMock()
    mock_backend_obj.name = "mock_hardware_backend"
    mock_service_instance.backend.return_value = mock_backend_obj
    monkeypatch.setattr("graphix_ibmq.backend.QiskitRuntimeService", lambda: mock_service_instance)

    # Act
    backend = IBMQBackend.from_hardware(name="mock_hardware_backend")

    # Assert
    assert isinstance(backend, IBMQBackend)
    assert backend._backend is mock_backend_obj
    mock_service_instance.backend.assert_called_once_with("mock_hardware_backend")


def test_direct_instantiation_raises_error():
    """
    Verify that calling IBMQBackend() directly raises a TypeError.
    """
    # Act & Assert
    with pytest.raises(TypeError, match="cannot be instantiated directly"):
        IBMQBackend()


def test_submit_job_calls_sampler(monkeypatch):
    """
    Verify that `submit_job` correctly uses the configured backend and calls the sampler.
    """
    # Arrange
    # 1. Create a valid backend instance using a factory
    mock_qiskit_backend = MagicMock()
    # Use patch to temporarily replace the classmethod's implementation
    with patch.object(
        IBMQBackend, "from_hardware", return_value=IBMQBackend(mock_qiskit_backend, IBMQCompileOptions())
    ):
        backend = IBMQBackend.from_hardware()

    # 2. Mock the transpiler and sampler
    mock_pass_manager = MagicMock()
    mock_pass_manager.run.return_value = QuantumCircuit(1)  # Return a dummy transpiled circuit
    monkeypatch.setattr("graphix_ibmq.backend.generate_preset_pass_manager", MagicMock(return_value=mock_pass_manager))

    mock_sampler_instance = MagicMock()
    mock_job = MagicMock()
    mock_sampler_instance.run.return_value = mock_job
    monkeypatch.setattr("graphix_ibmq.backend.Sampler", MagicMock(return_value=mock_sampler_instance))

    # 3. Create a dummy compiled circuit to submit
    dummy_compiled_circuit = IBMQCompiledCircuit(
        circuit=QuantumCircuit(1), pattern=DUMMY_PATTERN, register_dict={}, circ_output=[]
    )

    # Act
    job_result = backend.submit_job(dummy_compiled_circuit)

    # Assert
    mock_pass_manager.run.assert_called_once_with(dummy_compiled_circuit.circuit)
    mock_sampler_instance.run.assert_called_once()
    assert job_result.job is mock_job
