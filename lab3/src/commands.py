# src/commands.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
from .board import Board, Coord

@dataclass
class GameState:
    board: Board
    # Track the current “turn state” (example: 0/1/2 flips this turn)
    first_pick: Optional[Coord] = None
    second_pick: Optional[Coord] = None


def new_game(rows: int, cols: int, values: List[str]) -> GameState:
    return GameState(board=Board(rows, cols, values))


def pick(state: GameState, pos: Coord) -> Dict:
    """
    Example command: flip a card and apply matching rules.
    Return a JSON-serializable dict for API response.
    """
    value = state.board.flip_up(pos)

    if state.first_pick is None:
        state.first_pick = pos
        return {"status": "ok", "flipped": pos, "value": value, "match": None}

    if state.second_pick is None:
        state.second_pick = pos

        first = state.first_pick
        v1 = state.board.peek(first).value
        v2 = state.board.peek(pos).value

        if v1 == v2:
            state.board.mark_matched(first, pos)
            state.first_pick = None
            state.second_pick = None
            return {"status": "ok", "flipped": pos, "value": value, "match": True}

        # Not a match: keep them face-up for now; caller can “resolve” (flip down) later
        return {"status": "ok", "flipped": pos, "value": value, "match": False, "pending_hide": [first, pos]}

    # If already 2 picks are up, force resolve before next pick (rule choice)
    raise ValueError("turn already has two picks; resolve first")


def resolve_mismatch(state: GameState) -> Dict:
    """If last turn was a mismatch, flip both back down."""
    if state.first_pick is None or state.second_pick is None:
        return {"status": "ok", "resolved": False}

    p1, p2 = state.first_pick, state.second_pick
    # if they were matched, they won't flip down anyway
    state.board.flip_down(p1)
    state.board.flip_down(p2)
    state.first_pick = None
    state.second_pick = None
    return {"status": "ok", "resolved": True, "hidden": [p1, p2]}
