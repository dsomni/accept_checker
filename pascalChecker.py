from os import path

pathToCompiler = path.abspath(
    path.join('.', 'pascalCompiler', 'pabcnetcclear.exe'))

extension_compile = 'pas'
extension_run = 'exe'


def cmd_compile(folder_path, program_name):
    return [pathToCompiler, path.abspath(path.join(folder_path, f'{program_name}.{extension_compile}'))]


def cmd_run(folder_path, program_name):
    return [path.abspath(path.join(folder_path, f'{program_name}.{extension_run}'))]
