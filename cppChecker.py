from os import path
import json

CURRENT_DIR = path.dirname(path.abspath(__file__))

with open(path.abspath(path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

extension_compile = "cpp"
extension_run = "exe"

pathToCompiler = configs["COMPILER_PATHS"]["CPP"]


def cmd_compile(folder_path, program_name):
    return [
        pathToCompiler,
        "-o",
        path.abspath(path.join(folder_path, program_name)),
        path.abspath(path.join(folder_path, f"{program_name}.{extension_compile}")),
    ]


def cmd_run(folder_path, program_name):
    return [path.abspath(path.join(folder_path, f"{program_name}"))]


# def cmd_run(folder_path, program_name):
#   return [path.abspath(path.join(folder_path, f'{program_name}.{extension_run}'))]
