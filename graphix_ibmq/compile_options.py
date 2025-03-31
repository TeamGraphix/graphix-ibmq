from dataclasses import dataclass
from graphix.device_interface import CompileOptions


@dataclass
class IBMQCompileOptions(CompileOptions):
    optimization_level: int = 1
    save_statevector: bool = False
    layout_method: str = "dense"
    