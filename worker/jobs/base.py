class BaseJob:

    def __init__(self, parameters: dict):
        self.parameters = parameters

    async def execute(self) -> dict:
        """Execute the job. To be implemented by subclasses."""
        raise NotImplementedError(
            "Execute method must be implemented by subclasses.")
