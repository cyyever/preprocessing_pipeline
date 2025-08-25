import signal

from cyy_naive_lib.log import log_warning

received_signals = set()


def __handler(signum, frame) -> None:
    previous_handler = signal.getsignal(signum)
    log_warning("get signal %s", signum)
    received_signals.add(signum)
    if previous_handler is not None and not isinstance(previous_handler, int):
        previous_handler(signum, frame)


def check_signal(signum) -> bool:
    return signum in received_signals


def setup_signal_handler() -> None:
    log_warning("setup signal handler")
    signal.signal(signal.SIGINT, __handler)
