from __future__ import annotations

from graphix_ibmq.result_utils import format_result

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit_ibm_runtime.fake_provider.local_runtime_job import LocalRuntimeJob
    from qiskit_ibm_runtime.runtime_job_v2 import RuntimeJobV2
    from graphix_ibmq.compiler import IBMQPatternCompiler


class IBMQJob:
    """Job handler class for IBMQ devices and simulators."""

    def __init__(
        self,
        job: LocalRuntimeJob | RuntimeJobV2,
        compiler: IBMQPatternCompiler,
    ) -> None:
        """
        Parameters
         ----------
        job : LocalRuntimeJob | RuntimeJobV2
            The job object returned from Qiskit Runtime or real v2 runtime.
        """
        self.job = job
        self._compiler = compiler

    @property
    def get_id(self) -> str:
        """
        Get the unique identifier of the job.

        Returns
        -------
        str
            The job ID.
        """
        return self.job.job_id()

    @property
    def is_done(self) -> bool:
        """
        Check whether the job is completed.

        Returns
        -------
        bool
            True if the job is done, False otherwise.
        """
        status = self.job.status()
        if isinstance(status, str):
            return status.upper() == "DONE"
        return status.name == "DONE"

    def retrieve_result(self, raw_result: bool = False):
        """Retrieve the result from a completed job.

        Parameters
        ----------
        job : Job
            Handle to the executed job.
        raw_result : bool, optional
            If True, return raw counts; otherwise, return formatted results.

        Returns
        -------
        dict or Any
            Formatted result or raw counts from the job.

        Raises
        ------
        TypeError
            If the job handle is not an instance of IBMQJob.
        """

        if not self.is_done:
            # job not completed yet; skip retrieval
            return None

        result = self.job.result()
        counts = result[0].data.meas.get_counts()

        if not raw_result:
            return format_result(counts, self._compiler._pattern, self._compiler._register_dict)
        return counts
