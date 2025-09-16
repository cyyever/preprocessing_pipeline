import functools
import os

from cyy_naive_lib import load_json
from pandas import DataFrame


class HFTrainerResult:
    def __init__(self, result_path: str):
        assert os.path.isdir(result_path)
        self.result_path = result_path

    @functools.cached_property
    def trainer_state(self) -> dict:
        stat = load_json(os.path.join(self.result_path, "trainer_state.json"))
        assert stat and isinstance(stat, dict)
        return stat

    @functools.cached_property
    def log_history(self) -> list[dict]:
        h = self.trainer_state["log_history"]
        assert h and isinstance(h, list)
        return h

    @functools.cached_property
    def training_history(self) -> DataFrame:
        step_history = []
        for a in self.log_history:
            assert "step" in a
            if "eval_loss" not in a:
                step_history.append(a)
        assert "train_loss" in step_history[-1]
        step_history.pop(-1)
        assert step_history
        return DataFrame(step_history)
