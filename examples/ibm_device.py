"""
Converting MBQC pattern to qiskit circuit and execute it on IBMQ device
===================

In this example, we will demonstrate how to convert MBQC pattern to qiskit circuit and execute it on real IBMQ device backend.
We use the 3-qubit QFT as an example.

First, let us import relevant modules and define additional gates and function we'll use:
"""

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import random
from graphix import Circuit
from graphix_ibmq.runner import IBMQBackend
from qiskit import IBMQ, transpile
from qiskit_ibm_provider import IBMProvider
from qiskit.tools.visualization import plot_histogram
from qiskit_aer import AerSimulator
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

def format_result(pattern, result):
    """Format the result so that only the result corresponding to the output qubit is taken out.

    Returns
    -------
    masked_results : dict
        Dictionary of formatted results.
    """
    masked_results = {} 
    N_node = pattern.Nnode + len(pattern.results)

    # Iterate over original measurement results
    for key, value in result.get_counts().items():
        masked_key = ""
        for idx in pattern.output_nodes:
            masked_key +=  key[N_node - idx - 1]
        if masked_key in masked_results:
            masked_results[masked_key] += value
        else:
            masked_results[masked_key] = value

    return masked_results

#%%
# Now let us define a circuit to apply QFT to three-qubit state.

circuit = Circuit(3)
for i in range(3):
    circuit.h(i)

psi = {}
# prepare random state for each input qubit
for i in range(3):
    theta = random.uniform(0, np.pi)
    phi = random.uniform(0, 2*np.pi)
    circuit.ry(i, theta)
    circuit.rz(i, phi)
    psi[i] = [np.cos(theta/2), np.sin(theta/2)*np.exp(1j*phi)]

# 8 dimension input statevector
input_state = [0]*8 
for i in range(8): 
    i_str = f"{i:03b}"
    input_state[i] = psi[0][int(i_str[0])]*psi[1][int(i_str[1])]*psi[2][int(i_str[2])]

# QFT
circuit.h(0)
cp(circuit, np.pi / 2, 1, 0)
cp(circuit, np.pi / 4, 2, 0)
circuit.h(1)
cp(circuit, np.pi / 2, 2, 1)
circuit.h(2)
swap(circuit, 0, 2)

# transpile and plot the graph
pattern = circuit.transpile()
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
backend = IBMQBackend(pattern)
backend.to_qiskit()
print(type(backend.circ))

#%%
# Get the API token and load the IBMQ acount.

IBMQ.save_account('MY_API_TOKEN', overwrite=True)
IBMQ.load_account()

#%%
# Get provider and the backend.

instance_name = 'ibm-q/open/main'
backend_name = "ibm_lagos"

provider = IBMProvider(instance=instance_name)
backend = provider.get_backend(backend_name)
print(f"Using backend {backend.name}")

#%%
# We can now execute the circuit on the device backend.

circ_device = transpile(backend.circ, backend)
job = backend.run(circ_device, shots=1024, dynamic=True)
print(f"Your job's id: {job.job_id()}")
result = format_result(job.result())

#%%
# Retrieve the job if needed

# job = provider.backend.retrieve_job("Job ID")
# result = format_result(job.result())

#%%
# We can simulate the circuit with noise model based on the device we used

# get the noise model of the device backend
backend_noisemodel = FakeLagos()
sim_noise = AerSimulator.from_backend(backend_noisemodel)

# transpile the circuit for the noisy basis gates
circ_noise = transpile(backend.circ, sim_noise)
# execute noisy simulation and get counts
result_noise = format_result(pattern, sim_noise.run(circ_noise).result())

#%%
# Now let us compare the results with theoretical output

# calculate the theoretical output state
state = [0]*8
omega = np.exp(1j*np.pi/4)

for i in range(8):
    for j in range(8):
        state[i] += input_state[j]*omega**(i*j)/2**1.5

# calculate the theoretical counts
count_theory = {}
for i in range(2**3):
    count_theory[f"{i:03b}"] = 1024*np.abs(state[i])**2

# plot and compare the results
plot_histogram(
    [count_theory, result, result_noise],
    legend=["theoretical probability", "execution results", "aer simulation with noise model"],
)
