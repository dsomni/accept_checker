"""General utilities functions"""


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

from typing import Literal, Union

from database import DATABASE


VERDICT_DICT = dict(
    {
        "OK": 0,
        "TL": 1,
        "WA": 2,
        "CE": 3,
        "RE": 4,
        "SE": 5,
        "NT": 6,
        "ML": 7,
    }
)

VerdictType = Union[
    Literal["OK"],
    Literal["TL"],
    Literal["WA"],
    Literal["CE"],
    Literal["RE"],
    Literal["SE"],
    Literal["NT"],
    Literal["ML"],
]

ATTEMPT_STATUS_DICT = dict(
    {
        "pending": 0,
        "testing": 1,
        "finished": 2,
        "banned": 3,
    }
)

AttemptStatusType = Union[
    Literal["pending"],
    Literal["testing"],
    Literal["finished"],
    Literal["banned"],
]

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)


def soft_make_dir(path: str):
    """Creates folder using specified path

    Args:
        path (str)
    """
    if os.path.exists(path) and os.path.isdir(path):
        return
    os.mkdir(path)


def map_verdict(verdict: VerdictType) -> int:
    """Maps string verdict to its spec

    Args:
        verdict (VERDICT_TYPE): string verdict

    Returns:
        int: verdict spec
    """
    return VERDICT_DICT[verdict]


def generate_tests_verdicts(verdict: VerdictType, tests_number: int) -> list[int]:
    """Generates same verdict for all tests

    Args:
        verdict (VERDICT_TYPE): string verdict
        tests_number (int): number of tests

    Returns:
        list[int]: verdict specs
    """
    verdict_spec = VERDICT_DICT[verdict]
    return [verdict_spec for _ in range(tests_number)]


def map_attempt_status(attempt_status: AttemptStatusType) -> int:
    """Maps attempt status verdict to its spec

    Args:
        attempt_status (ATTEMPT_STATUS_TYPE): string attempt status

    Returns:
        int: attempt status spec
    """
    return ATTEMPT_STATUS_DICT[attempt_status]


async def send_alert(title: str, message: str, status: str = "error"):
    """Saves alert to the database

    Args:
        title (str): alert title
        message (str): message
        status (str, optional): Status code. Defaults to "error".
    """

    alert = dict(
        {
            "title": title,
            "date": datetime.now(timezone.utc),
            "message": message,
            "status": status,
        }
    )

    await DATABASE.insert_one("checker_alert", alert)


def delete_folder(path: str):
    """Deletes specified folder

    Args:
        path (str): path to the folder
    """
    if os.path.exists(path) and os.path.isdir(path):
        try:
            shutil.rmtree(path, ignore_errors=True)
        except BaseException:  # pylint: disable=W0718
            time.sleep(1)
            shutil.rmtree(path, ignore_errors=True)


def create_program_folder(attempt_spec: str) -> str:
    """Creates folder based on attempt spec

    Args:
        attempt_spec (str): attempt spec

    Returns:
        str: path to the folder
    """
    folder_name = f"{attempt_spec}_{datetime.utcnow().timestamp()}"
    folder_path = os.path.abspath(os.path.join(CURRENT_DIR, folder_name))
    soft_make_dir(folder_path)
    return folder_path


def kill_process_tree(pid: int):
    """Kills process tree

    Args:
        pid (int): pid of the process
    """
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except BaseException:  # pylint:disable=W0718
        pass


def connect_to_db():
    db_configs = dotenv_values(".env") or {}
    client = motor.motor_asyncio.AsyncIOMotorClient(
        db_configs["CONNECTION_STRING"] or ""
    )
    client.get_io_loop = asyncio.get_running_loop
    return client.Accept


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
    return module.mem_usage


def get_memory_usage(lang, mem):
    if lang == "java":
        return mem.rss
    return mem.data


def generate_program_path(folder, program_name):
    return os.path.abspath(os.path.join(CURRENT_DIR, folder, program_name))


def setup(module_spec, folder, program_name):
    module = import_module_from_spec(module_spec)
    return (
        module.cmd_compile(folder, program_name),
        module.cmd_run(folder, program_name),
    )
