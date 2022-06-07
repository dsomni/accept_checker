import asyncio
from datetime import datetime, timezone
import shutil
import importlib.util
import sys
import time
import os
from dotenv import dotenv_values
import motor.motor_asyncio
import psutil

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

def connect_to_db():
    db_configs = dotenv_values(".env") or {}
    client = motor.motor_asyncio.AsyncIOMotorClient(db_configs["CONNECTION_STRING"] or "")
    client.get_io_loop = asyncio.get_running_loop
    return client.Accept


async def send_alert(title: str, message: str, status: str = 'error'):
    database = connect_to_db()
    collection = database['checker_alert']
    alert = dict()
    alert['date'] = datetime.now(timezone.utc)
    alert['title'] = title
    alert['message'] = message
    alert['status'] = status
    await collection.insert_one(alert)
    print(f'{title}, alert sended')


def check_module(module_name):
    module_name = module_name
    module_spec = importlib.util.find_spec(module_name)
    if module_spec is None:
        return None
    else:
        return module_spec


def import_module_from_spec(module_spec):
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def get_module(lang, langs_configs):
    module_name = langs_configs[lang]
    module_spec = check_module(module_name)
    return module_name, module_spec


def get_extension(module_spec):
    module = import_module_from_spec(module_spec)
    return module.extension_compile


def get_tuner_data(module_spec):
    module = import_module_from_spec(module_spec)
    return module.time_offset_code, module.memory_offset_code, module.mem_usage

def get_mem_usage_func(module_spec):
    module = import_module_from_spec(module_spec)
    return  module.mem_usage


def get_memory_usage(lang, mem):
    if lang == "java":
        return mem.rss
    return mem.data


def generate_program_path(folder, program_name):
    return os.path.abspath(os.path.join(CURRENT_DIR, folder, program_name))


def create_program_file(folder, program_name, extension, programText):
    folder_path = generate_program_path(folder, program_name)
    path = os.path.abspath(os.path.join(folder_path, f"{program_name}.{extension}"))
    os.mkdir(folder_path)
    with open(path, "w") as program:
        program.write(programText)
    return path, folder_path


def delete_program_folder(folder):
    try:
        shutil.rmtree(folder, ignore_errors=True)
    except BaseException as e:
        time.sleep(1)
        shutil.rmtree(folder, ignore_errors=True)


def setup(module_spec, folder, program_name):
    module = import_module_from_spec(module_spec)
    return (module.cmd_compile(folder, program_name), module.cmd_run(folder, program_name))


def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass
