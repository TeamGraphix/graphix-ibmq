from __future__ import annotations
from dataclasses import dataclass

import numpy as np
from qiskit import ClassicalRegister, QuantumRegister, QuantumCircuit

from graphix.command import Command, CommandKind, N, M, E, X, Z, C
from graphix.fundamentals import Plane
from qiskit.circuit.classical import expr

from typing import TYPE_CHECKING, Callable, Mapping, Sequence, Iterable

if TYPE_CHECKING:
    from graphix.pattern import Pattern

CommandHandler = Callable[[Command], None]

class IBMQPatternCompiler:
    def __init__(self, pattern: Pattern) -> None:
        """
        Initializes the compiler with a given pattern.

        Parameters
        ----------
        pattern : Pattern
            The measurement-based quantum computation pattern.
        """
        self._pattern = pattern

        num_qubits = self._pattern.max_space()
        num_nodes = self._pattern.n_node

        qr = QuantumRegister(num_qubits)
        self._classical_register = ClassicalRegister(num_nodes, name="meas")
        self._circuit = QuantumCircuit(qr, self._classical_register)

        self._available_qubits = list(range(num_qubits))
        self._qubit_map: dict[int, int] = {}
        self._creg_map: dict[int, int] = {}
        self._next_creg_idx: int = 0

        for node_idx in self._pattern.input_nodes:
            circ_idx = self._allocate_qubit(node_idx)
            self._circuit.h(circ_idx)

    def compile(self, save_statevector: bool = False) -> IBMQCompiledCircuit:
        """
        Converts the MBQC pattern into a Qiskit QuantumCircuit.

        Parameters
        ----------
        save_statevector : bool
            If True, saves the statevector before output measurement.

        Returns
        -------
        IBMQCompiledCircuit
            A data class containing the compiled circuit and associated metadata.
        """
        self._process_commands()
        output_qubits = self._finalize_circuit(save_statevector)

        return IBMQCompiledCircuit(
            circuit=self._circuit,
            pattern=self._pattern,
            register_dict=self._creg_map,
            circ_output=output_qubits,
        )

    def _process_commands(self) -> None:
        """Iterates through and processes all commands in the pattern."""
        for cmd in self._pattern:  # Iterable[Command]
            if isinstance(cmd, N):
                self._apply_n(cmd)
            elif isinstance(cmd, E):
                self._apply_e(cmd)
            elif isinstance(cmd, M):
                self._apply_m(cmd)
            elif isinstance(cmd, X):
                self._apply_x(cmd)
            elif isinstance(cmd, Z):
                self._apply_z(cmd)
            elif isinstance(cmd, C):
                self._apply_c(cmd)

    def _allocate_qubit(self, node_idx: int) -> int:
        """Allocates a qubit from the pool, resets it, and maps it to a node."""
        if not self._available_qubits:
            raise RuntimeError("No available qubits to allocate.")
        circ_idx = self._available_qubits.pop(0)
        self._circuit.reset(circ_idx)
        self._qubit_map[node_idx] = circ_idx
        return circ_idx

    def _release_qubit(self, circ_idx: int) -> None:
        """Releases a qubit, making it available for reuse."""
        self._available_qubits.append(circ_idx)

    def _apply_n(self, cmd: N) -> None:
        """Handles the N command: create a new qubit in the |+> state."""
        circ_idx = self._allocate_qubit(cmd.node)
        self._circuit.h(circ_idx)

    def _apply_e(self, cmd: E) -> None:
        """Handles the E command: apply a CZ gate between two qubits."""
        qubit1 = self._qubit_map[cmd.nodes[0]]
        qubit2 = self._qubit_map[cmd.nodes[1]]
        self._circuit.cz(qubit1, qubit2)

    def _apply_m(self, cmd: M) -> None:
        """Handles the M command: perform a measurement."""
        if cmd.plane != Plane.XY:
            raise NotImplementedError("Non-XY plane measurements are not supported.")

        circ_idx = self._qubit_map[cmd.node]

        self._apply_classical_feedforward("X", circ_idx, cmd.s_domain)
        self._apply_classical_feedforward("Z", circ_idx, cmd.t_domain)

        if cmd.angle != 0:
            self._circuit.p(-cmd.angle * np.pi, circ_idx)

        self._circuit.h(circ_idx)
        self._circuit.measure(circ_idx, self._next_creg_idx)

        self._creg_map[cmd.node] = self._next_creg_idx
        self._next_creg_idx += 1
        self._release_qubit(circ_idx)

    def _apply_x(self, cmd: X) -> None:
        """Handles the X command: apply a Pauli X correction."""
        circ_idx = self._qubit_map[cmd.node]
        self._apply_classical_feedforward("X", circ_idx, cmd.domain)

    def _apply_z(self, cmd: Z) -> None:
        """Handles the Z command: apply a Pauli Z correction."""
        circ_idx = self._qubit_map[cmd.node]
        self._apply_classical_feedforward("Z", circ_idx, cmd.domain)

    def _apply_c(self, cmd: C) -> None:
        """Handles the C command: apply a custom Qiskit circuit method."""
        circ_idx = self._qubit_map[cmd.node]
        for method_name in cmd.clifford.qasm3:
            getattr(self._circuit, method_name)(circ_idx)

    def _apply_classical_feedforward(self, op: str, target_qubit: int, domain: Iterable[int]) -> None:
        """Applies classically-controlled X or Z gates based on measurement outcomes."""
        gate_map = {"X": self._circuit.x, "Z": self._circuit.z}
        if op not in gate_map:
            return

        apply_gate = gate_map[op]

        for node_idx in domain:
            if node_idx in self._creg_map:
                creg_idx = self._creg_map[node_idx]
                clbit = self._classical_register[creg_idx]
                cond = expr.equal(clbit, True)
                with self._circuit.if_test(cond):
                    apply_gate(target_qubit)
            elif self._pattern.results.get(node_idx) == 1:
                apply_gate(target_qubit)

    def _finalize_circuit(self, save_statevector: bool) -> list[int]:
        """Handles output measurements and optional statevector saving."""
        output_qubits = [self._qubit_map[node] for node in self._pattern.output_nodes]

        if save_statevector:
            self._circuit.save_statevector()

        for node in self._pattern.output_nodes:
            circ_idx = self._qubit_map[node]
            self._circuit.measure(circ_idx, self._next_creg_idx)
            self._creg_map[node] = self._next_creg_idx
            self._next_creg_idx += 1

        return output_qubits if save_statevector else []


@dataclass
class IBMQCompiledCircuit:
    """A compiled circuit with its associated pattern and register mapping.

    Attributes
    ----------
    circuit : QuantumCircuit
        The Qiskit quantum circuit generated from the pattern.
    register_dict : Mapping[int, int]
        Mapping from pattern node indices to classical register indices.
    circ_output : Sequence[int]
        List of output qubit indices in the compiled circuit.
    """

    circuit: QuantumCircuit
    pattern: Pattern
    register_dict: Mapping[int, int]
    circ_output: Sequence[int]
