from os import path
import json

CURRENT_DIR = path.dirname(path.abspath(__file__))

with open(path.abspath(path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

extension_compile = "py"
extension_run = "py"


def mem_usage(mem):
    return mem.data


def cmd_compile(folder_path, program_name):
    return [
        "python",
        "-m",
        "py_compile",
        path.abspath(path.join(folder_path, f"{program_name}.{extension_compile}")),
    ]


def cmd_run(folder_path, program_name):
    return ["python", path.abspath(path.join(folder_path, f"{program_name}.{extension_run}"))]


time_offset_code = "a = 0"
memory_offset_code = "while True: \n\t a = 0"
