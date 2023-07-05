from base64 import encode
import sys
import subprocess
import os
from time import sleep, time
import psutil
import json
import concurrent.futures as pool
from typing import Tuple, List

from utils import get_mem_usage_func, kill_process_tree, setup

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

configs = {}
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    configs = json.load(file)

DEFAULT_TIME_LIMIT = float(configs["DEFAULT_TIME_LIMIT"])
DEFAULT_MEMORY_LIMIT = int(configs["DEFAULT_MEMORY_LIMIT"])

MAX_TOTAL_SLEEP_K = 4
CHECKER_PASS_OUTPUT = "1"

INCREASE_TIMEOUT_K = 10
INCREASE_MEMORY_K = 64

CHECKER_CONSTRAINTS = (
    DEFAULT_TIME_LIMIT * INCREASE_TIMEOUT_K,
    DEFAULT_MEMORY_LIMIT * INCREASE_MEMORY_K,
)


def compile_program(cmd_compile, logs, compile_offset, get_mem):
    try:
        returncode, result, errs = limit_process(
            cmd_compile, None, CHECKER_CONSTRAINTS, (0, compile_offset, 0), get_mem
        )
        if returncode != 0:
            logs.append(f"Compiler error: {str(errs)}")
            return 1
    except Exception as e:
        logs.append(f"Error during compilation: {str(e)}")
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


def generate_results_nt(results):
    for i in range(len(results)):
        results[i] = 6
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


def check_info(process, timeout, memory_limit, get_mem):
    sleep_time = 0.01
    total_sleep = 0
    try:
        while process.is_running():
            cpu = sum(process.cpu_times()[:-1])

            if cpu > timeout or cpu > timeout * MAX_TOTAL_SLEEP_K:
                process.kill()
                return 1  # TL
            mem = get_mem(process.memory_info())  # bytes
            if mem > memory_limit:
                process.kill()
                return 7  # ML
            sleep(sleep_time)
            total_sleep += sleep_time
    except:
        pass
    return 4 if process.returncode and process.returncode != 0 else 0  # RE


def limit_process(cmd_run, test_input, constraints, offsets, get_mem):
    compile_offset, run_offset, mem_offset = offsets
    constraints_time, constraints_memory = constraints

    timeout = DEFAULT_TIME_LIMIT + run_offset
    if constraints_time:
        timeout = constraints_time + run_offset

    memory_limit = DEFAULT_MEMORY_LIMIT + mem_offset
    if constraints_memory:
        memory_limit = constraints_memory + mem_offset

    memory_limit = memory_limit * 1024 * 1024 * 8  # Mb -> bytes

    process = psutil.Popen(
        cmd_run,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf8",
    )

    with pool.ThreadPoolExecutor() as executor:
        info = executor.submit(check_info, process, timeout, memory_limit, get_mem)
        pg = executor.submit(process.communicate, input=test_input)

        returncode = info.result()

    result = None
    result, errs = pg.result()
    return returncode, result, errs


def run_program(test_input, test_output, cmd_run, constraints, offsets, get_mem):
    process = None
    verdict = 5
    try:
        returncode, result, errs = limit_process(
            cmd_run, test_input, constraints, offsets, get_mem
        )
        if returncode != 0:
            verdict = returncode  # see: check_info()
        elif compare_results(result, test_output):
            verdict = 0  # OK
        else:
            verdict = 2  # WA

    except psutil.Error as e:
        print(e)
        verdict = 4  # RE
    except BaseException as e:
        verdict = 5
    if process:
        kill_process_tree(process.pid)
    return verdict


def check_test(testResult, idx, cmd_run, constraints, offsets, get_mem):
    test_input = testResult["test"]["inputData"]
    test_output = testResult["test"]["outputData"]
    verdict = run_program(
        test_input, test_output, cmd_run, constraints, offsets, get_mem
    )
    return (idx, verdict)


CPU_NUMBER = os.cpu_count() or 0
MAX_WORKERS = min(16, CPU_NUMBER)


