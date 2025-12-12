# tests/test_board.py
import pytest
from src.board import Board

def test_flip_and_match():
    b = Board(2, 2, ["A", "A", "B", "B"])

    v1 = b.flip_up((0, 0))
    v2 = b.flip_up((0, 1))
    assert v1 == "A" and v2 == "A"

    b.mark_matched((0, 0), (0, 1))
    assert b.peek((0, 0)).matched is True
    assert b.peek((0, 1)).matched is True

def test_cannot_flip_matched():
    b = Board(1, 2, ["X", "X"])
    b.flip_up((0, 0))
    b.flip_up((0, 1))
    b.mark_matched((0, 0), (0, 1))
    with pytest.raises(ValueError):
        b.flip_up((0, 0))
