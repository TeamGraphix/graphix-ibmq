from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IBMQCompileOptions:
    """Compilation options specific to IBMQ backends.

    Attributes
    ----------
    optimization_level : int
        Optimization level for Qiskit transpiler (0 to 3).
    save_statevector : bool
        Whether to save the statevector before measurement (for debugging/testing).
    layout_method : str
        Qubit layout method used by the transpiler (for future use).
    """

    optimization_level: int = 3
    save_statevector: bool = False
    layout_method: str = "trivial"

    def __repr__(self) -> str:
        """Return a string representation of the compilation options."""
        return (
            f"IBMQCompileOptions(optimization_level={self.optimization_level}, "
            f"save_statevector={self.save_statevector}, "
            f"layout_method='{self.layout_method}')"
        )
