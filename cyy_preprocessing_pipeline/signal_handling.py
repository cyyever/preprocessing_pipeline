import functools
import os
import signal
from typing import Any

from cyy_naive_lib.log import log_warning

received_signals: set[int] = set()


def __handler(signum: int, frame: Any) -> None:
    log_warning("get signal %s", signum)
    received_signals.add(signum)


def check_signal(signum: int) -> bool:
    return signum in received_signals


def combine_handle(handler1: Any, handler2: Any, signum: int, frame: Any) -> None:
    handler1(signum, frame)
    handler2(signum, frame)


def setup_signal_handler(signum: int, overwrite: bool) -> None:
    log_warning("setup signal handler in pid %s", os.getpid())
    previous_handler = None
    if not overwrite:
        previous_handler = signal.getsignal(signum)
    if previous_handler is not None and not isinstance(previous_handler, int):
        signal.signal(
            signum,
            functools.partial(combine_handle, __handler, previous_handler),
        )
    else:
        signal.signal(signum, __handler)
