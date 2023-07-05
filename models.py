"""Contains data models"""


class PendingQueueItem:
    """Pending queue item model"""

    def __init__(self, item_dict: dict) -> None:
        self.task_type: int = item_dict["taskType"]
        self.task_check_type: int = item_dict["taskCheckType"]
        self.checker: dict = item_dict["checker"]

    def to_dict(self) -> dict:
        """Converts class to dict object

        Returns:
            dict
        """
        return {
            "taskType": self.task_type,
            "taskCheckType": self.task_check_type,
            "checker": self.checker,
        }


class Attempt:
    """Attempt model"""

    class Constraints:
        """Constraints model"""

        def __init__(self, constraints_dict: dict):
            self.time = constraints_dict["time"]
            self.memory = constraints_dict["memory"]

        def to_dict(self):
            """Converts class to dict object

            Returns:
                dict
            """
            return {
                "time": self.time,
                "memory": self.memory,
            }

    class Result:
        """Attempt result model"""

        class Test:
            """Result test model"""

            def __init__(self, test_dict: dict) -> None:
                self.input_data: str = test_dict["inputData"]
                self.output_data: str = test_dict["outputData"]

            def to_dict(self):
                """Converts class to dict object

                Returns:
                    dict
                """
                return {"inputData": self.input_data, "outputData": self.output_data}

        def __init__(self, result_dict: dict):
            self.test = self.Test(result_dict["test"])
            self.verdict: int = result_dict["verdict"]

        def to_dict(self):
            """Converts class to dict object

            Returns:
                dict
            """
            return {
                "test": self.test.to_dict(),
                "verdict": self.verdict,
            }

    def __init__(self, attempt_dict: dict):
        self.spec: str = attempt_dict["spec"]
        self.language: str = attempt_dict["language"]
        self.status: int = attempt_dict["status"]
        self.constraints = self.Constraints(attempt_dict["constraints"])
        self.program_text: str = attempt_dict["programText"]
        self.text_answers: list[str] = attempt_dict["textAnswers"]
        self.date: str = attempt_dict["date"]
        self.results = [self.Result(result) for result in attempt_dict["results"]]
        self.verdict: int = attempt_dict["verdict"]
        self.logs: list[str] = attempt_dict["logs"]

    def to_dict(self):
        """Converts class to dict object

        Returns:
            dict
        """
        return {
            "spec": self.spec,
            "language": self.language,
            "status": self.status,
            "constraints": self.constraints.to_dict(),
            "program_text": self.program_text,
            "textAnswers": self.text_answers,
            "date": self.date,
            "results": self.results,
            "verdict": self.verdict,
            "logs": self.logs,
        }


class Language:
    """Language model"""

    def __init__(self, language_dict: dict):
        self.spec: str = language_dict["spec"]

        self.short_name: str = language_dict["shortName"]
        self.run_offset: float = language_dict["runOffset"]
        self.compile_offset: float = language_dict["compileOffset"]
        self.mem_offset: float = language_dict["memOffset"]

    def to_dict(self):
        """Converts class to dict object

        Returns:
            dict
        """
        return {
            "spec": self.spec,
            "shortName": self.short_name,
            "runOffset": self.run_offset,
            "compileOffset": self.compile_offset,
            "memOffset": self.mem_offset,
        }
