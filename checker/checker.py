import sys
import subprocess
from multiprocessing import Process, Array
import os
import importlib.util
import psutil
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

configs = {}
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)
TIMEOUT = float(configs["TIMEOUT"])
TIMEOUT_COMPILE = float(configs["TIMEOUT_COMPILE"])


def import_module_from_spec(module_spec):
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def setup(module_spec, folder, program_name):
    module = import_module_from_spec(module_spec)
    return (module.cmd_compile(folder, program_name), module.cmd_run(folder, program_name), module.running_offset)


def compile_program(cmd_compile, logs):
    try:
        code = subprocess.run(cmd_compile, capture_output=True, timeout=TIMEOUT_COMPILE, check=True)
        logs.append(f"Compiler output: {code.stdout}")
        logs.append(f"Compiler error: {code.stderr}")
        return 0
    except subprocess.CalledProcessError as e:
        logs.append(f"Compiler output: {e.stdout}")
        logs.append(f"Compiler error: {e.stderr}")
        return 1
    except Exception as e:
        return 1


async def generate_results_ce(spec, collection, tests):
    tests[0]["verdict"] = 3
    for i in range(1, len(tests)):
        tests[i]["verdict"] = 6
    return await collection.update_one({"spec": spec}, {"$set": {"results": tests, "status": 2, "verdict": 0}})


async def generate_results_se(spec, collection, tests):
    for i in range(len(tests)):
        tests[i]["verdict"] = 5
    return await collection.update_one({"spec": spec}, {"$set": {"results": tests, "status": 2, "verdict": 0}})


def compare_results(result, test_output):
    result = list(result.strip().split("\n"))
    test_output = list(test_output.split("\n"))
    if len(test_output) != len(result):
        return False
    for i in range(len(test_output)):
        if str(result[i]).strip() != str(test_output[i]).strip():
            return False
    return True


def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass


def run_program(test_input, test_output, cmd_run, running_offset):
    process = None
    verdict = 5
    try:
        process = subprocess.Popen(
            cmd_run, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        result, errs = process.communicate(input=test_input, timeout=TIMEOUT + running_offset)
        if process.returncode != 0:
            verdict = 4  # RE
        elif compare_results(result, test_output):
            verdict = 0  # OK
        else:
            verdict = 2  # WA
    except subprocess.TimeoutExpired as e:
        verdict = 1  # TL
    except subprocess.SubprocessError as e:
        verdict = 4  # RE
    except BaseException as e:
        verdict = 5
    if process:
        kill_process_tree(process.pid)
    return verdict


def check_test(spec, testResult, idx, cmd_run, running_offset, results):
    test_input = testResult["test"]["inputData"]
    test_output = testResult["test"]["outputData"]
    verdict = run_program(test_input, test_output, cmd_run, running_offset)
    results[idx] = verdict


async def write_logs(spec, collection, logs):
    await collection.update_one({"spec": spec}, {"$set": {"logs": logs}})


async def generate_verdict(spec, collection):
    data = await collection.find_one({"spec": spec}, {"results": 1})
    results = data["results"]
    verdict = None
    for idx, result in enumerate(results):
        if result["verdict"] != 0:
            verdict = idx
            break
    else:
        verdict = len(results) - 1
    await collection.update_one({"spec": spec}, {"$set": {"verdict": verdict}})


async def checker(attempt_spec, module_spec, folder_path, program_name, tests, collection) -> bool:
    results = Array("i", [5] * len(tests))
    try:
        """Get cmd commands"""
        cmd_compile, cmd_run, running_offset = setup(module_spec, folder_path, program_name)
        logs = []
        """ Compilation """
        code = compile_program(cmd_compile, logs)
        await write_logs(attempt_spec, collection, logs)
        if code == 1:
            await generate_results_ce(attempt_spec, collection, tests)
            return True

        """ Running & Testing """
        processes = []
        for index, test in enumerate(tests):
            process = Process(target=check_test, args=(attempt_spec, test, index, cmd_run, running_offset, results))
            processes.append(process)
            process.start()
        for process in processes:
            process.join()

        for idx, verdict in enumerate(results):
            await collection.update_one({"spec": attempt_spec}, {"$set": {f"results.{idx}.verdict": verdict}})
        await generate_verdict(attempt_spec, collection)

        return True
    except Exception as e:
        await write_logs(attempt_spec, collection, [e])
        await generate_results_se(attempt_spec, collection, tests)
        return False
