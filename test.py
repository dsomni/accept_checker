import sys
import psutil
from subprocess import PIPE, Popen, run

# from resource import *
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(CURRENT_DIR, "1.py")


p = Popen(["python", path], stdout=PIPE, stdin=PIPE, stderr=PIPE, text=True)

K = 256 * 1024 * 1024

stack_usage = 0
data_usage = 1024 * 1024
d = data_usage + K

s = stack_usage + K

run([".\\procgov64.exe", "-m 120M", f"-p {p.pid}"], check=False)

result, errs = p.communicate(input="10")
print(result, errs)
