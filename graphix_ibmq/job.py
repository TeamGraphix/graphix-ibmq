from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qiskit.providers.jobstatus import JobStatus
from graphix_ibmq.result_utils import format_result

if TYPE_CHECKING:
    from qiskit_ibm_runtime.fake_provider.local_runtime_job import LocalRuntimeJob
    from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
    from graphix_ibmq.compiler import IBMQCompiledCircuit


@dataclass
class IBMQJob:
    """
    A handler for jobs submitted to IBMQ devices and simulators.

    This class wraps a Qiskit job object and the corresponding compiled circuit,
    providing methods to check the job's status and retrieve formatted results.
    """

    job: LocalRuntimeJob | RuntimeJobV2
    compiled_circuit: IBMQCompiledCircuit

    @property
    def id(self) -> str:
        """
        Returns the unique identifier of the job.

        Returns
        -------
        str
            The job ID.
        """
        job_id: str = self.job.job_id()
        return job_id

    @property
    def is_done(self) -> bool:
        """
        Checks if the job has completed execution.

        Returns
        -------
        bool
            True if the job is done, False otherwise.
        """
        is_done: bool = self.job.status() is JobStatus.DONE
        return is_done

    def retrieve_result(self, raw_result: bool = False) -> dict[str, int] | None:
        """
        Retrieves the result from a completed job.

        If the job is not yet complete, this method returns None.

        Parameters
        ----------
        raw_result : bool, optional
            If True, returns the raw measurement counts dictionary.
            If False (default), returns results formatted by the graphix pattern.

        Returns
        -------
        dict or None
            A dictionary containing the formatted results or raw counts.
            Returns None if the job has not yet finished.
        """
        if not self.is_done:
            return None

        # Result from SamplerV2 contains a list of pub_results.
        # We assume a single circuit was run, so we take the first element [0].
        result = self.job.result()
        counts: dict[str, int] = result[0].data.meas.get_counts()

        if raw_result:
            return counts

        return format_result(counts, self.compiled_circuit.pattern, self.compiled_circuit.register_dict)