def checker(
    module_spec,
    folder_path,
    program_name,
    tests,
    constraints,
    offsets,
) -> Tuple[List[int], List[str]]:
    results = [6] * len(tests)
    logs = []
    compile_offset = offsets[0]
    try:
        """Get cmd commands"""
        cmd_compile, cmd_run = setup(module_spec, folder_path, program_name)
        get_mem_usage = get_mem_usage_func(module_spec)

        """ Compilation """
        code = compile_program(cmd_compile, logs, compile_offset, get_mem_usage)
        if code == 1:
            return (generate_results_ce(results), logs)

        """ Running & Testing """
        with pool.ThreadPoolExecutor(max_workers=5) as executor:
            processes = [
                executor.submit(
                    check_test,
                    test,
                    index,
                    cmd_run,
                    constraints,
                    offsets,
                    get_mem_usage,
                )
                for index, test in enumerate(tests)
            ]

            for process in pool.as_completed(processes):
                idx, verdict = process.result()
                results[idx] = verdict

        return (results, logs)
    except Exception as e:
        print("Exception in Checker", e)
        return (generate_results_se(results), [f"Checker Error: {str(e)}"])


def check_output(
    program_input, program_output, checker_cmd_run, checker_offsets, get_mem
):
    process = None
    verdict = 6
    log = ""
    try:
        returncode, result, errs = limit_process(
            checker_cmd_run,
            program_input + "\n" + program_output,
            CHECKER_CONSTRAINTS,
            checker_offsets,
            get_mem,
        )
        if returncode != 0:
            verdict = 2  # RE
            log = f"Error when running custom checker: {errs}"
        elif compare_results(result, CHECKER_PASS_OUTPUT):
            verdict = 0
        else:
            verdict = 2
    except subprocess.TimeoutExpired as e:
        log = f"Custom checker: {str(e)}"
        verdict = 2  # TL
    except subprocess.SubprocessError as e:
        log = f"Error when running custom checker: {str(e)}"
        verdict = 2  # RE
    except BaseException as e:
        log = f"Error when running custom checker: {str(e)}"
        verdict = 2
    if process:
        kill_process_tree(process.pid)
    return (verdict, log)


def check_test_checker(
    testResult,
    idx,
    cmd_run,
    constraints,
    offsets,
    get_mem,
    checker_cmd_run,
    checker_offsets,
    get_checker_mem,
):
    test_input = testResult["test"]["inputData"]
    process = None
    verdict = 5
    log = ""
    try:
        returncode, result, errs = limit_process(
            cmd_run, test_input, constraints, offsets, get_mem
        )
        if returncode != 0:
            verdict = 4  # RE
        else:
            verdict, log = check_output(
                test_input, result, checker_cmd_run, checker_offsets, get_checker_mem
            )
    except subprocess.TimeoutExpired as e:
        verdict = 1  # TL
    except subprocess.SubprocessError as e:
        verdict = 4  # RE
    except BaseException as e:
        verdict = 5
    if process:
        kill_process_tree(process.pid)
    return (idx, verdict, log)


def custom(
    module_spec,
    folder_path,
    program_name,
    tests,
    constraints,
    offsets,
    checker_module_spec,
    checker_name,
    checker_offsets,
) -> Tuple[List[int], List[str]]:
    results = [6] * len(tests)
    logs = []
    checker_compile_offset, checker_run_offset, checker_mem_offset = checker_offsets
    compile_offset, run_offset, mem_offset = offsets
    constraints_time, constraints_memory = constraints
    try:
        """Get cmd commands Checker"""

        checker_cmd_compile, checker_cmd_run = setup(
            checker_module_spec, folder_path, checker_name
        )
        get_checker_mem = get_mem_usage_func(checker_module_spec)

        """ Compilation Checker"""
        code = compile_program(
            checker_cmd_compile, logs, checker_compile_offset, get_checker_mem
        )
        if code == 1:
            logs.append("Error when compiling custom checker")
            return (generate_results_nt(results), logs)

        """Get cmd commands"""
        cmd_compile, cmd_run = setup(module_spec, folder_path, program_name)
        get_mem = get_mem_usage_func(module_spec)

        """ Compilation """

        code = compile_program(cmd_compile, logs, compile_offset, get_mem)
        if code == 1:
            return (generate_results_ce(results), logs)

        """ Running & Testing """
        with pool.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            processes = [
                executor.submit(
                    check_test_checker,
                    test,
                    index,
                    cmd_run,
                    constraints,
                    offsets,
                    get_mem,
                    checker_cmd_run,
                    checker_offsets,
                    get_checker_mem,
                )
                for index, test in enumerate(tests)
            ]

            for process in pool.as_completed(processes):
                idx, verdict, log = process.result()
                if log != "":
                    logs.append(log)
                results[idx] = verdict

        return (results, logs)
    except Exception as e:
        print("Exception in Checker", e)
        return (generate_results_se(results), [f"Custom checker Error: {str(e)}"])
