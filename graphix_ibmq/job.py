from graphix_ibmq.result_utils import format_result


class IBMQJob:
    """Job handler class for IBMQ devices and simulators."""

    def __init__(self, job, compiler) -> None:
        """
        Initialize with a Qiskit Runtime job object.

        Parameters
        ----------
        job : Any
            The job object returned from Qiskit Runtime or Aer Sampler.
        """
        self.job = job
        self._compiler = compiler

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
        try:
            # Simulator jobs typically use .status().name
            return self.job.status().name == "DONE"
        except AttributeError:
            # Hardware jobs may return status as a string
            return str(self.job.status()).upper() == "DONE"

    def cancel(self) -> None:
        """
        Cancel the job if it's still running.
        """
        self.job.cancel()

    def get_status(self) -> str:
        """
        Get the current status of the job.

        Returns
        -------
        str
            Status string representing the job state.
        """
        return self.job.status()

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
            print("Job not done.")
            return None

        result = self.job.result()
        counts = result[0].data.meas.get_counts()

        if not raw_result:
            return format_result(counts, self._compiler._pattern, self._compiler._register_dict)
        return counts
