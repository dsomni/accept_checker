import asyncio
import json
import subprocess
import sys
from time import sleep, time
from dotenv import dotenv_values
import psutil
import os
import motor.motor_asyncio

from utils import (
    create_program_file,
    delete_program_folder,
    get_extension,
    get_module,
    get_tuner_data,
    kill_process_tree,
    setup,
)

FOLDER = "offset"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
    cnf = json.load(file)
    langs_configs = cnf["LANGS"]
    attempts_folder = cnf["MANAGER_OPTIONS"]["attempts_folder"]
configs = dotenv_values(".env") or {}

client = motor.motor_asyncio.AsyncIOMotorClient(configs["CONNECTION_STRING"] or "")
database = client.Accept
client.get_io_loop = asyncio.get_running_loop


def compile_program(cmd_compile, lang, logs):
    try:
        start = time()
        p = psutil.Popen(cmd_compile, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.wait()
        return round(time() - start, 3)
    except BaseException as e:
        logs.append(f"Error during compilation {lang}: {str(e)}")
        return None


def run_program_time(cmd_run, lang, logs):
    p = None
    try:
        start = time()
        p = psutil.Popen(cmd_run, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.wait()
        return round(time() - start, 3)
    except BaseException as e:
        if p:
            kill_process_tree(p.pid)
        logs.append(f"Error during running for time {lang}: {str(e)}")
        return None


def run_program_memory(cmd_run, get_mem, lang, logs):
    p = None
    try:
        p = psutil.Popen(cmd_run, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        sleep(1)
        mem = get_mem(p.memory_info())

        kill_process_tree(p.pid)
        return mem
    except BaseException as e:
        if p:
            kill_process_tree(p.pid)
        logs.append(f"Error during running for time {lang}: {str(e)}")
        return None


async def save_configs(lang, compile_offset, run_offset, mem_offset, logs, folder_path):
    try:
        if len(logs) > 0:
            print(*logs, sep="\n")
        collection = database["language"]

        result = await collection.update_one(
            {"shortName": lang},
            {
                "$set": {"runOffset": run_offset, "compileOffset": compile_offset, "memOffset": mem_offset},
            },
        )

        delete_program_folder(folder_path)

        return result.matched_count == 1
    except:
        delete_program_folder(folder_path)


async def start():
    for lang in langs_configs.keys():

        module_name, module_spec = get_module(lang, langs_configs)
        extension = get_extension(module_spec)
        time_offset_code, memory_offset_code, mem_usage = get_tuner_data(module_spec)

        program_path, folder_path = create_program_file(FOLDER, f"{lang}_t", extension, time_offset_code)

        if lang == "pascal":
            folder_path = os.path.join(FOLDER, f"{lang}_t")

        cmd_compile, cmd_run = setup(module_spec, folder_path, f"{lang}_t")
        logs = []

        # Tune Compile Time offset
        compile_offset = compile_program(cmd_compile, lang, logs)
        if not compile_offset:
            compile_offset = 0
            await save_configs(lang, compile_offset, 0, 0, logs, folder_path)
            continue

        # Tune Run Time offset
        run_offset = run_program_time(cmd_run, lang, logs)
        if not run_offset:
            run_offset = 0
            await save_configs(lang, compile_offset, run_offset, 0, logs, folder_path)
            continue

        delete_program_folder(folder_path)

        program_path, folder_path = create_program_file(FOLDER, f"{lang}_m", extension, memory_offset_code)

        if lang == "pascal":
            folder_path = os.path.join(FOLDER, f"{lang}_m")

        cmd_compile, cmd_run = setup(module_spec, folder_path, f"{lang}_m")

        # Tune Run Memory offset
        compile_offset_m = compile_program(cmd_compile, lang, logs)
        if not compile_offset_m:
            await save_configs(lang, compile_offset, run_offset, 0, logs, folder_path)
            continue

        mem_offset = run_program_memory(cmd_run, mem_usage, lang, logs)
        if not mem_offset:
            mem_offset = 0

        result = await save_configs(lang, compile_offset, run_offset, mem_offset, logs, folder_path)
        print(f"{lang}: {result}")


if __name__ == "__main__":
    asyncio.run(start())
