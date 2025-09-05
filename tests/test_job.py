import pytest

import graphix_ibmq.job as job_module

from graphix_ibmq.job import IBMQJob
from qiskit.providers.jobstatus import JobStatus


class FakeMeas:
    def __init__(self, counts: dict[str, int]):
        self._counts = counts

    def get_counts(self) -> dict[str, int]:
        return dict(self._counts)


class FakeData:
    def __init__(self, counts: dict[str, int]):
        self.meas = FakeMeas(counts)


class FakePubResult:
    def __init__(self, counts: dict[str, int]):
        self.data = FakeData(counts)


class FakeJobDone:
    def __init__(self, job_id: str, counts: dict[str, int]):
        self._job_id = job_id
        self._pub_results = [FakePubResult(counts)]

    def job_id(self) -> str:
        return self._job_id

    def status(self):
        return JobStatus.DONE

    def result(self):
        return self._pub_results


class FakeJobRunning(FakeJobDone):
    def status(self):
        return JobStatus.RUNNING


class FakeCompiledCircuit:
    def __init__(self):
        self.pattern = object()
        self.register_dict = {"out": [0, 1, 2]}


@pytest.fixture
def counts():
    return {"000": 10, "011": 5, "101": 7}


def test_id_property_returns_job_id(counts):
    fake = FakeJobDone("ABC123", counts)
    job = IBMQJob(job=fake, compiled_circuit=FakeCompiledCircuit())
    assert job.id == "ABC123"


def test_is_done_true_false(counts):
    job_done = IBMQJob(
        job=FakeJobDone("ID", counts), compiled_circuit=FakeCompiledCircuit()
    )
    job_run = IBMQJob(
        job=FakeJobRunning("ID", counts), compiled_circuit=FakeCompiledCircuit()
    )
    assert job_done.is_done is True
    assert job_run.is_done is False


def test_retrieve_result_returns_none_if_not_done(counts):
    job = IBMQJob(
        job=FakeJobRunning("ID", counts), compiled_circuit=FakeCompiledCircuit()
    )
    assert job.retrieve_result() is None
    assert job.retrieve_result(raw_result=True) is None


def test_retrieve_result_raw_counts_path_hits_get_counts(counts, monkeypatch):
    called = {"format_called": False}

    def fake_format_result(_counts, _pattern, _reg):
        called["format_called"] = True
        return {"should_not_be_returned": 1}

    monkeypatch.setattr(job_module, "format_result", fake_format_result)

    job = IBMQJob(job=FakeJobDone("ID", counts), compiled_circuit=FakeCompiledCircuit())
    out = job.retrieve_result(raw_result=True)
    assert out == counts
    assert called["format_called"] is False


def test_retrieve_result_formatted_path_calls_format_result(counts, monkeypatch):
    received = {}

    def fake_format_result(_counts, _pattern, _reg):
        received["counts"] = _counts
        received["pattern"] = _pattern
        received["register_dict"] = _reg
        return {"formatted": sum(_counts.values())}

    monkeypatch.setattr(job_module, "format_result", fake_format_result)

    fake_compiled = FakeCompiledCircuit()
    job = IBMQJob(job=FakeJobDone("ID", counts), compiled_circuit=fake_compiled)
    out = job.retrieve_result(raw_result=False)

    assert out == {"formatted": sum(counts.values())}
    assert received["counts"] == counts
    assert received["pattern"] is fake_compiled.pattern
    assert received["register_dict"] is fake_compiled.register_dict
