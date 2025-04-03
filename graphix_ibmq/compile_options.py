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

    optimization_level: int = 1
    save_statevector: bool = False
    layout_method: str = "dense"
