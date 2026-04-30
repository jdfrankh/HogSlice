import os
import sys


def get_runtime_dir():
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "HogSlice")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    runtime_dir = os.path.join(base_dir, "Runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    return runtime_dir


def get_runtime_path(filename):
    return os.path.join(get_runtime_dir(), filename)