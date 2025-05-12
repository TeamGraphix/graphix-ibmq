from dataclasses import dataclass
from graphix.device_interface import CompileOptions


@dataclass
class IBMQCompileOptions(CompileOptions):
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

    def __init__(
        self,
        optimization_level: int = 3,
        save_statevector: bool = False,
        layout_method: str = "trivial",
    ) -> None:
        """Initialize the compilation options.

        Parameters
        ----------
        optimization_level : int
            Optimization level for Qiskit transpiler (0 to 3).
        save_statevector : bool
            Whether to save the statevector before measurement (for debugging/testing).
        layout_method : str
            Qubit layout method used by the transpiler (for future use).
        """
        self.optimization_level = optimization_level
        self.save_statevector = save_statevector
        self.layout_method = layout_method

    def __repr__(self) -> str:
        """Return a string representation of the compilation options."""
        return (
            f"IBMQCompileOptions(optimization_level={self.optimization_level}, "
            f"save_statevector={self.save_statevector}, "
            f"layout_method='{self.layout_method}')"
        )
