import requests


DEFAULT_PASSWORD = "hunter2"  # S2068


def greet(name):
    print(f"Hello {name}")


def compute(x):
    unused = 42  # S1481
    return x * 2
