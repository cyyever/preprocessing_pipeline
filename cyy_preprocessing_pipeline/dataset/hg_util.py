import copy
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

import datasets
import numpy as np
from cyy_naive_lib import Decorator, load_json


class HFDatasetUtil(Decorator[datasets.Dataset]):
    @classmethod
    def load_from_json(cls, dataset_json: str):
        dataset = load_json(dataset_json)
        return cls.load(dataset)

    @classmethod
    def load(cls, dataset: list | dict):
        if isinstance(dataset, Mapping):
            return cls(datasets.Dataset.from_dict(dataset))
        if isinstance(dataset, Iterable):
            return cls(datasets.Dataset.from_list(list(dataset)))
        raise RuntimeError("Unsupported dataset:" + type(dataset))

    @property
    def dataset(self) -> datasets.Dataset:
        return self._decorator_object

    def set_dataset(self, dataset: datasets.Dataset):
        self._decorator_object = dataset

    def filter(self, **kwargs: Any):
        new_instance = copy.copy(self)
        new_instance.set_dataset(self.dataset.filter(**kwargs))
        return new_instance

    def add_column_from_dict(
        self, column: dict, column_name: str, matched_key: str
    ) -> None:
        assert column

        def impl(example):
            assert column_name not in column
            k = example[matched_key]
            value = column.pop(k, None)
            if value is None:
                column.pop(str(k), None)
            example[column_name] = column.pop(k, None)
            return example

        self.set_dataset(self.dataset.map(impl, num_proc=2))

    def get_numerical_column(self, column_name: str) -> np.ndarray:
        col = self.dataset[column_name]
        assert None not in col
        return np.array(col)

    def count_column(self, column_name: str) -> Counter:
        return Counter(self.dataset[column_name])
