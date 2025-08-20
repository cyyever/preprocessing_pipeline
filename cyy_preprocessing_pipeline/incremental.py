import json
import os
from collections.abc import Callable
from typing import Any


def incremental_computing(
    input_json: str, output_json: str, fun: Callable[[str, Any], tuple[Any, bool]]
) -> None:
    new_value: bool = False
    with open(input_json, encoding="utf8") as f1:
        data = json.load(f1)
        res = {}
        if os.path.isfile(output_json):
            with open(output_json, encoding="utf8") as f2:
                res = json.load(f2)
        res = {str(k): v for k, v in res.items()}
        for sample_id, value in data.items():
            if str(sample_id) in res:
                continue
            result, done = fun(sample_id, value)
            if done:
                res[str(sample_id)] = result
            new_value = True
    if new_value:
        with open(output_json, "w", encoding="utf8") as f:
            json.dump(res, f, indent=2)


def strip_lines(s: str) -> list[str]:
    lines = s.splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    return lines
