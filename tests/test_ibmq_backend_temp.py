import unittest
import numpy as np
import networkx as nx
from graphix.transpiler import Circuit
from graphix_ibmq.backend import IBMQBackend
import qiskit.quantum_info as qi

class TestIBMQBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # IBMQBackendを一度初期化
        cls.backend = IBMQBackend()

    def test_backend_initialization(self):
        """Backendが正しく初期化されるか"""
        self.assertIsInstance(self.backend, IBMQBackend)

    def test_run_simple_pattern(self):
        """簡単な2qubit QFTパターンでrunできるか"""
        n = 2
        circuit = Circuit(n)
        self._qft(circuit, n)
        pattern = circuit.transpile().pattern
        pattern.minimize_space()

        result = self.backend.run(pattern, shots=1024)
        self.assertIsInstance(result, dict)
        self.assertTrue(len(result) > 0)

    def test_result_matches_theory(self):
        """実行結果が理論分布と大きくずれていないか"""
        n = 2
        circuit = Circuit(n)
        self._qft(circuit, n)
        pattern = circuit.transpile().pattern
        pattern.minimize_space()

        result = self.backend.run(pattern, shots=1024)

        # 理想結果を計算
        qc = circuit.to_qiskit()
        ideal = qi.Statevector.from_instruction(qc)
        probs = ideal.probabilities_dict()

        # 実機結果を正規化
        total_shots = sum(result.values())
        exp_probs = {k: v / total_shots for k, v in result.items()}

        # L1ノルム (差の総和) が小さいかチェック
        l1_distance = sum(abs(exp_probs.get(k, 0) - probs.get(k, 0)) for k in set(probs) | set(exp_probs))
        self.assertLess(l1_distance, 0.3)  # 許容誤差: 30%

    def test_invalid_option(self):
        """不正な引数でエラーになるか"""
        n = 2
        circuit = Circuit(n)
        self._qft(circuit, n)
        pattern = circuit.transpile().pattern

        with self.assertRaises(TypeError):
            # わざと不正なオプションを渡す
            self.backend.run(pattern, shots="invalid")

    @staticmethod
    def _qft(circuit, n):
        """QFT生成（テスト内関数）"""
        for i in range(n):
            TestIBMQBackend._qft_rotations(circuit, i)
        TestIBMQBackend._swap_registers(circuit, n)

    @staticmethod
    def _qft_rotations(circuit, n):
        if n == circuit.width:
            return
        circuit.h(n)
        for qubit in range(n+1, circuit.width):
            theta = np.pi / 2 ** (qubit - n)
            TestIBMQBackend._cp(circuit, theta, qubit, n)

    @staticmethod
    def _cp(circuit, theta, control, target):
        circuit.rz(control, theta / 2)
        circuit.rz(target, theta / 2)
        circuit.cnot(control, target)
        circuit.rz(target, -theta / 2)
        circuit.cnot(control, target)

    @staticmethod
    def _swap_registers(circuit, n):
        for qubit in range(n // 2):
            TestIBMQBackend._swap(circuit, qubit, n - qubit - 1)

    @staticmethod
    def _swap(circuit, a, b):
        circuit.cnot(a, b)
        circuit.cnot(b, a)
        circuit.cnot(a, b)
