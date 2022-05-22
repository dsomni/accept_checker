from datetime import datetime
from multiprocessing import Pool, Queue
from time import sleep
from manager import run
import motor.motor_asyncio
import os
import json
import asyncio
from threading import Thread

PARALLEL_TESTS = 4


async def take_one(collection):
    queue_item = await collection.find_one({})
    if queue_item:
        await collection.delete_one({"attempt": queue_item["attempt"]})
    return queue_item


async def main():
    languages_cursor = database["language"].find({})
    # queue = []
    languages = dict()
    async for language in languages_cursor:
        languages[language["spec"]] = language

    with Pool(processes=PARALLEL_TESTS) as pool:
        start = datetime.now()
        while True:
            try:
                queue_item = await take_one(database["pending_task_attempt"])
                if not queue_item:
                    print(datetime.now() - start)
                    sleep(2)
                    continue
                attempt_spec = queue_item["attempt"]
                task_type = queue_item["taskType"]
                check_type = queue_item["taskCheckType"]
                attempt = await database["attempt"].find_one({"spec": attempt_spec})
                if task_type == 0:
                    result = pool.apply_async(run, (attempt_spec, languages[attempt["language"]]))
                    print(result.get())

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
    event_loop.run_until_complete(main())
