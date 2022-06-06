from os import path
import json

CURRENT_DIR = path.dirname(path.abspath(__file__))

with open(path.abspath(path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

extension_compile = "java"
extension_run = "java"

pathToCompiler = configs["COMPILER_PATHS"]["JAVA"]


def mem_usage(mem):
    return mem.rss


def cmd_compile(folder_path, program_name):
    return [pathToCompiler, path.abspath(path.join(folder_path, f"{program_name}.{extension_compile}"))]


def cmd_run(folder_path, program_name):
    return ["java", path.abspath(path.join(folder_path, f"{program_name}.{extension_run}"))]


time_offset_code = "class Main\n{ public static void main(String args[])\n  {\n    int a;\n  }\n}"
memory_offset_code = "class Main\n{ public static void main(String args[])\n  {\n    while(true){}\n  }\n}"
