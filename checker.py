import sys
import subprocess
from multiprocessing import Process
import os
import signal
import importlib.util
import psutil
import json

configs = {}
with open("configs.json", "r") as file:
    configs = json.load(file)
TIMEOUT = float(configs['TIMEOUT'])
TIMEOUT_COMPILE = float(configs['TIMEOUT_COMPILE'])



def get_tests(path, n):
    tests = []
    for i in range(n):
        with open(os.path.abspath(os.path.join(path, f'input{i}.log')), 'r') as inp, open(os.path.abspath(os.path.join(path, f'output{i}.log')), 'r') as out:
            tests.append([''.join(inp.readlines()),
                         ''.join(out.readlines())])
    return tests


def check_module(module_name):
    module_spec = importlib.util.find_spec(module_name)
    if module_spec is None:
        return None
    else:
        return module_spec


def import_module_from_spec(module_spec):
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def setup_cmd(module_name, folder, program_name):
    module_spec = check_module(module_name)
    module = import_module_from_spec(module_spec)
    return [module.cmd_compile(folder, program_name), module.cmd_run(folder, program_name)]


def compile_program(folder, cmd_compile):
    with open(os.path.abspath(os.path.join(folder, 'compile_out.log')), 'w') as out, open(os.path.abspath(os.path.join(folder, 'compile_err.log')), 'w') as err:
        try:
            code = subprocess.check_call(
                cmd_compile, stdin=subprocess.PIPE, stdout=out, stderr=err, timeout=TIMEOUT_COMPILE)
            return 0
        except Exception as e:
            return 1


def write_result(result, results_folder, idx):
    with open(os.path.abspath(os.path.join(results_folder, str(idx))), 'w') as out:
        out.write(f'{result[0]}\n{result[1]}\n{result[2]}\n')


def generate_results_ce(results_folder, n):
    for i in range(n):
        write_result([i+1, 'CE', 'Compilation Error'], results_folder, i)


def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):  # or parent.children() for recursive=False
            child.kill()
        parent.kill()
    except:
        pass

def run_program(test_input, idx, folder, cmd_run):
    with open(os.path.abspath(os.path.join(folder, f'out{idx}.log')), 'w') as out, open(os.path.abspath(os.path.join(folder, f'err{idx}.log')), 'w') as err:
        program_call = subprocess.Popen(
            cmd_run,
            stdin=subprocess.PIPE,
            stdout=out, stderr=err,
            text=True)
        try:
            program_call.communicate(
                input=test_input, timeout=TIMEOUT)
            return program_call.poll()  # 0 - OK, 1 - RE
        # except subprocess.TimeoutExpired:
        except Exception as e:
            try:
                kill_process_tree(program_call.pid)
            except:
                program_call.kill()

    with open(os.path.abspath(os.path.join(folder, f'err{idx}.log')), 'r') as err:
        if len(err.readlines()):
            return 1  # RE
    return 3  # TL


def compare_results(test_output, idx, folder):
    with open(os.path.abspath(os.path.join(folder, f'out{idx}.log')), 'r') as out:
        program_output = out.readlines()
        test_output = list(
            map(lambda x: x+'\n', list(test_output.split('\n'))))
        if (len(test_output) != len(program_output)):
            return 2  # WA
        for i in range(len(test_output)):
            if (str(program_output[i]).strip() != str(test_output[i]).strip()):
                return 2  # WA
        return 0


def generate_result(code, idx):
    if code == 0:
        return [idx+1, 'OK', 'OK']
    elif code == 1:
        return [idx+1, 'RE', 'Runtime Error']
    elif code == 2:
        return [idx+1, 'WA', 'Wrong Answer']
    elif code == 3:
        return [idx+1, 'TL', 'Time Limit']


def check_test(test, idx, folder, cmd_run, results_folder):
    test_input, test_output = test
    code = run_program(test_input, idx, folder, cmd_run)
    if code == 0:
        code = compare_results(test_output, idx, folder)

    write_result(generate_result(code, idx), results_folder, idx)


if __name__ == "__main__":
    ''' Get args '''
    module_name = sys.argv[1]
    folder = sys.argv[2]
    program_name = sys.argv[3]
    tests = get_tests(sys.argv[4], int(sys.argv[5]))
    tests_number = int(sys.argv[5])
    results_folder = sys.argv[6]

    try:
        ''' Get cmd commands '''
        cmd_compile, cmd_run = setup_cmd(module_name, folder, program_name)

        ''' Compilation '''
        code = compile_program(folder, cmd_compile)
        if (code == 1):
            generate_results_ce(results_folder, tests_number)
            exit(0)

        ''' Running & Testing '''
        processes = []
        for index, test in enumerate(tests):
            process = Process(target=check_test, args=(
                test, index, folder, cmd_run, results_folder))
            processes.append(process)
            process.start()
        for process in processes:
            process.join()

        exit(0)
    except Exception as e:
        print(e)
        exit(0)
