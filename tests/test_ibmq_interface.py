import unittest
import numpy as np
from qiskit import Aer, transpile
from graphix_ibmq.runner import IBMQBackend
import tests.random_circuit as rc


def modify_statevector(statevector, output_qubit):
    N = round(np.log2(len(statevector)))
    new_statevector = np.zeros(2 ** len(output_qubit), dtype=complex)
    for i in range(len(statevector)):
        i_str = format(i, f"0{N}b")
        new_idx = ""
        for idx in output_qubit:
            new_idx += i_str[N - idx - 1]
        new_statevector[int(new_idx, 2)] += statevector[i]
    return new_statevector


class TestIBMQInterface(unittest.TestCase):
    def test_to_qiskit(self):
        nqubits = 5
        depth = 5
        pairs = [(i, np.mod(i + 1, nqubits)) for i in range(nqubits)]
        circuit = rc.generate_gate(nqubits, depth, pairs)
        pattern = circuit.transpile()
        state = pattern.simulate_pattern()

        ibmq_backend = IBMQBackend(pattern)
        simulator = Aer.get_backend("aer_simulator")
        ibmq_backend.to_qiskit(save_statevector=True)
        qiskit_circuit = transpile(ibmq_backend.circ, simulator)
        sim_result = simulator.run(qiskit_circuit).result()
        state_qiskit = sim_result.get_statevector(qiskit_circuit)
        state_qiskit_mod = modify_statevector(state_qiskit, ibmq_backend.circ_output)

        np.testing.assert_almost_equal(np.abs(np.dot(state_qiskit_mod.conjugate(), state.flatten())), 1)


if __name__ == "__main__":
    unittest.main()
