import pytest
import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from graphix_ibmq.compiler import IBMQPatternCompiler
import random_circuit as rc


def reduce_statevector_to_outputs(statevector: np.ndarray, output_qubits: list) -> np.ndarray:
    """Reduce a full statevector to the subspace corresponding to output_qubits."""
    n = round(np.log2(len(statevector)))
    reduced = np.zeros(2 ** len(output_qubits), dtype=complex)
    for i, amp in enumerate(statevector):
        bin_str = format(i, f"0{n}b")
        reduced_idx = "".join([bin_str[n - idx - 1] for idx in output_qubits])
        reduced[int(reduced_idx, 2)] += amp
    return reduced


@pytest.mark.parametrize(
    "nqubits, depth",
    [
        (3, 3),
        (4, 4),
        (5, 5),
    ],
)
def test_ibmq_compiler_statevector_equivalence(nqubits, depth):
    """Test that IBMQPatternCompiler circuit reproduces the same statevector as MBQC simulation."""
    sim = AerSimulator()

    for _ in range(5):  # repeat with different random circuits
        pairs = [(i, (i + 1) % nqubits) for i in range(nqubits)]
        circuit = rc.generate_gate(nqubits, depth, pairs)
        pattern = circuit.transpile().pattern
        mbqc_state = pattern.simulate_pattern()

        compiler = IBMQPatternCompiler(pattern)
        qc = compiler.to_qiskit_circuit(save_statevector=True, layout_method=None)

        transpiled = transpile(qc, sim)
        result = sim.run(transpiled).result()
        qiskit_state = np.array(result.get_statevector(qc))
        qiskit_reduced = reduce_statevector_to_outputs(qiskit_state, compiler._circ_output)

        fidelity = np.abs(np.dot(qiskit_reduced.conjugate(), mbqc_state.flatten()))
        assert np.isclose(fidelity, 1.0, atol=1e-6), f"Fidelity mismatch: {fidelity}"
