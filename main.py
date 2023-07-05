"""Starts the checker"""


import asyncio

from listener import LISTENER

if __name__ == "__main__":
    asyncio.run(LISTENER.start())
