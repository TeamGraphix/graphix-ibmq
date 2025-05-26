"""Qiskit to graphix circuit converter."""

from graphix import Circuit
from qiskit import QuantumCircuit, transpile


def qiskit_to_graphix(qc: QuantumCircuit) -> Circuit:
    """Convert a Qiskit circuit to a graphix circuit.

    .. note::

        A qiskit circuit that contains non-unitary components such as ``if_else`` operation, measurement, etc. is not supported.

    Args:
        qc (QuantumCircuit): Qiskit circuit to convert

    Returns:
        Circuit: Converted graphix circuit

    """
    if not isinstance(qc, QuantumCircuit):
        raise TypeError(f"qc must be QuantumCircuit, not {type(qc)}")
    if len(qc.get_instructions("if_else")) != 0:
        raise ValueError("QuantumCircuit must not contain `if_else` operation")
    qc = transpile(qc, basis_gates=["rx", "rz", "cx"])
    circuit = Circuit(qc.num_qubits)
    # initialize with zero state
    for idx in range(qc.num_qubits):
        circuit.h(idx)
    for ci in qc.data:
        if ci.operation.name == "rx":
            circuit.rx(ci.qubits[0]._index, ci.operation.params[0])
        elif ci.operation.name == "rz":
            circuit.rz(ci.qubits[0]._index, ci.operation.params[0])
        elif ci.operation.name == "cx":
            circuit.cnot(ci.qubits[0]._index, ci.qubits[1]._index)
        else:
            raise ValueError(f"QuantumCircuit must not contain non-unitary component: {ci.operation.name}")

    return circuit
