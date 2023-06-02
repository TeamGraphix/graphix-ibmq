import numpy as np

# Conjugation of Clifford gates result in a Clifford gate.
# CLIFFORD_CONJ provides the Clifford index of conjugated matrix.
# Example (S and S dagger):  CLIFFORD_CONJ[4]
# see graphix.clifford module for the definitions and details of Clifford operatos for each index.
CLIFFORD_CONJ = np.array(
    [0, 1, 2, 3, 5, 4, 6, 15, 12, 9, 10, 11, 8, 13, 14, 7, 20, 22, 23, 21, 16, 19, 17, 18], dtype=np.int32
)

# qiskit representation of Clifford gates above.
# see graphix.clifford module for the definitions and details of Clifford operatos for each index.
CLIFFORD_TO_QISKIT = [
    ["id"],
    ["x"],
    ["y"],
    ["z"],
    ["s"],
    ["sdg"],
    ["h"],
    ["sdg", "h", "sdg"],
    ["h", "x"],
    ["sdg", "y"],
    ["sdg", "x"],
    ["h", "y"],
    ["h", "z"],
    ["sdg", "h", "sdg", "y"],
    ["sdg", "h", "s"],
    ["sdg", "h", "sdg", "x"],
    ["sdg", "h"],
    ["sdg", "h", "y"],
    ["sdg", "h", "z"],
    ["sdg", "h", "x"],
    ["h", "s"],
    ["h", "sdg"],
    ["h", "x", "sdg"],
    ["h", "x", "s"],
]
