import importlib.util
import json
import os

from checker import checker
import motor.motor_asyncio
import asyncio

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    langs_configs = json.load(file)["LANGS"]


def check_module(module_name):
    module_name = module_name
    module_spec = importlib.util.find_spec(module_name)
    if module_spec is None:
        return None
    else:
        return module_spec


def import_module_from_spec(module_spec):
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def get_module(lang):
    global langs_configs
    module_name = langs_configs[lang]
    module_spec = check_module(module_name)
    return module_name, module_spec


def get_extension(module_spec):
    module = import_module_from_spec(module_spec)
    return module.extension_compile


def create_program_file(folder, program_name, extension, programText):
    path = os.path.abspath(os.path.join(CURRENT_DIR, folder, f"{program_name}.{extension}"))
    with open(path, "w") as program:
        program.write(programText)
    return path


def delete_program_file(program_path):
    os.remove(program_path)


FOLDER = "programs"


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
configs = {}
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

client = motor.motor_asyncio.AsyncIOMotorClient(configs["database"]["connection_string"])
database = client.Accept


async def start_checker(attempt, language) -> bool:
    print("in run!")
    collection = database["attempt"]

    tests = attempt["results"]
    lang = language["shortName"]
    program_name = attempt["spec"]

    """ Setup files """
    module_name, module_spec = get_module(lang)
    extension = get_extension(module_spec)

    program_path = create_program_file(FOLDER, program_name, extension, attempt["programText"])
    folder_path = os.path.abspath(os.path.join(CURRENT_DIR, FOLDER))

    """ Run checker """
    result = await checker(attempt["spec"], module_spec, folder_path, program_name, tests, collection)
    delete_program_file(program_path)
    return result


def run(attempt, language):
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(start_checker(attempt, language))
