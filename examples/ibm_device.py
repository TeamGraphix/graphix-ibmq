"""
Converting MBQC pattern to qiskit circuit and execute it on IBMQ device
===================

In this example, we will demonstrate how to convert MBQC pattern to qiskit circuit and execute it on real IBMQ device backend.
We use the 3-qubit QFT as an example.

First, let us import relevant modules and define additional gates and function we'll use:
"""
#%%
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import random
from graphix.transpiler import Circuit
from graphix_ibmq.backend import IBMQBackend
from qiskit.visualization import plot_histogram
from qiskit.providers.fake_provider import FakeLagos



def cp(circuit, theta, control, target):
    """Controlled phase gate, decomposed"""
    circuit.rz(control, theta / 2)
    circuit.rz(target, theta / 2)
    circuit.cnot(control, target)
    circuit.rz(target, -1 * theta / 2)
    circuit.cnot(control, target)


def swap(circuit, a, b):
    """swap gate, decomposed"""
    circuit.cnot(a, b)
    circuit.cnot(b, a)
    circuit.cnot(a, b)


#%%
# Now let us define a circuit to apply QFT to three-qubit state.

circuit = Circuit(3)
for i in range(3):
    circuit.h(i)

psi = {}
# prepare random state for each input qubit
for i in range(3):
    theta = random.uniform(0, np.pi)
    phi = random.uniform(0, 2 * np.pi)
    circuit.ry(i, theta)
    circuit.rz(i, phi)
    psi[i] = [np.cos(theta / 2), np.sin(theta / 2) * np.exp(1j * phi)]

# 8 dimension input statevector
input_state = [0] * 8
for i in range(8):
    i_str = f"{i:03b}"
    input_state[i] = psi[0][int(i_str[0])] * psi[1][int(i_str[1])] * psi[2][int(i_str[2])]

# QFT
circuit.h(0)
cp(circuit, np.pi / 2, 1, 0)
cp(circuit, np.pi / 4, 2, 0)
circuit.h(1)
cp(circuit, np.pi / 2, 2, 1)
circuit.h(2)
swap(circuit, 0, 2)

# transpile and plot the graph
pattern = circuit.transpile().pattern
nodes, edges = pattern.get_graph()
g = nx.Graph()
g.add_nodes_from(nodes)
g.add_edges_from(edges)
np.random.seed(100)
nx.draw(g)
plt.show()

#%%
# Now let us convert the pattern to qiskit circuit.

# minimize the space to save memory during aer simulation.
pattern.minimize_space()

# convert to qiskit circuit
backend = IBMQBackend()
compiled = backend.compile(pattern)

#%%
# load the account with API token
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(channel="ibm_quantum", token="API TOKEN", overwrite=True)

# get the device backend
backend.select_device()

#%%
# We can now execute the circuit on the device backend.

job = backend.submit_job(compiled, shots=1024)

#%%
# Retrieve the job result

if job.is_done:
    result = job.retrieve_result()

#%%
# We can simulate the circuit with device-based noise model.

# get the noise model of the device backend
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
backend.set_simulator(based_on=FakeManilaV2())

# execute noisy simulation and get counts
job = backend.submit_job(compiled, shots=1024)
result_noise = job.retrieve_result()

#%%
# Now let us compare the results with theoretical output

# calculate the theoretical output state
state = [0] * 8
omega = np.exp(1j * np.pi / 4)

for i in range(8):
    for j in range(8):
        state[i] += input_state[j] * omega ** (i * j) / 2**1.5

# calculate the theoretical counts
count_theory = {}
for i in range(2**3):
    count_theory[f"{i:03b}"] = 1024 * np.abs(state[i]) ** 2

# plot and compare the results
fig, ax = plt.subplots(figsize=(7,5))
plot_histogram(
    [count_theory, result, result_noise],
    legend=["theoretical probability", "execution result", "Aer simulation w/ noise model"],
    ax=ax,
    bar_labels=False
)
legend = ax.legend(fontsize=18)
legend = ax.legend(loc='upper left')
