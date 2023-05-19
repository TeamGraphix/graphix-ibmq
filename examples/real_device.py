"""
Converting MBQC pattern to qiskit circuit and execute it on IBMQ device
===================

"""

from graphix import Pattern, Circuit
from qiskit import IBMQ

# get the API token
IBMQ.save_account('MY_API_TOKEN', overwrite=True)
IBMQ.load_account()

