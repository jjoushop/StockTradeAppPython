# Agents
# Agent = large language model (LLM), configured with instructions and tools.

# Basic configuration:

# name: A required string that identifies your agent.
# instructions: also known as a developer message or system prompt.
# model: which LLM to use, and optional model_settings to configure model tuning parameters like - temperature, top_p, etc.
# tools: Tools that the agent can use to achieve its tasks.

# Set your openai API key
import os
import getpass
import argparse
import logging
from pathlib import Path
from StockTradeAppImp import ThreadPoolApplication, install_signal_handlers

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"var: ")

_set_env("OPENAI_API_KEY")

#!pip install matplotlib
import numpy as np #The Numpy numerical computing library
import pandas as pd #The Pandas data science library
import requests #The requests library for HTTP requests in Python
import math #The Python math module
import secrets as sec
import json
import datetime as datetime

# this import is for running it on a jupyter notebook
import nest_asyncio
nest_asyncio.apply()

from agents import Agent, Runner, function_tool


def configure_logging(enabled: bool) -> None:
    if enabled:
        logging.disable(logging.NOTSET)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
        )
    else:
        logging.disable(logging.CRITICAL)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run named worker threads from config.")
    parser.add_argument(
        "--config",
        default=Path(__file__).with_name("config.json"),
        type=Path,
        help="Path to JSON configuration file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = ThreadPoolApplication.from_config_file(args.config)
    configure_logging(app.config.logging_enabled)
    install_signal_handlers(app)
    app.run_forever()


if __name__ == "__main__":
    main()
    
