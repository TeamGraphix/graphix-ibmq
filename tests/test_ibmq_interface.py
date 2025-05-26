import numpy as np
from graphix.random_objects import rand_gate

from graphix_ibmq.runner import IBMQBackend


def modify_statevector(statevector, output_qubit):
    n = round(np.log2(len(statevector)))
    new_statevector = np.zeros(2 ** len(output_qubit), dtype=complex)
    for i in range(len(statevector)):
        i_str = format(i, f"0{n}b")
        new_idx = ""
        for idx in output_qubit:
            new_idx += i_str[n - idx - 1]
        new_statevector[int(new_idx, 2)] += statevector[i]
    return new_statevector


def test_to_qiskit() -> None:
    nqubits = 5
    depth = 5
    pairs = [(i, np.mod(i + 1, nqubits)) for i in range(nqubits)]
    circuit = rand_gate(nqubits, depth, pairs)
    pattern = circuit.transpile().pattern
    state = pattern.simulate_pattern()

    ibmq_backend = IBMQBackend(pattern)
    ibmq_backend.to_qiskit(save_statevector=True)
    sim_result = ibmq_backend.simulate(format_result=False)
    state_qiskit = sim_result.get_statevector(ibmq_backend.circ)
    state_qiskit_mod = modify_statevector(np.array(state_qiskit), ibmq_backend.circ_output)

    np.testing.assert_almost_equal(np.abs(np.dot(state_qiskit_mod.conjugate(), state.flatten())), 1)


def test_to_qiskit_after_pauli_preprocess() -> None:
    nqubits = 2
    depth = 2
    pairs = [(i, np.mod(i + 1, nqubits)) for i in range(nqubits)]
    circuit = rand_gate(nqubits, depth, pairs)
    pattern = circuit.transpile().pattern
    pattern.perform_pauli_measurements()
    pattern.minimize_space()
    state = pattern.simulate_pattern()

    ibmq_backend = IBMQBackend(pattern)
    ibmq_backend.to_qiskit(save_statevector=True)
    sim_result = ibmq_backend.simulate(format_result=False)
    state_qiskit = sim_result.get_statevector(ibmq_backend.circ)
    state_qiskit_mod = modify_statevector(np.array(state_qiskit), ibmq_backend.circ_output)

    np.testing.assert_almost_equal(np.abs(np.dot(state_qiskit_mod.conjugate(), state.flatten())), 1)
