# src/board.py
from __future__ import annotations
from dataclasses import dataclass
from threading import RLock
from typing import Dict, List, Optional, Tuple

Coord = Tuple[int, int]  # (row, col)

@dataclass(frozen=True)
class Cell:
    value: str
    face_up: bool = False
    matched: bool = False


class Board:
    """
    Mutable Board ADT.

    Rep:
      - grid is rows x cols
      - each cell has a string value
      - matched => face_up (usually true; you can enforce your exact rule)
    Safety:
      - guarded by an internal lock to be safe under concurrent HTTP requests
    """

    def __init__(self, rows: int, cols: int, values: List[str]):
        if rows <= 0 or cols <= 0:
            raise ValueError("rows/cols must be positive")
        if len(values) != rows * cols:
            raise ValueError("values length must equal rows*cols")

        self._rows = rows
        self._cols = cols
        self._lock = RLock()

        self._grid: List[List[Cell]] = []
        i = 0
        for r in range(rows):
            row_cells = []
            for c in range(cols):
                row_cells.append(Cell(value=values[i], face_up=False, matched=False))
                i += 1
            self._grid.append(row_cells)

        self._check_rep()

    def _check_rep(self) -> None:
        assert len(self._grid) == self._rows
        for r in range(self._rows):
            assert len(self._grid[r]) == self._cols
            for cell in self._grid[r]:
                assert isinstance(cell.value, str)
                if cell.matched:
                    # choose the invariant your rules want:
                    assert cell.face_up is True

    def size(self) -> Tuple[int, int]:
        return (self._rows, self._cols)

    def peek(self, pos: Coord) -> Cell:
        r, c = pos
        with self._lock:
            self._validate_coord(pos)
            return self._grid[r][c]

    def flip_up(self, pos: Coord) -> str:
        """Flip a card face-up and return its value (if allowed by rules)."""
        r, c = pos
        with self._lock:
            self._validate_coord(pos)
            cell = self._grid[r][c]
            if cell.matched:
                raise ValueError("cannot flip a matched card")
            if cell.face_up:
                raise ValueError("already face up")

            self._grid[r][c] = Cell(value=cell.value, face_up=True, matched=False)
            self._check_rep()
            return cell.value

    def flip_down(self, pos: Coord) -> None:
        r, c = pos
        with self._lock:
            self._validate_coord(pos)
            cell = self._grid[r][c]
            if cell.matched:
                raise ValueError("cannot flip down a matched card")
            if not cell.face_up:
                return
            self._grid[r][c] = Cell(value=cell.value, face_up=False, matched=False)
            self._check_rep()

    def mark_matched(self, pos1: Coord, pos2: Coord) -> None:
        """Mark two positions as permanently matched."""
        with self._lock:
            self._validate_coord(pos1)
            self._validate_coord(pos2)
            c1 = self._grid[pos1[0]][pos1[1]]
            c2 = self._grid[pos2[0]][pos2[1]]
            if not c1.face_up or not c2.face_up:
                raise ValueError("both must be face up to match")
            if c1.value != c2.value:
                raise ValueError("values do not match")

            self._grid[pos1[0]][pos1[1]] = Cell(value=c1.value, face_up=True, matched=True)
            self._grid[pos2[0]][pos2[1]] = Cell(value=c2.value, face_up=True, matched=True)
            self._check_rep()

    def _validate_coord(self, pos: Coord) -> None:
        r, c = pos
        if not (0 <= r < self._rows and 0 <= c < self._cols):
            raise ValueError("invalid coordinate")
