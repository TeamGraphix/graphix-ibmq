import unittest
import numpy as np
from graphix import Circuit
from graphix import Pattern
from qiskit import Aer, transpile

def modify_statevector(statevector, output_qubit):
    N = round(np.log2(len(statevector)))
    new_statevector = np.zeros(2**len(output_qubit), dtype=complex)
    for i in range(len(statevector)):
        i_str = f"{i:04b}"
        new_idx = i_str[N - output_qubit[0] - 1] + i_str[N - output_qubit[1] - 1] + i_str[N - output_qubit[2] - 1]
        new_statevector[int(new_idx, 2)] = statevector[i]
    return new_statevector

# copy of graphix/tests/random_cuircuit.py
def first_rotation(circuit, nqubits):
    for qubit in range(nqubits):
        circuit.rx(qubit, np.random.rand())


def mid_rotation(circuit, nqubits):
    for qubit in range(nqubits):
        circuit.rx(qubit, np.random.rand())
        circuit.rz(qubit, np.random.rand())


def last_rotation(circuit, nqubits):
    for qubit in range(nqubits):
        circuit.rz(qubit, np.random.rand())


def entangler(circuit, pairs):
    for a, b in pairs:
        circuit.cnot(a, b)


def entangler_rzz(circuit, pairs):
    for a, b in pairs:
        circuit.rzz(a, b, np.random.rand())

def generate_gate(nqubits, depth, pairs, use_rzz=False):
    circuit = Circuit(nqubits)
    first_rotation(circuit, nqubits)
    entangler(circuit, pairs)
    for k in range(depth - 1):
        mid_rotation(circuit, nqubits)
        if use_rzz:
            entangler_rzz(circuit, pairs)
        else:
            entangler(circuit, pairs)
    last_rotation(circuit, nqubits)
    return circuit


class TestIBMQInterface(unittest.TestCase):
    def test_to_qiskit(self):
        nqubits = 5
        depth = 5
        pairs = [(i, np.mod(i + 1, nqubits)) for i in range(nqubits)]
        circuit = generate_gate(nqubits, depth, pairs)
        pattern = circuit.transpile()

        simulator = Aer.get_backend('aer_simulator')
        qiskit_circuit = pattern.to_qiskit(save_statevector = True) #to be modified
        qiskit_circuit = transpile(qiskit_circuit, simulator)
        
        state = pattern.simulate_pattern()
        result = simulator.run(qiskit_circuit).result()
        state_qiskit = result.get_statevector(qiskit_circuit)

        np.testing.assert_almost_equal(np.abs(np.dot(state_qiskit.conjugate(), state.flatten())), 1)


if __name__ == '__main__':
    unittest.main()