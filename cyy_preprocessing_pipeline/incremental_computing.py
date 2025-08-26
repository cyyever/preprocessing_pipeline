import signal
from collections.abc import Callable, Generator
from typing import Any

from cyy_naive_lib import Expected, ProcessPool, TimeCounter, load_json, save_json

from .signal_handling import check_signal, setup_signal_handler


def incremental_save(
    output_json: str,
    data_fun: Callable[[Any], Generator[tuple[str, Any], Any, None]],
    save_second_interval: int = 10 * 60,
) -> None:
    setup_signal_handler(signal.SIGINT, overwrite=True)
    res = load_json(output_json)
    time_counter = TimeCounter()
    for result_pair in data_fun(res):
        key, v = result_pair
        assert key not in res
        res[key] = v
        if check_signal(signal.SIGINT):
            break
        if time_counter.elapsed_seconds() >= save_second_interval:
            save_json(res, output_json)
            time_counter.reset_start_time()
    save_json(res, output_json)


executor_pool: ProcessPool | None = None


def incremental_computing(
    input_json: str,
    output_json: str,
    fun: Callable[[str, Any], Expected],
    save_second_interval: int = 10 * 60,
    multiprocessing: bool = False,
) -> None:
    global executor_pool
    data = load_json(input_json)

    if multiprocessing and executor_pool is None:
        executor_pool = ProcessPool()

    def wrapped_fun(sample_id, value):
        expected = fun(sample_id, value)
        if expected.is_ok():
            return str(sample_id), expected.value()
        return None

    def data_fun(previous_results: Any) -> Generator[tuple[str, Any], Any, None]:
        assert isinstance(previous_results, dict)
        for sample_id, value in data.items():
            if str(sample_id) in previous_results:
                continue
            if multiprocessing:
                assert executor_pool is not None
                executor_pool.submit(wrapped_fun, sample_id, value)
                futures, _ = executor_pool.wait_results(timeout=0)
                for tuple_result in futures.values():
                    if tuple_result is not None:
                        sample_id, result = tuple_result
                        assert isinstance(sample_id, str)
                        yield str(sample_id), result
            else:
                res = wrapped_fun(sample_id, value)
                if res is not None:
                    yield res

    incremental_save(
        output_json=output_json,
        data_fun=data_fun,
        save_second_interval=save_second_interval,
    )


def incremental_reduce(
    input_json: str,
    output_json: str,
    fun: Callable[[Any, dict], dict],
    save_second_interval: int = 10 * 60,
) -> None:
    raise NotImplementedError("abc")
    # data = load_json(input_json)
    # assert data
    #
    # def data_fun(previous_results):
    #     for value in data.values():
    #         res = fun(value, previous_results)
    #
    # incremental_save(
    #     output_json=output_json,
    #     data_fun=data_fun,
    #     save_second_interval=save_second_interval,
    # )
