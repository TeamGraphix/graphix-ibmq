"""
Converting qiskit circuit to graphix circuit
====================================================================

In this example, we will demonstrate how to convert qiskit circuit to graphix circuit.

First, let us import relevant modules and define quantum circuit we want to convert:
"""


# %%
from IPython.display import display
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.random.utils import random_circuit

qc = random_circuit(5, 2, seed=42)

qc = transpile(qc, basis_gates=["rx", "rz", "cx"])
qc.draw("mpl", style="iqp")


# %%
# To convert the circuit, we just need to call :func:`~graphix_ibmq.converter.qiskit_to_graphix` function
# from :mod:`graphix_ibmq.converter` module.

from graphix_ibmq.converter import qiskit_to_graphix

gx_qc = qiskit_to_graphix(qc)
for inst in gx_qc.instruction:
    print(inst)

# %%
# You can confirm that the converted circuit is equivalent to the original circuit as follows:

from qiskit.quantum_info import Statevector

sv = Statevector.from_instruction(qc)
sv = sv.reverse_qargs()  # Note that qiskit and graphix use different qubit ordering

gx_qc = qiskit_to_graphix(qc)
gx_sv = gx_qc.simulate_statevector()
gx_sv = Statevector(gx_sv.flatten())

sv.equiv(gx_sv)
