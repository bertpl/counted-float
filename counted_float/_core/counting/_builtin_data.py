from importlib.resources import files

from counted_float._core.counting.models import FlopsBenchmarkResults, InstructionLatencies


class BuiltInData:
    """
    A class that provides access to built-in data for the counted_float package.
    """

    @classmethod
    def benchmarks(cls) -> dict[str, FlopsBenchmarkResults]:
        return {
            file.stem: FlopsBenchmarkResults.model_validate_json(file.read_text())
            for file in files("counted_float._core.data.benchmarks").iterdir()
            if file.is_file() and file.name.endswith(".json")
        }

    @classmethod
    def specs(cls) -> dict[str, InstructionLatencies]:
        return {
            file.stem: InstructionLatencies.model_validate_json(file.read_text())
            for file in files("counted_float._core.data.specs").iterdir()
            if file.is_file() and file.name.endswith(".json")
        }
