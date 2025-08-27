import functools
from collections.abc import Generator, Iterable
from typing import Any

import torch
import torch.utils.data

from ..pipeline import DataPipeline
from ..tensor import tensor_to

type IndicesType = Iterable[int]
type OptionalIndicesType = IndicesType | None


def get_dataset_size(dataset: Any) -> int:
    match dataset:
        case {0: {"mask": mask}}:
            return mask.sum()
        case [{"mask": mask}]:
            return mask.sum()
    if hasattr(dataset, "__len__"):
        return len(dataset)
    match dataset:
        case torch.utils.data.IterableDataset():
            return sum(1 for _ in dataset)
    raise NotImplementedError(dataset)


def select_item(dataset: Any, indices: OptionalIndicesType = None) -> Generator:
    if indices is not None:
        indices = sorted(
            set(
                int(idx.item()) if isinstance(idx, torch.Tensor) else idx
                for idx in indices
            )
        )
    match dataset:
        case torch.utils.data.IterableDataset():
            iterator = iter(dataset)
            if indices is None:
                yield from enumerate(iterator)
            else:
                assert indices
                next_idx = indices[0]
                for idx, item in enumerate(iterator):
                    if idx == next_idx:
                        yield idx, item
                        indices = indices[1:]
                        if not indices:
                            return
                        next_idx = indices[0]
        case _:
            if indices is None:
                indices = list(range(get_dataset_size(dataset)))
            for idx in indices:
                yield idx, dataset[idx]


def subset_dp(
    dataset: torch.utils.data.Dataset, indices: OptionalIndicesType = None
) -> torch.utils.data.MapDataPipe:
    return torch.utils.data.datapipes.map.SequenceWrapper(
        list(dict(select_item(dataset, indices)).values()), deepcopy=False
    )


class KeyPipe(torch.utils.data.MapDataPipe):
    def __init__(self, dp: Any) -> None:
        super().__init__()
        self.__dp = dp

    def __getitem__(self, index) -> tuple:
        item = self.__dp[index]
        return (index, item)

    def __len__(self) -> int:
        return len(self.__dp)


class DatasetWithIndex(DatasetTransform):
    def __init__(self) -> None:
        super().__init__(fun=DatasetWithIndex.apply, name="add index to dataset")

    @classmethod
    def apply(cls, data: Any) -> Any:
        dataset = data
        return torch.utils.data.datapipes.map.Mapper(
            KeyPipe(dataset), DatasetWithIndex._add_index_to_map_item
        )

    @classmethod
    def _add_index_to_map_item(cls, item) -> dict:
        key, value = item[0], item[1]
        return {"index": key, "data": value}


