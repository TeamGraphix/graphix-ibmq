from graphix.device_interface import JobHandle


class IBMQJobHandle(JobHandle):
    def __init__(self, job):
        self.job = job

    def get_id(self) -> str:
        return self.job.job_id()

    def is_done(self) -> bool:
        return self.job.status().name == "DONE"

    def cancel(self) -> None:
        self.job.cancel()
        