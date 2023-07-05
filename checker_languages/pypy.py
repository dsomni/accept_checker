"""Contains Pypy Language class"""

from os import path

from checker_languages.basic import CheckerLanguage


class PypyLanguage(CheckerLanguage):
    """Pypy language class"""

    def __init__(self):
        super().__init__()
        self.compiler_path: str = "pypy3"

    def get_offset_codes(self):
        return "a = 0", "while True: \n\t a = 0"

    def get_compile_extension(self):
        return "py"

    def get_run_extension(self):
        return "py"

    def get_memory_usage(self, memory_info):
        return memory_info.data

    def get_cmd_compile(self, folder_path: str, program_name: str):
        return [
            self.compiler_path,
            "-m",
            "py_compile",
            path.abspath(
                path.join(folder_path, f"{program_name}.{self.get_compile_extension()}")
            ),
        ]

    def get_cmd_run(self, folder_path: str, program_name: str):
        return [
            self.compiler_path,
            path.abspath(
                path.join(folder_path, f"{program_name}.{self.get_run_extension()}")
            ),
        ]


PYPY_LANGUAGE = PypyLanguage()
