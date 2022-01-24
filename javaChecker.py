from os import path

extension_compile = 'java'
extension_run = 'java'


def cmd_compile(folder_path, program_name):
  return ['javac', path.abspath(path.join(folder_path, f'{program_name}.{extension_compile}'))]


def cmd_run(folder_path, program_name):
  return ['java', path.abspath(path.join(folder_path, f'{program_name}.{extension_run}'))]
