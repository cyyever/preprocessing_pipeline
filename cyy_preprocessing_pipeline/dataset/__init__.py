import json
import os
from collections.abc import Generator, Iterable
from typing import Any

import torch
import torch.utils.data

from ..transform import DatasetTransform
from .iob import IOBParser, IOBRecord
from .local_file import load_local_files
from .sampler import DatasetSampler
from .util import (
    DatasetUtil,
    DatasetWithIndex,
    IndicesType,
    OptionalIndicesType,
    get_dataset_size,
    select_item,
    subset_dp,
)

__all__ = [
    "IOBParser",
    "IOBRecord",
    "DatasetWithIndex",
    "OptionalIndicesType",
    "subset_dp",
    "IndicesType",
    "select_item",
    "get_dataset_size",
    "DatasetSampler",
    "DatasetUtil",
    "load_local_files",
]
