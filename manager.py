import importlib.util
from itertools import zip_longest
import json
import os
import shutil
import time
from checker import custom

import sys

from checker import checker
import motor.motor_asyncio
import asyncio
from dotenv import dotenv_values

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    cnf = json.load(file)
    langs_configs = cnf["LANGS"]
    attempts_folder = cnf["MANAGER_OPTIONS"]["attempts_folder"]
configs = dotenv_values(".env") or {}


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

def generate_program_path(folder, program_name):
    return os.path.abspath(os.path.join(CURRENT_DIR, folder, program_name))

def create_program_file(folder, program_name, extension, programText):
    folder_path = generate_program_path(folder, program_name)
    path = os.path.abspath(os.path.join(folder_path, f"{program_name}.{extension}"))
    os.mkdir(folder_path)
    with open(path, "w") as program:
        program.write(programText)
    return path, folder_path


def delete_program_folder(folder):
    try:
        shutil.rmtree(folder,ignore_errors=True)
    except BaseException as e:
        time.sleep(1)
        shutil.rmtree(folder,ignore_errors=True)


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


async def save_attempt_results(spec, tests, results, logs, collection):
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



FOLDER = attempts_folder or "programs"


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

client = motor.motor_asyncio.AsyncIOMotorClient(configs["CONNECTION_STRING"] or "")
database = client.Accept
client.get_io_loop = asyncio.get_running_loop

async def save_results(spec, tests, results, logs):
    collection = database["attempt"]
    await delete_from_pending(spec, database["pending_task_attempt"])
    verdict = await save_attempt_results(spec, tests, results, logs, collection)
    if not verdict:
        return False
    result = await save_verdict(spec, verdict, database)
    return result


def soft_run(func):
    async def inner(attempt, *args):
        try:
            await func(attempt, *args)
        except BaseException as e:
            tests = attempt["results"]
            spec = attempt["spec"]
            print("ManagerError: ", e)
            delete_program_folder(generate_program_path(FOLDER, spec))
            try:
                await save_results(spec, tests, [5] * len(tests), [str(e)])
            except:
                print("ManagerError (in handler:) ): ", e)
            return False

    return inner

@soft_run
async def tests_checker(attempt, language) -> bool:

    folder_path = None
    collection = database["attempt"]

    tests = attempt["results"]
    constraints_time = None
    constraints = attempt["constraints"]
    if constraints:
        constraints_time = constraints["time"]
    lang = language["shortName"]
    run_offset = language["runOffset"]
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
    results, logs = checker(module_spec, folder_path, spec, run_offset, compile_offset, tests, constraints_time)
    delete_program_folder(folder_path)

    """ Save result """
    return await save_results(spec, tests, results, logs)


def compare_strings(test: str, answer: str) -> int:
    test_strings = map(lambda x: x.strip(), test.strip().split("\n"))
    answer_strings = map(lambda x: x.strip(), answer.strip().split("\n"))
    for t, a in zip_longest(test_strings, answer_strings):
        if t != a:
            return 2
    return 0


@soft_run
async def text_checker(attempt) -> bool:
    collection = database["attempt"]

    tests = attempt["results"]
    spec = attempt["spec"]
    answers = attempt["textAnswers"]
    answers_length = len(answers)

    """ Run checker """
    is_set = await set_testing(spec, collection)
    if not is_set:
        return False

    results = []
    for i, test_result in enumerate(tests):
        if i >= answers_length:
            results.append(2)  # WA
        else:
            results.append(compare_strings(test_result["test"]["outputData"], answers[i]))

    """ Save result """
    return await save_results(spec, tests, results, [])



CHECKER_NAME = "checker"

@soft_run
async def custom_checker(attempt, language, checker) -> bool:
    checker_code = checker["sourceCode"]
    checker_lang = checker["language"]

    spec = attempt["spec"]
    collection = database["attempt"]

    tests = attempt["results"]

    if not checker_code:
        return await save_results(spec, tests, [6] * len(tests), ["No checker specified"])

    constraints_time = None
    constraints = attempt["constraints"]
    if constraints:
        constraints_time = constraints["time"]
    lang = language["shortName"]
    run_offset = language["runOffset"]
    compile_offset = language["compileOffset"]

    checker_run_offset = checker_lang["runOffset"]
    checker_compile_offset = checker_lang["compileOffset"]

    """ Setup files """
    module_name, module_spec = get_module(lang)
    extension = get_extension(module_spec)

    module_name, checker_module_spec = get_module(checker_lang["shortName"])
    checker_extension = get_extension(checker_module_spec)

    program_path, folder_path = create_program_file(FOLDER, spec, extension, attempt["programText"])
    with open(os.path.join(folder_path, f"{CHECKER_NAME}.{checker_extension}"), "w") as custom_checker:
        custom_checker.write(checker_code)

    """ Run checker """
    is_set = await set_testing(spec, collection)
    if not is_set:
        return False
    results, logs = custom(
        module_spec,
        folder_path,
        spec,
        run_offset,
        compile_offset,
        tests,
        constraints_time,
        checker_module_spec,
        CHECKER_NAME,
        checker_run_offset,
        checker_compile_offset,
    )
    delete_program_folder(folder_path)

    """ Save result """
    return await save_results(spec, tests, results, logs)


async def start(*args):
    attempt_spec = args[1]

    attempt = await database["attempt"].find_one({"spec": attempt_spec})

    queue_item = await database["pending_task_attempt"].find_one({"attempt": attempt_spec})

    task_type = queue_item["taskType"]
    check_type = queue_item["taskCheckType"]

    if task_type == 0:  # code

        language = await database["language"].find_one({"spec": attempt["language"]})
        if check_type == 0:
            await tests_checker(attempt, language)
        else:  # check_type == 1
            checker = queue_item["checker"]

            if checker:
                await custom_checker(attempt, language, queue_item["checker"])
            else:
                await custom_checker(attempt, language, None)

    elif task_type == 1:  # text
        await text_checker(attempt)


if __name__ == "__main__":
    asyncio.run(start(*sys.argv))
