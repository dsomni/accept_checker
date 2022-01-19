

import importlib.util
import subprocess
import os
import shutil
import time
import json


def create_folder(folder):
    try:
        os.mkdir(folder)
    except Exception as e:
        pass


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


def get_module(lang):
    global langs_configs
    module_name = langs_configs.get(lang)
    module_spec = check_module(module_name)
    if module_spec:
        return module_name, module_spec


def get_extension(module_spec):
    module = import_module_from_spec(module_spec)
    return module.extension_compile


def create_program_file(folder, program_name, extension, programText):
    with open(os.path.abspath(os.path.join(folder, f'{program_name}.{extension}')), 'w') as program:
        program.write(programText)


def setup_tests(folder, tests):
    path = os.path.abspath(os.path.join(folder, 'tests'))
    create_folder(path)
    for i in range(len(tests)):
        with open(os.path.abspath(os.path.join(path, f'input{i}.log')), 'w') as inp, open(os.path.abspath(os.path.join(path, f'output{i}.log')), 'w') as out:
            inp.write(tests[i][0])
            out.write(tests[i][1])
    return path


def get_results_path(folder):
    path = os.path.abspath(os.path.join(folder, 'results'))
    create_folder(path)
    return path


def get_results(results_folder_path, tests_length):
    results = []
    for i in range(tests_length):
        with open(os.path.abspath(os.path.join(results_folder_path, str(i))), 'r') as file:
            result = list(map(lambda x: x.strip(), file.readlines()))
            results.append(f'Test#{result[0]} {result[1]} {result[2]}')
    return results


def before_end(folder):
    try:
        shutil.rmtree(folder)
    except:
        # delete folder using chroot
        # time.sleep(1)
        # shutil.rmtree(folder)
        pass
    pass


DEFAULT_NAME = 'program'

langs_configs = []
with open("langs.json", "r") as file:
    langs_configs = json.load(file)
langs = list(langs_configs.keys())


def run(lang, program_text, tests, should_before_end=True, should_print_command=False):

    create_folder(os.path.abspath(os.path.join('.', 'logs')))
    folder = os.path.abspath(os.path.join('.', 'logs', f'{lang}_logs'))
    results = []
    tests_length = len(tests)

    ''' Create a folder '''
    create_folder(folder)

    ''' Setup files '''
    module_name, module_spec = get_module(lang)
    extension = get_extension(module_spec)
    program_name = DEFAULT_NAME
    create_program_file(folder, program_name, extension, program_text)
    tests_folder_path = setup_tests(folder, tests)
    results_folder_path = get_results_path(folder)

    ''' Setup command '''
    command = ['python', os.path.abspath(os.path.join('.', 'checker.py')), module_name, folder, program_name,
                tests_folder_path, str(tests_length), results_folder_path]
    if should_print_command:
        print(' '.join(command))

    ''' Run checker '''
    try:
        checker_process = subprocess.Popen(command)
        checker_process.wait()
    except:
        pass

    ''' Generate results '''
    code = checker_process.returncode
    if (code == 0):
        results = get_results(results_folder_path, tests_length)



    if should_before_end:
        before_end(folder)
    return results


# results = run('cpp', '#include <iostream>\n using namespace std;\nint main()\n{\nint a; cin >> a; cout << 1/a;\nreturn 0;\n}', [['0', '1']], False, False)
# print(results)
