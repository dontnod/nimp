import json
import logging
import os
import platform


def configure_logging(log_level):
    log_format = "[{levelname}] {message}"
    logging.basicConfig(level = log_level, format = log_format, style = "{")
    logging.addLevelName(logging.DEBUG, "Debug")
    logging.addLevelName(logging.INFO, "Info")
    logging.addLevelName(logging.WARNING, "Warning")
    logging.addLevelName(logging.ERROR, "Error")
    logging.addLevelName(logging.CRITICAL, "Critical")


def create_default_environment():
    return {
        "git_executable": "git",
        "artifact_repository": "B:/" if platform.system() == "Windows" else "/b"
    }


def load_environment():
    env = create_default_environment()
    env.update(_load_environment_transform(os.path.join(os.path.expanduser("~"), "environment.json")))
    env.update(_load_environment_transform("environment.json"))
    return env


def _load_environment_transform(transform_file_path):
    if not os.path.exists(transform_file_path):
        return {}
    with open(transform_file_path) as transform_file:
        return json.load(transform_file)
