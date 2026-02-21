import collections
import copy
import functools
import random
from collections.abc import Callable
from typing import Any

import torch
from cyy_naive_lib.log import log_warning

from .util import DatasetUtil


class DatasetSampler:
    def __init__(self, dataset_util: DatasetUtil) -> None:
        self.__dataset_util: DatasetUtil = dataset_util
        self._excluded_indices: set[int] = set()
        self.checked_indices: set[int] | None = None

    @property
    def dataset(self) -> torch.utils.data.Dataset:
        return self.__dataset_util.dataset

    def set_excluded_indices(self, excluded_indices: set[int]) -> None:
        self._excluded_indices = excluded_indices

    @functools.cached_property
    def sample_label_dict(self) -> dict[int, set[Any]]:
        return dict(self.__dataset_util.get_batch_labels())

    @functools.cached_property
    def label_sample_dict(self) -> dict[Any, set[int]]:
        label_sample_dict: collections.defaultdict[Any, set[int]] = collections.defaultdict(set)
        for index, labels in self.sample_label_dict.items():
            for label in labels:
                label_sample_dict[label].add(index)
        return dict(label_sample_dict)

    def get_subsets(
        self, index_list: list[set[int]]
    ) -> list[torch.utils.data.MapDataPipe]:
        return [
            self.__dataset_util.get_subset(indices=indices) for indices in index_list
        ]

    def split_indices(
        self,
        part_proportions: list[dict[Any, float]],
        labels: list[Any] | None = None,
        is_iid: bool = False,
    ) -> list[set[int]]:
        assert part_proportions

        sub_index_list: list[set[int]] = [set() for _ in range(len(part_proportions))]

        def __split_per_label(label: Any, indices: set[int]) -> set[int]:
            nonlocal part_proportions
            label_part = [
                part_proportion.get(label, 0) for part_proportion in part_proportions
            ]
            if sum(label_part) == 0:
                return set()
            part_index_lists = self.__split_index_list(
                label_part, list(indices), is_iid=is_iid
            )
            for i, part_index_list in enumerate(part_index_lists):
                sub_index_list[i] |= set(part_index_list)
            return indices

        self.__check_sample_by_label(
            callback=__split_per_label,
            labels=labels,
        )
        return sub_index_list

    def sample_indices(
        self,
        parts: list[dict[Any, float]],
        labels: list[Any] | None = None,
    ) -> list[set[int]]:
        assert parts

        sub_index_list: list[set[int]] = [set() for _ in range(len(parts))]

        def __sample_per_label(label: Any, indices: set[int]) -> set[int]:
            nonlocal parts
            label_part = [part.get(label, 0) for part in parts]
            if sum(label_part) == 0:
                return set()
            part_index_lists = self.__split_index_list(
                label_part, list(indices), is_iid=False
            )
            sampled_indices = set()
            for i, part_index_list in enumerate(part_index_lists):
                part_index_set = set(
                    part_index_list[: int(label_part[i] * len(indices))]
                )
                sampled_indices.update(part_index_set)
                sub_index_list[i] |= part_index_set
            return sampled_indices

        self.__check_sample_by_label(
            callback=__sample_per_label,
            labels=labels,
        )
        return sub_index_list

    def iid_split_indices(
        self,
        parts: list[float],
        labels: list[Any] | None = None,
    ) -> list[set[int]]:
        assert parts

        if labels is None:
            labels = list(self.label_sample_dict.keys())
        return self.split_indices(
            part_proportions=[{label: part for label in labels} for part in parts],
            labels=labels,
        )

    def random_split_indices(
        self, parts: list[float], labels: list[Any] | None = None, by_label: bool = True
    ) -> list[list[int]]:
        if by_label:
            collected_indices = set()

            def __collect(_: Any, indices: set[int]) -> set[int]:
                collected_indices.update(indices)
                return indices

            self.__check_sample_by_label(callback=__collect, labels=labels)
            return self.__split_index_list(parts, list(collected_indices), is_iid=False)
        index_list = list(set(range(len(self.__dataset_util))) - self._excluded_indices)
        return self.__split_index_list(parts, index_list, is_iid=False)

    def iid_split(
        self, parts: list[float], labels: list[Any] | None = None
    ) -> list[torch.utils.data.MapDataPipe]:
        return self.get_subsets(self.iid_split_indices(parts, labels=labels))

    def iid_sample_indices(self, percent: float) -> set[int]:
        labels = list(self.label_sample_dict.keys())
        return self.sample_indices(
            [{label: percent for label in labels}], labels=labels
        )[0]

    def randomize_label(
        self, indices: list[int], percent: float, all_labels: set[Any] | None = None
    ) -> dict[int, set[Any]]:
        randomized_label_map: dict[int, set[Any]] = {}
        if all_labels is None:
            all_labels = set(self.label_sample_dict.keys())

        flipped_indices = random.sample(list(indices), k=int(len(indices) * percent))
        for index in flipped_indices:
            other_labels = list(all_labels - self.sample_label_dict[index])
            randomized_label_map[index] = set(
                random.sample(
                    other_labels,
                    min(len(other_labels), len(self.sample_label_dict[index])),
                )
            )

        return randomized_label_map

    def randomize_label_by_class(
        self,
        percent: float | dict[Any, float],
        all_labels: set[Any] | None = None,
        **kwargs: Any,
    ) -> dict[int, set[Any]]:
        randomized_label_map: dict[int, set[Any]] = {}

        def __randomize(label: Any, indices: set[int]) -> set[int]:
            nonlocal randomized_label_map
            nonlocal percent
            if not indices:
                return indices

            new_percent = percent[label] if isinstance(percent, dict) else percent
            assert isinstance(new_percent, float | int)

            randomized_label_map |= self.randomize_label(
                indices=indices,
                percent=new_percent,
                all_labels=all_labels,
            )

            return indices

        self.__check_sample_by_label(callback=__randomize, **kwargs)

        return randomized_label_map

    @classmethod
    def __split_index_list(
        cls, parts: list[float], index_list: list[int], is_iid: bool
    ) -> list[list[int]]:
        assert index_list
        if len(parts) == 1:
            assert parts[0] != 0
            return [index_list]
        random.shuffle(index_list)
        part_lens: list[int] = []
        first_assert = True
        index_num = len(index_list)
        total = sum(parts)

        for part in parts:
            assert part > 0
            part_len = int(index_num * part / total)
            if part_len == 0 and is_iid:
                if sum(part_lens, start=0) < index_num:
                    part_len = 1
                elif first_assert:
                    first_assert = False
                    log_warning(
                        "has zero part when splitting list, %s %s",
                        index_num,
                        parts,
                    )
            part_lens.append(part_len)
        for _ in range(index_num - sum(part_lens)):
            idx = random.randrange(len(part_lens))
            part_lens[idx] += 1
        assert sum(part_lens) == index_num
        part_indices = []
        for part_len in part_lens:
            if part_len != 0:
                part_indices.append(index_list[0:part_len])
                index_list = index_list[part_len:]
            else:
                part_indices.append([])
        return part_indices

    def __check_sample_by_label(
        self,
        callback: Callable[..., set[int]],
        labels: list[Any] | None = None,
    ) -> None:
        excluded_indices = copy.copy(self._excluded_indices)

        if labels is None:
            labels = list(self.label_sample_dict.keys())
        for label in labels:
            indices = self.label_sample_dict[label] - excluded_indices
            if self.checked_indices is not None:
                indices = indices.intersection(self.checked_indices)
            if indices:
                resulting_indices = callback(label=label, indices=indices)
                excluded_indices.update(resulting_indices)


class ClassificationDatasetSampler(DatasetSampler):
    pass
