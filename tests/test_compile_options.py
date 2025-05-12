import pytest
from graphix_ibmq.compile_options import IBMQCompileOptions


def test_default_options():
    opts = IBMQCompileOptions()
    assert opts.optimization_level == 3
    assert opts.save_statevector is False
    assert opts.layout_method == "trivial"


def test_repr():
    opts = IBMQCompileOptions(optimization_level=2, save_statevector=True, layout_method="dense")
    expected = "IBMQCompileOptions(optimization_level=2, save_statevector=True, layout_method='dense')"
    assert repr(opts) == expected
