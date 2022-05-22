import sys
import subprocess
import os
import importlib.util
import psutil
import json
import concurrent.futures as pool
from typing import Tuple, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

configs = {}
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)
DEFAULT_TIMEOUT = float(configs["DEFAULT_TIMEOUT"])
DEFAULT_TIMEOUT_COMPILE = float(configs["DEFAULT_TIMEOUT_COMPILE"])


def import_module_from_spec(module_spec):
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def setup(module_spec, folder, program_name):
    module = import_module_from_spec(module_spec)
    return (module.cmd_compile(folder, program_name), module.cmd_run(folder, program_name))


def compile_program(cmd_compile, logs, compile_offset):
    try:
        code = subprocess.run(
            cmd_compile, capture_output=True, timeout=DEFAULT_TIMEOUT_COMPILE + compile_offset, check=True
        )
        logs.append(f"Compiler output: {code.stdout}")
        logs.append(f"Compiler error: {code.stderr}")
        return 0
    except subprocess.CalledProcessError as e:
        logs.append(f"Compiler output: {e.stdout}")
        logs.append(f"Compiler error: {e.stderr}")
        return 1
    except Exception as e:
        return 1


def generate_results_ce(results):
    results[0] = 3
    for i in range(1, len(results)):
        results[i] = 6
    return results


def generate_results_se(results):
    for i in range(len(results)):
        results[i] = 5
    return results


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


def run_program(test_input, test_output, cmd_run, run_offset, constraints_time):
    process = None
    verdict = 5
    try:
        process = subprocess.Popen(
            cmd_run, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        timeout = DEFAULT_TIMEOUT + run_offset
        if constraints_time:
            timeout = constraints_time + run_offset

        result, errs = process.communicate(input=test_input, timeout=timeout)
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


def check_test(testResult, idx, cmd_run, running_offset, constraints_time):
    test_input = testResult["test"]["inputData"]
    test_output = testResult["test"]["outputData"]
    verdict = run_program(test_input, test_output, cmd_run, running_offset, constraints_time)
    return (idx, verdict)


CPU_NUMBER = os.cpu_count() or 0
MAX_WORKERS = min(16, CPU_NUMBER)


def checker(
    module_spec, folder_path, program_name, run_offset, compile_offset, tests, constraints_time
) -> Tuple[List[int], List[str]]:
    results = [5] * len(tests)
    try:
        """Get cmd commands"""
        cmd_compile, cmd_run = setup(module_spec, folder_path, program_name)

        logs = []

        """ Compilation """
        code = compile_program(cmd_compile, logs, compile_offset)
        if code == 1:
            return (generate_results_ce(results), logs)

        """ Running & Testing """
        with pool.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            processes = [
                executor.submit(check_test, test, index, cmd_run, run_offset, constraints_time)
                for index, test in enumerate(tests)
            ]

            for process in pool.as_completed(processes):
                idx, verdict = process.result()
                results[idx] = verdict

        return (results, logs)
    except Exception as e:
        print("Exception in Checker", e)
        return (generate_results_se(results), [str(e)])
