# Lab 3 Execution Report

**Name:** Mohamed Dhiaeddine Hassine  
**Group:** FAF-233  

## Project Overview

Lab 3 implements a web-based Memory Scramble game, demonstrating full-stack web development capabilities. The project combines backend game logic, RESTful API design, and frontend user interface to create an interactive gaming experience.

## Board Implementation

### Thread-Safe Board Data Structure
The board uses immutable cells and thread-safe operations:

```python
@dataclass(frozen=True)
class Cell:
    value: str
    face_up: bool = False
    matched: bool = False

class Board:
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
```

The board uses frozen dataclasses for cells to ensure immutability, while the board itself uses a reentrant lock (RLock) to coordinate access to the mutable grid state.

### Card Flipping Operations
The board provides atomic operations for card manipulation:

```python
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
```

These operations ensure that card state changes are atomic and maintain board invariants through the `_check_rep()` method.

## Game State Management

### Turn-Based Game Logic
The commands module manages game state and turn flow:

```python
@dataclass
class GameState:
    board: Board
    first_pick: Optional[Coord] = None
    second_pick: Optional[Coord] = None

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

        return {"status": "ok", "flipped": pos, "value": value, "match": False, "pending_hide": [first, pos]}

    raise ValueError("turn already has two picks; resolve first")
```

The game state tracks the current turn (first and second picks) and enforces the game rules through the pick method.

### Turn Resolution
Mismatched pairs are resolved through a separate operation:

```python
def resolve_mismatch(state: GameState) -> Dict:
    """If last turn was a mismatch, flip both back down."""
    if state.first_pick is None or state.second_pick is None:
        return {"status": "ok", "resolved": False}

    p1, p2 = state.first_pick, state.second_pick
    state.board.flip_down(p1)
    state.board.flip_down(p2)
    state.first_pick = None
    state.second_pick = None
    return {"status": "ok", "resolved": True, "hidden": [p1, p2]}
```

This allows the client to control the timing of when mismatched cards are flipped back down, enabling user experience improvements like brief delays for memorization.

## REST API Implementation

### Flask Application Structure
The server provides a clean REST interface:

```python
from flask import Flask, request, jsonify
from typing import List
from . import commands

app = Flask(__name__)
STATE = None

@app.post("/new")
def api_new():
    global STATE
    data = request.get_json(force=True)

    rows = int(data["rows"])
    cols = int(data["cols"])
    values: List[str] = list(data["values"])
    STATE = commands.new_game(rows, cols, values)
    return jsonify({"status": "ok"})

@app.post("/pick")
def api_pick():
    if STATE is None:
        return jsonify({"status": "error", "message": "game not created"}), 400

    data = request.get_json(force=True)
    r = int(data["row"])
    c = int(data["col"])

    try:
        result = commands.pick(STATE, (r, c))
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.post("/resolve")
def api_resolve():
    if STATE is None:
        return jsonify({"status": "error", "message": "game not created"}), 400
    try:
        result = commands.resolve_mismatch(STATE)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
```

The API uses standard HTTP status codes and JSON responses for clear client communication.

### Error Handling
The server provides comprehensive error handling:

```python
try:
    result = commands.pick(STATE, (r, c))
    return jsonify(result)
except Exception as e:
    return jsonify({"status": "error", "message": str(e)}), 400
```

This ensures that invalid operations (like trying to flip an already face-up card) return appropriate error responses to the client.

## Frontend Implementation

### Dynamic Board Rendering
The frontend dynamically creates the game board:

```javascript
function renderBoard(r, c) {
  boardDiv.innerHTML = "";
  boardDiv.style.display = "grid";
  boardDiv.style.gridTemplateColumns = `repeat(${c}, 80px)`;
  boardDiv.style.gap = "10px";

  for (let i = 0; i < r; i++) {
    for (let j = 0; j < c; j++) {
      const btn = document.createElement("button");
      btn.textContent = "?";
      btn.style.height = "80px";
      btn.addEventListener("click", () => onPick(i, j, btn));
      boardDiv.appendChild(btn);
    }
  }
}
```

The board is rendered as a CSS grid with interactive buttons for each card position.

### AJAX Communication
The frontend communicates with the backend through AJAX:

```javascript
async function onPick(row, col, btn) {
  const res = await fetch("/api/pick", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({row, col})
  });
  const data = await res.json();

  if (data.status !== "ok") {
    alert(data.message);
    return;
  }

  btn.textContent = data.value;

  if (data.match === false) {
    setTimeout(async () => {
      await fetch("/api/resolve", { method: "POST" });
      renderBoard(rows, cols);
    }, 700);
  }
}
```

The client handles both successful picks and mismatches, with a brief delay before resolving mismatches to improve user experience.

## Concurrency and Testing

### Unit Testing
The board logic is thoroughly tested:

```python
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
```

These tests verify the core game mechanics and edge cases, ensuring the board maintains its invariants.

### Thread Safety Validation
The board includes representation checking:

```python
def _check_rep(self) -> None:
    assert len(self._grid) == self._rows
    for r in range(self._rows):
        assert len(self._grid[r]) == self._cols
        for cell in self._grid[r]:
            assert isinstance(cell.value, str)
            if cell.matched:
                assert cell.face_up is True
```

This invariant checking runs after every state change to ensure the board remains in a valid state.

## Advanced Features

### Simulation Framework
The simulation module provides concurrent testing:

```python
async def simulation_main() -> None:
    print("MEMORY SCRAMBLE - CONCURRENT SIMULATION")
    
    filename = "boards/ab.txt"
    board: Board = await call_blocking(Board.parse_from_file, filename)
    rows, cols = board.get_dimensions()

    players = 4
    tries = 100
    min_delay_ms = 0.1
    max_delay_ms = 2.0

    async def player(player_number: int) -> None:
        player_id = f"player{player_number}"
        for jj in range(tries):
            try:
                await timeout_ms(min_delay_ms + random.random() * (max_delay_ms - min_delay_ms))
                first = (random_int(rows), random_int(cols))
                await call_blocking(board.flip, player_id, first[0], first[1])
                
                await timeout_ms(min_delay_ms + random.random() * (max_delay_ms - min_delay_ms))
                second = (random_int(rows), random_int(cols))
                await call_blocking(board.flip, player_id, second[0], second[1])
                
                board_state = await call_blocking(board.look, player_id)
                my_cards = count_my_cards(board_state)
                if my_cards == 2:
                    print(f"{color}[{player_id}] MATCH!")
            except Exception as e:
                print(f"{color}[{player_id}] Flip failed: {e}")
```

This simulation tests the board's ability to handle concurrent access from multiple players, validating the thread safety implementation.

## Conclusion

Lab 3 successfully demonstrates full-stack web development capabilities through the implementation of a complete Memory Scramble game. The project showcases proper separation of concerns, thread-safe concurrent programming, and modern web development practices.

The implementation provides a solid foundation for understanding web application architecture, RESTful API design, and frontend-backend integration. The modular design and comprehensive testing ensure maintainability and reliability.

This project serves as an excellent example of integrating game logic, web services, and user interface to create a complete interactive application.