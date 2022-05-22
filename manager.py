import importlib.util
import json
import os
import shutil
import time

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
    folder_path = os.path.abspath(os.path.join(CURRENT_DIR, folder, f"{program_name}"))
    path = os.path.abspath(os.path.join(folder_path, f"{program_name}.{extension}"))
    os.mkdir(folder_path)
    with open(path, "w") as program:
        program.write(programText)
    return path, folder_path


def delete_program_folder(folder):
    try:
        shutil.rmtree(folder)
    except BaseException as e:
        time.sleep(1)
        shutil.rmtree(folder)


async def save_verdict(attempt_spec, verdict, database):
    verdict_coll = database["user_task_verdict"]
    user_task = await database["user_task_attempt"].find_one({"attempt": attempt_spec})
    if not user_task:
        return False
    await verdict_coll.update_one(
        {"user": user_task["user"], "task": user_task["task"], "verdict": {"$ne": 0}},
        {"$set": {"verdict": verdict}},
        True,
    )
    return True


async def save_results(spec, tests, results, logs, collection):
    for i in range(len(tests)):
        tests[i]["verdict"] = results[i]

    verdict = len(tests) - 1
    for idx, result in enumerate(tests):
        if result["verdict"] != 0:
            verdict = idx
            break

    r = await collection.update_one(
        {"spec": spec}, {"$set": {"status": 2, "verdict": verdict, "results": tests, "logs": logs}}
    )

    return r.modified_count == 1
    # return True


async def set_testing(spec, collection):
    result = await collection.update_one({"spec": spec}, {"$set": {"status": 1}})
    return result.matched_count == 1


async def delete_from_pending(spec, collection):
    result = await collection.delete_one({"attempt": spec})
    return result.deleted_count == 1


FOLDER = "programs"


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
configs = {}
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

client = motor.motor_asyncio.AsyncIOMotorClient(configs["database"]["connection_string"])
database = client.Accept


async def tests_checker(attempt, language) -> bool:
    folder_path = None
    try:
        collection = database["attempt"]

        tests = attempt["results"]
        # constrains_time = attempt["constrains"]["time"]
        lang = language["shortName"]
        run_offset = language["runOffset"]  # + constrains_time
        compile_offset = language["compileOffset"]
        spec = attempt["spec"]

        """ Setup files """
        module_name, module_spec = get_module(lang)
        extension = get_extension(module_spec)

        program_path, folder_path = create_program_file(FOLDER, spec, extension, attempt["programText"])

        """ Run checker """
        is_set = await set_testing(spec, collection)
        if not is_set:
            return False
        results, logs = checker(module_spec, folder_path, spec, run_offset, compile_offset, tests)
        delete_program_folder(folder_path)

        await delete_from_pending(spec, database["pending_task_attempt"])
        verdict = await save_results(spec, tests, results, logs, collection)
        if not verdict:
            return False
        result = await save_verdict(spec, verdict, database)
        return result

    except BaseException as e:
        print("ManagerError: ", e)
        if folder_path:
            delete_program_folder(folder_path)
        return False


def run_tests_checker(*args):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tests_checker(*args))
