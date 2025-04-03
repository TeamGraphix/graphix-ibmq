from graphix.device_interface import JobHandler


class IBMQJobHandler(JobHandler):
    """Job handler class for IBMQ devices and simulators."""

    def __init__(self, job) -> None:
        """
        Initialize with a Qiskit Runtime job object.

        Parameters
        ----------
        job : Any
            The job object returned from Qiskit Runtime or Aer Sampler.
        """
        self.job = job

    def get_id(self) -> str:
        """
        Get the unique identifier of the job.

        Returns
        -------
        str
            The job ID.
        """
        return self.job.job_id()

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
