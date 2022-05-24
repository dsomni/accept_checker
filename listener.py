from time import sleep
import time
from manager import run_tests_checker, run_text_checker, run_custom_checker
import motor.motor_asyncio
import os
import json
import asyncio
import concurrent.futures as pool

SLEEP_TIMEOUT = 3
LANGS_REFETCH_TIMEOUT = 60 * 30
CPU_NUMBER = os.cpu_count() or 0
MAX_WORKERS = max(2, int(CPU_NUMBER * 0.6))


async def take_one(collection):
    queue_item = await collection.find_one({"examined": None})
    if queue_item:
        await collection.update_one({"attempt": queue_item["attempt"]}, {"$set": {"examined": True}})
    return queue_item


async def fetch_languages():
    # print("FETCH LANGUAGES")
    languages_cursor = database["language"].find({})
    languages = dict()
    async for language in languages_cursor:
        languages[language["spec"]] = language
    return languages


async def listener():
    languages = await fetch_languages()

    with pool.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # start = datetime.now()
        # processes = []
        last_lang_refetch = 0
        while True:
            try:
                queue_item = await take_one(database["pending_task_attempt"])

                if not queue_item:
                    # for process in processes:
                    #     if process.done():
                    #         processes.remove(process)
                    # if len(processes) == 0:
                    #     print(datetime.now() - start)
                    last_lang_refetch += SLEEP_TIMEOUT
                    sleep(SLEEP_TIMEOUT)
                    continue
                if last_lang_refetch >= LANGS_REFETCH_TIMEOUT:
                    last_lang_refetch = 0
                    languages = await fetch_languages()
                attempt_spec = queue_item["attempt"]
                task_type = queue_item["taskType"]
                check_type = queue_item["taskCheckType"]
                attempt = await database["attempt"].find_one({"spec": attempt_spec})
                if task_type == 0:  # code
                    if check_type == 0:
                        process = executor.submit(run_tests_checker, attempt, languages[attempt["language"]])
                    else:  # check_type == 1
                        checker = queue_item["checker"]
                        if checker:
                            process = executor.submit(
                                run_custom_checker,
                                attempt,
                                languages[attempt["language"]],
                                checker["sourceCode"],
                                languages[checker["language"]],
                            )
                        else:
                            process = executor.submit(
                                run_custom_checker, attempt, languages[attempt["language"]], None, None
                            )
                    if attempt["language"] == 4:  # java
                        process.result()
                elif task_type == 1:  # text
                    process = executor.submit(run_text_checker, attempt)

            except BaseException as e:
                print(e)
                sleep(SLEEP_TIMEOUT)


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    configs = {}
    with open(os.path.abspath(os.path.join(CURRENT_DIR, "configs.json")), "r") as file:
        configs = json.load(file)

    client = motor.motor_asyncio.AsyncIOMotorClient(configs["database"]["connection_string"])
    database = client.Accept

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(listener())
