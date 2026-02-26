import dataclasses
import functools

import numpy as np
import torch

from cyy_preprocessing_pipeline.tensor import recursive_tensor_op


def double(t: torch.Tensor) -> torch.Tensor:
    return t * 2


def test_single_tensor():
    t = torch.tensor([1.0, 2.0])
    result = recursive_tensor_op(t, double)
    assert torch.equal(result, torch.tensor([2.0, 4.0]))


def test_list_of_tensors():
    data = [torch.tensor(1.0), torch.tensor(2.0)]
    result = recursive_tensor_op(data, double)
    assert torch.equal(result[0], torch.tensor(2.0))
    assert torch.equal(result[1], torch.tensor(4.0))


def test_tuple_of_tensors():
    data = (torch.tensor(3.0),)
    result = recursive_tensor_op(data, double)
    assert isinstance(result, tuple)
    assert torch.equal(result[0], torch.tensor(6.0))


def test_dict_of_tensors():
    data = {"a": torch.tensor(1.0), "b": torch.tensor(2.0)}
    result = recursive_tensor_op(data, double)
    assert torch.equal(result["a"], torch.tensor(2.0))
    assert torch.equal(result["b"], torch.tensor(4.0))


def test_nested():
    data = {"x": [torch.tensor(1.0)], "y": (torch.tensor(2.0),)}
    result = recursive_tensor_op(data, double)
    assert torch.equal(result["x"][0], torch.tensor(2.0))
    assert torch.equal(result["y"][0], torch.tensor(4.0))


def test_numpy_skipped():
    arr = np.array([1.0, 2.0])
    result = recursive_tensor_op(arr, double)
    assert np.array_equal(result, arr)


def test_numpy_in_container():
    data = [np.array([1.0]), torch.tensor(3.0)]
    result = recursive_tensor_op(data, double)
    assert np.array_equal(result[0], np.array([1.0]))
    assert torch.equal(result[1], torch.tensor(6.0))


def test_functools_partial():
    data = functools.partial(int, torch.tensor(1.0))
    result = recursive_tensor_op(data, double)
    assert isinstance(result, functools.partial)
    assert torch.equal(result.args[0], torch.tensor(2.0))


@dataclasses.dataclass
class _Box:
    value: torch.Tensor


def test_dataclass():
    data = _Box(value=torch.tensor(5.0))
    result = recursive_tensor_op(data, double)
    assert torch.equal(result.value, torch.tensor(10.0))


def test_kwargs_forwarded():
    def add(t: torch.Tensor, offset: float = 0) -> torch.Tensor:
        return t + offset

    result = recursive_tensor_op(torch.tensor(1.0), add, offset=10.0)
    assert torch.equal(result, torch.tensor(11.0))


def test_non_tensor_passthrough():
    assert recursive_tensor_op(42, double) == 42
    assert recursive_tensor_op("hello", double) == "hello"
