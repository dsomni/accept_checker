import sys
import subprocess
import os
import importlib.util
from time import sleep
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
DEFAULT_MEMORY_LIMIT = 16 * 1024 * 1024


def import_module_from_spec(module_spec):
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def setup(module_spec, folder, program_name):
    module = import_module_from_spec(module_spec)
    return (module.cmd_compile(folder, program_name), module.cmd_run(folder, program_name))


def compile_program(cmd_compile, logs, compile_offset):
    try:
        returncode, result, errs = limit_process(cmd_compile, None, compile_offset, 0, DEFAULT_MEMORY_LIMIT * 200, 0)
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


def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass


def check_info(process, timeout, memory_limit):
    try:
        while process.is_running():
            cpu = sum(process.cpu_times()[:-1])
            if cpu > timeout:
                process.kill()
                return 9
            total_mem = process.memory_info()
            mem = total_mem.vms + total_mem.rss + total_mem.data
            if mem > memory_limit:
                process.kill()
                return 7
            sleep(1)
        return process.returncode
    except:
        return process.returncode


def limit_process(cmd_run, test_input, constraints_time, run_offset, constraints_memory, mem_offset):
    process = psutil.Popen(
        cmd_run,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    timeout = DEFAULT_TIMEOUT + run_offset
    if constraints_time:
        timeout = constraints_time + run_offset

    memory_limit = DEFAULT_MEMORY_LIMIT + mem_offset
    if constraints_memory:
        memory_limit = constraints_memory + mem_offset
    with pool.ThreadPoolExecutor() as executor:
        info = executor.submit(check_info, process, timeout, memory_limit)
        pg = executor.submit(process.communicate, input=test_input)

        returncode = info.result()

    result = None
    result, errs = pg.result()
    return returncode, result, errs


def run_program(test_input, test_output, cmd_run, run_offset, constraints_time, constraints_memory, mem_offset):
    process = None
    verdict = 5
    try:

        returncode, result, errs = limit_process(
            cmd_run, test_input, constraints_time, run_offset, constraints_memory, mem_offset
        )
        if returncode == 1:
            verdict = 4  # RE
        elif returncode == 9:
            verdict = 1  # TL
        elif returncode == 7:
            verdict = 7  # ML
        elif compare_results(result, test_output):
            verdict = 0  # OK
        else:
            verdict = 2  # WA

    except psutil.Error as e:
        verdict = 4  # RE
    except BaseException as e:
        verdict = 5
    if process:
        kill_process_tree(process.pid)
    return verdict


def check_test(testResult, idx, cmd_run, running_offset, constraints_time, constraints_memory, mem_offset):
    test_input = testResult["test"]["inputData"]
    test_output = testResult["test"]["outputData"]
    verdict = run_program(
        test_input, test_output, cmd_run, running_offset, constraints_time, constraints_memory, mem_offset
    )
    return (idx, verdict)


CPU_NUMBER = os.cpu_count() or 0
MAX_WORKERS = min(16, CPU_NUMBER)


def checker(
    module_spec,
    folder_path,
    program_name,
    run_offset,
    compile_offset,
    tests,
    constraints_time,
    constraints_memory,
    mem_offset,
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
        with pool.ThreadPoolExecutor() as executor:
            processes = [
                executor.submit(
                    check_test, test, index, cmd_run, run_offset, constraints_time, constraints_memory, mem_offset
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


CHECKER_PASS_OUTPUT = "1"
INCREASE_TIMEOUT_K = 5


def check_output(program_input, program_output, checker_cmd_run, checker_run_offset, checker_mem_offset):
    process = None
    verdict = 6
    log = ""
    try:
        returncode, result, errs = limit_process(
            checker_cmd_run,
            program_input + "\n" + program_output,
            DEFAULT_TIMEOUT * INCREASE_TIMEOUT_K,
            checker_run_offset,
            0,
            checker_mem_offset,
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
    run_offset,
    constraints_time,
    constraints_memory,
    mem_offset,
    checker_cmd_run,
    checker_run_offset,
    checker_mem_offset,
):
    test_input = testResult["test"]["inputData"]
    process = None
    verdict = 5
    log = ""
    try:
        returncode, result, errs = limit_process(
            cmd_run, test_input, constraints_time, run_offset, constraints_memory, mem_offset
        )
        if returncode != 0:
            verdict = 4  # RE
        else:
            verdict, log = check_output(test_input, result, checker_cmd_run, checker_run_offset, checker_mem_offset)
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
    run_offset,
    compile_offset,
    tests,
    constraints_time,
    constraints_memory,
    mem_offset,
    checker_module_spec,
    checker_name,
    checker_run_offset,
    checker_compile_offset,
    checker_mem_offset,
) -> Tuple[List[int], List[str]]:
    results = [5] * len(tests)
    try:

        """Get cmd commands Checker"""
        checker_cmd_compile, checker_cmd_run = setup(checker_module_spec, folder_path, checker_name)

        logs = []

        """ Compilation Checker"""
        code = compile_program(checker_cmd_compile, logs, checker_compile_offset)
        if code == 1:
            logs.append("Error when compiling custom checker")
            return (generate_results_nt(results), logs)

        """Get cmd commands"""
        cmd_compile, cmd_run = setup(module_spec, folder_path, program_name)

        """ Compilation """
        code = compile_program(cmd_compile, logs, compile_offset)
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
                    run_offset,
                    constraints_time,
                    constraints_memory,
                    mem_offset,
                    checker_cmd_run,
                    checker_run_offset,
                    checker_mem_offset,
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
