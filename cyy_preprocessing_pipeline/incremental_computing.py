from collections.abc import Callable
from typing import Any

from cyy_naive_lib.storage import load_json, save_json
from cyy_naive_lib.time_counter import TimeCounter


def incremental_save(
    output_json: str,
    data_fun: Callable[[dict], tuple[Any, Any] | None],
    save_second_interval: int = 10 * 60,
) -> None:
    new_value: bool = False
    res = load_json(output_json)
    time_counter = TimeCounter()
    while True:
        result_pair = data_fun(res)
        if result_pair is None:
            break
        key, v = result_pair
        assert key not in res
        res[key] = v
        new_value = True
        if time_counter.elapsed_seconds() >= save_second_interval:
            save_json(res, output_json)
            time_counter.reset_start_time()
    if new_value:
        save_json(res, output_json)


def incremental_computing(
    input_json: str,
    output_json: str,
    fun: Callable[[str, Any], tuple[Any, bool]],
    save_second_interval: int = 10 * 60,
) -> None:
    data = load_json(input_json)

    def data_fun(res):
        for sample_id, value in data.items():
            if str(sample_id) in res:
                continue
            result, done = fun(sample_id, value)
            if done:
                return str(sample_id), result
        return None

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
    data = load_json(input_json)
    assert data

    def data_fun(res):
        for value in data.values():
            res = fun(value, res)

    incremental_save(
        output_json=output_json,
        data_fun=data_fun,
        save_second_interval=save_second_interval,
    )
