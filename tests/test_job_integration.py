# tests/test_job_integration.py
import time
import pytest

pytest.importorskip("qiskit_aer")
pytest.importorskip("qiskit_ibm_runtime")
pytest.importorskip("graphix")
pytest.importorskip("graphix_ibmq")

from graphix.transpiler import Circuit
from graphix_ibmq.backend import IBMQBackend
from graphix_ibmq.job import IBMQJob


@pytest.mark.integration
def test_retrieve_result_real_qiskit_aer_chain(tmp_path):
    # 1) 1qubit H
    circ = Circuit(1)
    circ.h(0)

    pattern = circ.transpile().pattern
    pattern.minimize_space()

    backend = IBMQBackend.from_simulator()
    compiled = backend.compile(pattern)

    shots = 256
    ibmq_job = backend.submit_job(compiled, shots=shots)

    job = IBMQJob(job=ibmq_job.job, compiled_circuit=compiled)

    deadline = time.time() + 30
    while not job.is_done and time.time() < deadline:
        time.sleep(0.05)
    assert job.is_done, "Job did not reach DONE within timeout"

    counts_raw = job.retrieve_result(raw_result=True)
    assert isinstance(counts_raw, dict)

    out_bits = len(compiled.register_dict.get("out", []))
    if out_bits == 0 and len(counts_raw) > 0:
        out_bits = len(next(iter(counts_raw.keys())))
    assert out_bits >= 1
    assert all(isinstance(k, str) and len(k) == out_bits for k in counts_raw.keys())
    assert sum(counts_raw.values()) == shots

    counts_formatted = job.retrieve_result(raw_result=False)
    assert isinstance(counts_formatted, dict)
    assert len(counts_formatted) >= 1
