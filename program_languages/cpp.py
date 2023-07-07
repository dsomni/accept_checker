"""Contains Cpp Language class"""

from os import path


from program_languages.basic import ProgramLanguage


class CppLanguage(ProgramLanguage):
    """Cpp language class"""

    def __init__(self):
        super().__init__()
        self.compiler_path: str = "g++"

    def get_offset_codes(self):
        return (
            "int main()\n{\nint a = 0;\nreturn 0;\n }",
            "int main()\n{\nwhile(true){}\nreturn 0;\n }",
        )

    def get_compile_extension(self):
        return "cpp"

    def get_run_extension(self):
        return "exe"

    def get_memory_usage(self, memory_info):
        return memory_info.data

    def get_cmd_compile(self, folder_path: str, program_name: str):
        return [
            self.compiler_path,
            "-o",
            path.abspath(path.join(folder_path, program_name)),
            path.abspath(
                path.join(folder_path, f"{program_name}.{self.get_compile_extension()}")
            ),
        ]

    def get_cmd_run(self, folder_path: str, program_name: str):
        return [path.abspath(path.join(folder_path, f"{program_name}"))]


CPP_LANGUAGE = CppLanguage()