from datetime import datetime
import subprocess
from time import sleep

from dotenv import dotenv_values
import motor.motor_asyncio
import os
import json
import asyncio
import concurrent.futures as pool


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_manager(spec):
    global CURRENT_DIR
    try:
        subprocess.run(["python", os.path.join(CURRENT_DIR, "manager.py"), spec], check=True)
    except BaseException as e:
        print(f"Listener error: error when starting manager: {e}")


async def take_one(collection):
    queue_item = await collection.find_one({"examined": None}, {"attempt": True})
    if queue_item:
        await collection.update_one({"attempt": queue_item["attempt"]}, {"$set": {"examined": True}})
    return queue_item


async def listener(configs):

    SLEEP_TIMEOUT = int(configs["LISTENER_OPTIONS"]["sleep_timeout_s"] or 3)
    # CPU_NUMBER = os.cpu_count() or 0
    # MAX_WORKERS = max(2, int(CPU_NUMBER * (float(configs["LISTENER_OPTIONS"]["cpu_utilization"] or 0.6))))

    with pool.ProcessPoolExecutor() as executor:
        start = datetime.now()
        processes = []
        # last_lang_refetch = 0
        while True:
            try:
                queue_item = await take_one(database["pending_task_attempt"])
                if not queue_item:
                    for process in processes:
                        if process.done():
                            processes.remove(process)
                    # if len(processes) == 0:
                    #     print(datetime.now() - start)
                    sleep(SLEEP_TIMEOUT)
                    continue
                attempt_spec = queue_item["attempt"]

                process = executor.submit(run_manager, attempt_spec)
                processes.append(process)

            except BaseException as e:
                print(e)
                sleep(SLEEP_TIMEOUT)


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    configs = {}
    with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
        configs = json.load(file)
    db_configs = dotenv_values(".env") or {}

    client = motor.motor_asyncio.AsyncIOMotorClient(db_configs["CONNECTION_STRING"] or "")
    client.get_io_loop = asyncio.get_running_loop

    database = client.Accept

    asyncio.run(listener(configs))
