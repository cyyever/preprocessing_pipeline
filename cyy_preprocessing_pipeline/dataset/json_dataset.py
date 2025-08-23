import json
import os
from collections.abc import Callable
from typing import Any


def load_json(json_file: str) -> dict[str, Any]:
    res = {}
    if os.path.isfile(json_file):
        with open(json_file, encoding="utf8") as f:
            res = json.load(f)
            assert isinstance(res, dict), json_file
            res = {str(k): v for k, v in res.items()}
    return res


def save_json(data, json_file: str, backup: bool = True) -> None:
    hard_link = json_file + ".hard_link"
    link_flag: bool = False
    if backup and os.path.isfile(json_file) and not os.path.exists(hard_link):
        os.link(json_file, hard_link)
        link_flag = True
        os.unlink(json_file)
    with open(json_file, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    if link_flag:
        os.unlink(hard_link)


def incremental_computing(
    input_json: str, output_json: str, fun: Callable[[str, Any], tuple[Any, bool]]
) -> None:
    new_value: bool = False
    data = load_json(input_json)
    assert data
    res = load_json(output_json)
    for sample_id, value in data.items():
        if str(sample_id) in res:
            continue
        result, done = fun(sample_id, value)
        if done:
            res[str(sample_id)] = result
        new_value = True
    if new_value:
        save_json(res, output_json)


def incremental_reduce(
    input_json: str, output_json: str, fun: Callable[[Any, dict], dict]
) -> None:
    data = load_json(input_json)
    assert data
    res = load_json(output_json)
    for value in data.values():
        res = fun(value, res)
    with open(output_json, "w", encoding="utf8") as f:
        json.dump(res, f, indent=2, sort_keys=True)