class DatasetUtil:
    def __init__(
        self,
        dataset: torch.utils.data.Dataset,
        name: None | str = None,
        pipeline: DataPipeline | None = None,
    ) -> None:
        self.__dataset: torch.utils.data.Dataset = dataset
        self.__len: None | int = None
        self.__sample_number: None | int = None
        self._name: str = name if name else ""
        self.__pipeline: DataPipeline = (
            pipeline if pipeline is not None else DataPipeline()
        )

    def __len__(self) -> int:
        if self.__len is None:
            self.__len = get_dataset_size(self.dataset)
        return self.__len

    @property
    def dataset(self) -> torch.utils.data.Dataset:
        return self.__dataset

    @property
    def label_number(self) -> int:
        return len(self.get_labels())

    @property
    def sample_number(self) -> int:
        if self.__sample_number is not None:
            return self.__sample_number
        self.__sample_number = 0
        for _, target in self.__get_batch_labels_impl():
            match target:
                case torch.Tensor():
                    self.__sample_number += int((target != -100).sum().item())
                case [int(), *_]:
                    self.__sample_number += len([a for a in target if a != -100])
        assert self.__sample_number != 0
        return self.__sample_number

    @property
    def pipeline(self) -> DataPipeline:
        return self.__pipeline

    def cache_pipeline(self, device: torch.device) -> tuple[Any, DataPipeline]:
        data, remaining_pipeline = self.__pipeline.cache_dataset(dataset=self.dataset)
        if device.type != "cpu":
            data = tensor_to(data, device=device)
        return data, remaining_pipeline

    def decompose(self) -> None | dict:
        return None

    def get_subset(self, indices: IndicesType) -> torch.utils.data.MapDataPipe:
        return subset_dp(self.dataset, indices)

    def get_raw_samples(self, indices: OptionalIndicesType = None) -> Generator:
        return select_item(dataset=self.dataset, indices=indices)

    def get_samples(self, indices: OptionalIndicesType = None) -> Generator:
        raw_samples = self.get_raw_samples(indices=indices)
        for idx, sample in raw_samples:
            if self.__pipeline is not None:
                sample = self.__pipeline.apply_first(sample)
            yield idx, sample

    def get_sample(self, index: int) -> Any:
        for _, sample in self.get_samples(indices=[index]):
            return sample
        return None

    @classmethod
    def __decode_target(cls, target: Any) -> set:
        match target:
            case int() | str():
                return {target}
            case torch.Tensor():
                if target.numel() == 1:
                    return {target.item()}
                # one hot vector
                if (target <= 1).all().item() and (target >= 0).all().item():
                    return set(target.nonzero().view(-1).tolist())
                raise NotImplementedError(f"Unsupported target {target}")
            case dict():
                if "labels" in target:
                    return cls.__decode_target(target["labels"].tolist())
                if all(isinstance(s, str) and s.isnumeric() for s in target):
                    return cls.__decode_target({int(s) for s in target})
            case Iterable():
                return set(target)
        raise RuntimeError("can't extract labels from target: " + str(target))

    @classmethod
    def replace_target(cls, old_target: Any, new_target: set[Any]) -> Any:
        match old_target:
            case int() | str():
                assert len(new_target) == 1
                new_target = list(new_target)[0]
                assert type(old_target) is type(new_target)
                assert old_target != new_target
                return new_target
            case torch.Tensor():
                if old_target.numel() == 1:
                    assert len(new_target) == 1
                    old_shape = old_target.shape
                    old_target_value = old_target.item()
                    new_target_value = list(new_target)[0]
                    new_target_tensor = old_target.clone().reshape(-1)
                    assert old_target_value != new_target_value
                    new_target_tensor[0] = new_target_value
                    return new_target_tensor.reshape(old_shape)
                raise NotImplementedError(f"Unsupported target {old_target}")
            # case dict():
            #     if "labels" in old_target:
            #         new_target_dict = copy.deepcopy(old_target)
            #         new_target_dict["labels"] = cls.replace_target(
            #             old_target["labels"], new_target
            #         )
            #         return new_target_dict
            # case list() | tuple():
            #     old_target_value = cls.__decode_target(old_target)
            #     return type(old_target)(
            #         new_target.get(old_t, old_t) for old_t in old_target_value
            #     )

        raise RuntimeError(f"can't convert labels {new_target} for target {old_target}")

    def _get_sample_input(self, index: int) -> Any:
        sample = self.get_sample(index)
        return sample["input"]

    def __get_batch_labels_impl(
        self, indices: OptionalIndicesType = None
    ) -> Generator[tuple[int, Any]]:
        for idx, sample in self.get_samples(indices):
            target: Any | None = None
            if "target" in sample:
                target = sample["target"]
            else:
                if "input" in sample and isinstance(sample["input"], dict):
                    sample = sample["input"]
                if "ner_tags" in sample:
                    target = sample["ner_tags"]
                elif "labels" in sample:
                    target = sample["labels"]
                elif "tags" in sample:
                    target = sample["tags"]
                else:
                    raise NotImplementedError(sample.keys())
            assert target is not None
            yield idx, target

    def get_batch_labels(
        self, indices: OptionalIndicesType = None
    ) -> Generator[tuple[int, set]]:
        for idx, target in self.__get_batch_labels_impl(indices):
            labels = DatasetUtil.__decode_target(target)
            if -100 in labels:
                labels.remove(-100)
            yield idx, labels

    def get_sample_label(self, index: int) -> set:
        for _, labels in self.get_batch_labels(indices=[index]):
            return labels
        raise RuntimeError()

    def get_labels(self) -> set:
        return set().union(*tuple(set(labels) for _, labels in self.get_batch_labels()))

    def get_original_dataset(self) -> torch.utils.data.Dataset:
        return self.dataset[0].get("original_dataset", self.dataset)

    def get_label_names(self) -> dict:
        original_dataset = self.get_original_dataset()
        classes = getattr(original_dataset, "classes", None)
        if classes and isinstance(classes[0], str):
            return dict(enumerate(classes))

        def get_label_name(container: set, idx_and_labels: tuple[int, set]) -> set:
            container.update(idx_and_labels[1])
            return container

        label_names: set = functools.reduce(
            get_label_name, self.get_batch_labels(), set()
        )
        if label_names:
            return dict(enumerate(sorted(label_names)))
        raise RuntimeError("no label names detected")
