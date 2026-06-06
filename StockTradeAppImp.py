from __future__ import annotations

import logging
import os
import signal
import time
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from pathlib import Path
from threading import Event

from StockTradeConfig import AppConfig, load_config
from StockTradeSharedMemory import SharedMemory
from StockTradeWorker import run_worker


class ThreadPoolApplication:
    shutdown_timeout_seconds = 10.0

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.shared_memory = SharedMemory()
        self.stop_event = Event()
        self._forced_stop_requested = False

    @classmethod
    def from_config_file(cls, config_path: str | Path) -> "ThreadPoolApplication":
        return cls(load_config(config_path))

    def request_stop(self) -> None:
        self.stop_event.set()

    def run_forever(self) -> None:
        logging.info("Launching %s configured worker threads", self.config.thread_count)
        executor = ThreadPoolExecutor(max_workers=self.config.thread_count)
        futures = [
            executor.submit(
                run_worker,
                thread_config,
                self.shared_memory,
                self.stop_event,
                self.config.heartbeat_interval_seconds,
            )
            for thread_config in self.config.threads
        ]

        try:
            while not self.stop_event.is_set():
                done, _not_done = wait(futures, timeout=0.5, return_when=FIRST_EXCEPTION)
                for future in done:
                    exception = future.exception()
                    if exception is not None:
                        raise exception

                if all(future.done() for future in futures):
                    return
        finally:
            self.request_stop()
            self._shutdown_executor(executor, futures)

    def _shutdown_executor(self, executor: ThreadPoolExecutor, futures: list[object]) -> None:
        deadline = time.monotonic() + self.shutdown_timeout_seconds
        while time.monotonic() < deadline:
            if all(future.done() for future in futures):
                executor.shutdown(wait=True)
                return
            time.sleep(0.2)

        unfinished_count = sum(1 for future in futures if not future.done())
        logging.error(
            "Timed out waiting for %s worker thread(s) to stop; forcing process exit",
            unfinished_count,
        )
        executor.shutdown(wait=False, cancel_futures=True)
        os._exit(130)


def install_signal_handlers(app: ThreadPoolApplication) -> None:
    def handle_signal(signum: int, _frame: object) -> None:
        if app.stop_event.is_set():
            logging.warning("Received signal %s again, forcing process exit", signum)
            os._exit(130)

        logging.info("Received signal %s, stopping workers", signum)
        app.request_stop()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)
