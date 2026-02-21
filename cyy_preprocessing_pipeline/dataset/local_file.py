from pathlib import Path

import datasets
from datasets import load_dataset


def load_local_files(files: str | Path | list[str | Path]) -> datasets.Dataset:
    if isinstance(files, (str, Path)):
        files = [files]
    str_files = [str(f) for f in files]
    path = Path(str_files[0]).suffix[1:]
    return load_dataset(path=path, data_files=str_files, split="train", cache_dir=None)
