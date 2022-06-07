from os import path
import json

CURRENT_DIR = path.dirname(path.abspath(__file__))

with open(path.abspath(path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

extension_compile = "pas"
extension_run = "exe"

pathToCompiler = configs["COMPILER_PATHS"]["PASCAL"]


def mem_usage(mem):
    return mem.data


def cmd_compile(folder_path, program_name):
    return [pathToCompiler,  path.abspath(path.join(folder_path, f"{program_name}.{extension_compile}"))]


def cmd_run(folder_path, program_name):
    return ["mono",  path.abspath(path.join(folder_path, f"{program_name}.{extension_run}"))]


time_offset_code = "var i:integer; Begin i:=0;End."
memory_offset_code = "var i:integer; Begin while (true)  do i:=0; End."
