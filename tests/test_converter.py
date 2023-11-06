import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.random.utils import random_circuit
from qiskit.quantum_info import Statevector

from graphix_ibmq.converter import qiskit_to_graphix


class TestConverter(unittest.TestCase):
    def test_qiskit_to_graphix(self):
        qc = random_circuit(5, 2, seed=42)
        qc = transpile(qc, basis_gates=["rx", "rz", "cx"])
        gx_qc = qiskit_to_graphix(qc)
        sv = Statevector.from_instruction(qc)
        sv = sv.reverse_qargs()
        gx_sv = gx_qc.simulate_statevector()
        gx_sv = Statevector(gx_sv.flatten())
        self.assertTrue(sv.equiv(gx_sv))
