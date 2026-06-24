# import pytest
from mazegen import MazeGenerator


def test_creation():
    gen = MazeGenerator(10, 10)
    assert gen.width == 10
