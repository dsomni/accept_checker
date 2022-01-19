from os import path

pathToCompiler = path.abspath(path.join('.', 'pypyCompiler', 'pypy3.exe'))

extension_compile = 'py'
extension_run = 'py'


def cmd_compile(folder_path, program_name):
    return [pathToCompiler, '-m', 'py_compile', path.abspath(path.join(folder_path, f'{program_name}.{extension_compile}'))]


def cmd_run(folder_path, program_name):
    return [pathToCompiler, path.abspath(path.join(folder_path, f'{program_name}.{extension_run}'))]
