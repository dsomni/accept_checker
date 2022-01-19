from os import path

extension_compile = 'cpp'
extension_run = 'exe'


def cmd_compile(folder_path, program_name):
    return ['g++', '-o', path.abspath(path.join(folder_path, program_name)), path.abspath(path.join(folder_path, f'{program_name}.{extension_compile}'))]


def cmd_run(folder_path, program_name):
    return [path.abspath(path.join(folder_path, f'{program_name}.{extension_run}'))]
