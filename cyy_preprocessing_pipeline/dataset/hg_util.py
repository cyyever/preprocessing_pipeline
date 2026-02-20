import copy
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any, Self

import datasets
import numpy as np
from cyy_naive_lib import Decorator, load_json
from cyy_naive_lib.metric import SamplesMetrics, SamplesMetricsGroup


class HFDatasetUtil(Decorator[datasets.Dataset]):
    @classmethod
    def load_from_json(cls, dataset_json: str) -> Self:
        dataset = load_json(dataset_json)
        return cls.load(dataset)

    @classmethod
    def load(cls, dataset: list | dict) -> Self:
        if isinstance(dataset, Mapping):
            return cls(datasets.Dataset.from_dict(dataset))
        if isinstance(dataset, Iterable):
            return cls(datasets.Dataset.from_list(list(dataset)))
        raise RuntimeError("Unsupported dataset:" + type(dataset).__name__)

    @property
    def dataset(self) -> datasets.Dataset:
        return self._decorator_object

    def set_dataset(self, dataset: datasets.Dataset) -> None:
        self._decorator_object = dataset

    def filter(self, *args: Any, **kwargs: Any) -> Self:
        new_instance = copy.copy(self)
        new_instance.set_dataset(self.dataset.filter(*args, **kwargs))
        return new_instance

    def add_id_column(self, column_name: str) -> None:
        def impl(example: dict[str, Any], idx: int) -> dict[str, Any]:
            assert column_name not in example
            example[column_name] = idx
            return example

        self.set_dataset(self.dataset.map(impl, with_indices=True, num_proc=2))

    def add_column_from_dict(
        self,
        column: dict[Any, Any],
        column_name: str,
        matched_key: str,
        default_value: Any = None,
    ) -> None:
        assert column

        def impl(example: dict[str, Any]) -> dict[str, Any]:
            assert column_name not in example
            k = example[matched_key]
            value = column.get(k)
            if value is None:
                value = column.get(str(k), default_value)
            example[column_name] = value
            return example

        self.set_dataset(self.dataset.map(impl, num_proc=2))

    def get_numerical_column(self, column_name: str) -> np.ndarray:
        col = self.dataset[column_name]
        assert None not in col
        return np.array(col)

    def get_column_metrics(self, column_name: str) -> SamplesMetrics:
        return SamplesMetrics(
            samples=self.get_numerical_column(column_name), label=column_name
        )

    def get_columns_metrics(
        self, column_names: list[str] | dict[str, str]
    ) -> SamplesMetricsGroup:
        real_column_names = []
        if isinstance(column_names, dict):
            real_column_names = list(column_names.keys())
        else:
            real_column_names = column_names

        group = SamplesMetricsGroup(
            elements=[self.get_column_metrics(k) for k in real_column_names]
        )
        if isinstance(column_names, dict):
            for col_name, metrics in zip(
                real_column_names, group.elements, strict=False
            ):
                metrics.label = column_names[col_name]

        return group

    def count_column(self, column_name: str) -> Counter[Any]:
        return Counter(self.dataset[column_name])
