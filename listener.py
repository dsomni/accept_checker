from datetime import datetime
from time import sleep
from manager import run_tests_checker
import motor.motor_asyncio
import os
import json
import asyncio
import concurrent.futures as pool


async def take_one(collection):
    queue_item = await collection.find_one({"examined": None})
    if queue_item:
        await collection.update_one({"attempt": queue_item["attempt"]}, {"$set": {"examined": True}})
    return queue_item


async def listener():
    languages_cursor = database["language"].find({})
    languages = dict()
    async for language in languages_cursor:
        languages[language["spec"]] = language

    with pool.ProcessPoolExecutor(max_workers=5) as executor:
        start = datetime.now()
        processes = []
        while True:
            try:
                queue_item = await take_one(database["pending_task_attempt"])
                if not queue_item:
                    for process in processes:
                        if process.done():
                            processes.remove(process)
                    if len(processes) == 0:
                        print(datetime.now() - start)
                    sleep(2)
                    continue
                attempt_spec = queue_item["attempt"]
                task_type = queue_item["taskType"]
                check_type = queue_item["taskCheckType"]
                attempt = await database["attempt"].find_one({"spec": attempt_spec})
                if task_type == 0:
                    process = executor.submit(run_tests_checker, attempt, languages[attempt["language"]])
                    processes.append(process)

            except BaseException as e:
                print(e)
                sleep(2)


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    configs = {}
    with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
        configs = json.load(file)

    client = motor.motor_asyncio.AsyncIOMotorClient(configs["database"]["connection_string"])
    database = client.Accept

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(listener())
