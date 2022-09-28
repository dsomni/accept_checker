from itertools import zip_longest
import json
import os
from checker import custom
import sys
from checker import checker
import asyncio
from math import floor

from utils import (
    connect_to_db,
    create_program_file,
    delete_program_folder,
    generate_program_path,
    get_extension,
    get_module,
    send_alert,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    cnf = json.load(file)
    langs_configs = cnf["LANGS"]
    attempts_folder = cnf["MANAGER_OPTIONS"]["attempts_folder"]


FOLDER = attempts_folder or "programs"

database = connect_to_db()


async def save_verdict(attempt_spec, verdict, database):
    verdict_coll = database["user_task_verdict"]
    user_task = await database["user_task_attempt"].find_one({"attempt": attempt_spec})
    if not user_task:
        return False
    res = await verdict_coll.find_one({"user": user_task["user"], "task": user_task["task"]})
    if not res or res["verdict"] != 0:
        await verdict_coll.update_one(
            {"user": user_task["user"], "task": user_task["task"], "verdict": {"$ne": 0}},
            {"$set": {"verdict": verdict}},
            True,
        )
    return True


async def save_attempt_results(spec, tests, results, logs, collection):
    for i in range(len(tests)):
        tests[i]["verdict"] = results[i]

    verdict = 0
    verdictTest = 0
    for result in tests:
        if result["verdict"] != 0:
            verdict = result["verdict"]
            break
        verdictTest += 1

    await collection.update_one(
        {"spec": spec}, {"$set": {"status": 2, "verdict": verdict, "results": tests, "logs": logs}}
    )

    return (verdict, verdictTest)


async def save_task_results(attempt, author: str, task: str, results, verdict, verdictTest, collection):
    spec = attempt["spec"]

    passedTests = len(list(filter(lambda result: result == 0, results)))
    percentTests = floor(passedTests / len(results) * 100)

    current_attempt = {
        "attempt": spec,
        "date": attempt["date"],
        "passedTests": passedTests,
        "percentTests": percentTests,
        "verdict": verdict,
        "verdictTest": verdictTest,
    }

    results_db = await collection.find_one({"task": task, "user": author})

    if not results_db or len(results_db["bests"]) == 0:
        best = None
    else:
        best = results_db["bests"][-1]
    new_best = None

    if best and (best["verdict"] == verdict == 0 or best["percentTests"] > percentTests):
        new_best = best
        new_best["date"] = attempt["date"]
    else:
        new_best = current_attempt

    if not results_db:
        await collection.insert_one({"task": task, "user": author, "results": [current_attempt], "bests": [new_best]})
    else:
        await collection.update_one(
            {"task": task, "user": author}, {"$push": {"results": current_attempt, "bests": new_best}}
        )

    return True


async def set_testing(spec, collection):
    result = await collection.update_one({"spec": spec}, {"$set": {"status": 1}})
    return result.matched_count == 1


async def delete_from_pending(spec, collection):
    result = await collection.delete_one({"attempt": spec})
    return result.deleted_count == 1


async def save_results(attempt, author, task, tests, results, logs):
    collection = database["attempt"]
    spec = attempt["spec"]
    await delete_from_pending(spec, database["pending_task_attempt"])
    (verdict, verdictTest) = await save_attempt_results(spec, tests, results, logs, collection)
    await save_task_results(attempt, author, task, results, verdict, verdictTest, database["user_task_result"])
    result = await save_verdict(spec, verdict, database)
    return result


def soft_run(func):
    async def inner(attempt, author: str, task: str, *args):
        try:
            await func(attempt, author, task, *args)
        except BaseException as e:
            tests = attempt["results"]
            spec = attempt["spec"]
            await send_alert("ManagerError", f"{spec}\n{e}")
            delete_program_folder(generate_program_path(FOLDER, spec))
            try:
                await save_results(spec, author, task, tests, [5] * len(tests), [str(e)])
            except:
                await send_alert("ManagerError (when saving results)", f"{spec}\n{str(e)}")
            return False

    return inner


def get_constraints(attempt):
    constraints_time = None
    constraints_memory = None
    constraints = attempt["constraints"]
    if constraints:
        constraints_time = constraints["time"]
        constraints_memory = constraints["memory"]
    return constraints_time, constraints_memory


def get_offsets(language):
    compile_offset = language["compileOffset"]
    run_offset = language["runOffset"]
    mem_offset = language["memOffset"]
    return compile_offset, run_offset, mem_offset


@soft_run
async def tests_checker(attempt, author: str, task: str, language) -> bool:
    folder_path = None
    collection = database["attempt"]

    constraints = get_constraints(attempt)
    offsets = get_offsets(language)
    spec = attempt["spec"]
    tests = attempt["results"]
    lang = language["shortName"]

    """ Setup files """
    module_name, module_spec = get_module(lang, langs_configs)
    extension = get_extension(module_spec)

    program_path, folder_path = create_program_file(FOLDER, spec, extension, attempt["programText"])

    """ Run checker """
    is_set = await set_testing(spec, collection)
    if not is_set:
        return False
    results, logs = checker(
        module_spec,
        folder_path,
        spec,
        tests,
        constraints,
        offsets,
    )
    delete_program_folder(folder_path)

    """ Save result """
    return await save_results(attempt, author, task, tests, results, logs)


def compare_strings(test: str, answer: str) -> int:
    test_strings = map(lambda x: x.strip(), test.strip().split("\n"))
    answer_strings = map(lambda x: x.strip(), answer.strip().split("\n"))
    for t, a in zip_longest(test_strings, answer_strings):
        if t != a:
            return 2
    return 0


@soft_run
async def text_checker(attempt, author, task) -> bool:
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
    return await save_results(attempt, author, task, tests, results, [])


CHECKER_NAME = "checker"


@soft_run
async def custom_checker(attempt, author: str, task: str, language, checker) -> bool:
    checker_code = checker["sourceCode"]
    checker_lang = checker["language"]

    spec = attempt["spec"]
    collection = database["attempt"]

    tests = attempt["results"]

    if not checker_code:
        return await save_results(attempt, author, task, tests, [6] * len(tests), ["No checker specified"])

    constraints = get_constraints(attempt)

    offsets = get_offsets(language)

    lang = language["shortName"]

    checker_offsets = get_offsets(checker_lang)

    """ Setup files """
    module_name, module_spec = get_module(lang, langs_configs)
    extension = get_extension(module_spec)

    module_name, checker_module_spec = get_module(checker_lang["shortName"], langs_configs)
    checker_extension = get_extension(checker_module_spec)

    program_path, folder_path = create_program_file(FOLDER, spec, extension, attempt["programText"])
    with open(os.path.join(folder_path, f"{CHECKER_NAME}.{checker_extension}"), "w") as custom_checker_f:
        custom_checker_f.write(checker_code)

    """ Run checker """
    is_set = await set_testing(spec, collection)
    if not is_set:
        return False
    results, logs = custom(
        module_spec,
        folder_path,
        spec,
        tests,
        constraints,
        offsets,
        checker_module_spec,
        CHECKER_NAME,
        checker_offsets,
    )
    delete_program_folder(folder_path)

    """ Save result """
    return await save_results(attempt, author, task, tests, results, logs)


async def start(*args):
    attempt_spec = args[1]
    author = args[2]
    task = args[3]

    attempt = await database["attempt"].find_one({"spec": attempt_spec})

    queue_item = await database["pending_task_attempt"].find_one({"attempt": attempt_spec})

    task_type = queue_item["taskType"]
    check_type = queue_item["taskCheckType"]

    if task_type == 0:  # code

        language = await database["language"].find_one({"spec": attempt["language"]})
        if check_type == 0:
            await tests_checker(attempt, author, task, language)
        else:  # check_type == 1
            checker = queue_item["checker"]
            checker_language = await database["language"].find_one({"spec": checker["language"]})
            checker["language"] = checker_language
            if checker:
                await custom_checker(attempt, author, task, language, checker)
            else:
                await custom_checker(attempt, author, task, language, None)

    elif task_type == 1:  # text
        await text_checker(attempt, author, task)


if __name__ == "__main__":
    asyncio.run(start(*sys.argv))
