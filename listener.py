import subprocess
import sys
from time import sleep

import os
import json
import asyncio
import concurrent.futures as pool

from utils import connect_to_db


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_manager(spec, author, task):
    global CURRENT_DIR
    try:
        subprocess.run(["python", os.path.join(CURRENT_DIR, "manager.py"), spec, author, task], check=True)
    except BaseException as e:
        print("Listener error", f"Error when starting manager: {e}")


async def take_one(collection):
    queue_item = await collection.find_one({"examined": None}, {"attempt": True, "author": True, "task": True})
    if queue_item:
        await collection.update_one({"attempt": queue_item["attempt"]}, {"$set": {"examined": True}})
    return queue_item


async def listener(configs, database):
    try:
        SLEEP_TIMEOUT = int(configs["LISTENER_OPTIONS"]["sleep_timeout_s"] or 3)
        CPU_NUMBER = os.cpu_count() or 0
        MAX_WORKERS = max(2, int(CPU_NUMBER * (float(configs["LISTENER_OPTIONS"]["cpu_utilization"] or 0.6))))

        with pool.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while True:
                try:
                    queue_item = await take_one(database["pending_task_attempt"])
                    if not queue_item:
                        sleep(SLEEP_TIMEOUT)
                        continue
                    attempt_spec = queue_item["attempt"]
                    author = queue_item["author"]
                    task = queue_item["task"]

                    executor.submit(run_manager, attempt_spec, author, task)

                except BaseException as e:
                    print(e)
                    sleep(SLEEP_TIMEOUT)
    except KeyboardInterrupt:
        print("\nExit")
        sys.exit(0)


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
        configs = json.load(file)

    database = connect_to_db()

    asyncio.run(listener(configs, database))
