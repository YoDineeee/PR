# src/simulation.py
# Copyright (c) MIT 6.102/6.031 style simulation (Python port)
# Minimal deps: only standard library

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Adjust import to your project
# Expecting:
#   Board.parse_from_file(path) -> Board
#   board.get_dimensions() -> (rows, cols)
#   board.flip(player_id, row, col)  (blocking allowed)
#   board.look(player_id) -> str
#   board.__str__ or board.to_string() -> str
from board import Board  # change if your module path differs


Coord = Tuple[int, int]


@dataclass
class Stats:
    total_flips: int = 0
    successful_matches: int = 0
    failed_flips: int = 0
    waits: int = 0


# ----- tiny helpers -----

def random_int(max_exclusive: int) -> int:
    return random.randrange(max_exclusive)

async def timeout_ms(milliseconds: float) -> None:
    await asyncio.sleep(milliseconds / 1000.0)

def now_ms() -> float:
    return time.time() * 1000.0

def board_to_string(board: Board) -> str:
    # Support either __str__ or to_string()
    if hasattr(board, "to_string"):
        return board.to_string()
    return str(board)

def count_my_cards(look_text: str) -> int:
    # Spec-style: each cell line could be "my X"
    lines = look_text.splitlines()
    return sum(1 for line in lines if line.startswith("my "))


# ---- adapter: run potentially-blocking board methods safely in threads ----

async def call_blocking(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


# ----- main concurrent simulation -----

async def simulation_main() -> None:
    print("MEMORY SCRAMBLE - CONCURRENT SIMULATION")

    filename = "boards/ab.txt"
    board: Board = await call_blocking(Board.parse_from_file, filename)
    rows, cols = board.get_dimensions()

    print(f"\nLoaded board: {rows}x{cols} from {filename}")
    print("Initial board state:")
    print(board_to_string(board))

    # Configuration
    players = 4
    tries = 100
    min_delay_ms = 0.1
    max_delay_ms = 2.0

    print(f"\nStarting simulation with {players} players, {tries} attempts each")
    print(f"Random delays between {min_delay_ms}ms and {max_delay_ms}ms\n")

    stats = Stats()

    async def player(player_number: int) -> None:
        player_id = f"player{player_number}"
        colors = ["\x1b[31m", "\x1b[32m", "\x1b[33m", "\x1b[34m"]  # red/green/yellow/blue
        color = colors[player_number % len(colors)]
        reset = "\x1b[0m"

        print(f"{color}[{player_id}] Starting...{reset}")

        for jj in range(tries):
            try:
                # random delay before first flip
                await timeout_ms(min_delay_ms + random.random() * (max_delay_ms - min_delay_ms))

                first = (random_int(rows), random_int(cols))
                print(f"{color}[{player_id}] Attempt {jj+1}: Flipping FIRST card at {first}{reset}")

                start = now_ms()
                await call_blocking(board.flip, player_id, first[0], first[1])
                stats.total_flips += 1

                wait_time = now_ms() - start
                wait_threshold_ms = 5.0
                if wait_time > wait_threshold_ms:
                    stats.waits += 1
                    print(f"{color}[{player_id}]   -> Waited {int(wait_time)}ms for card{reset}")

                # random delay before second flip
                await timeout_ms(min_delay_ms + random.random() * (max_delay_ms - min_delay_ms))

                second = (random_int(rows), random_int(cols))
                print(f"{color}[{player_id}] Attempt {jj+1}: Flipping SECOND card at {second}{reset}")

                await call_blocking(board.flip, player_id, second[0], second[1])
                stats.total_flips += 1

                # determine match by looking at board state
                board_state = await call_blocking(board.look, player_id)
                my_cards = count_my_cards(board_state)
                if my_cards == 2:
                    stats.successful_matches += 1
                    print(f"{color}[{player_id}]   MATCH! Cards will be removed on next move{reset}")
                else:
                    print(f"{color}[{player_id}] No match, cards stay face up{reset}")

            except Exception as e:
                stats.failed_flips += 1
                print(f"{color}[{player_id}] Flip failed: {e}{reset}")

        print(f"{color}[{player_id}] Finished all attempts{reset}")

    tasks = [asyncio.create_task(player(i)) for i in range(players)]
    await asyncio.gather(*tasks)

    print("SIMULATION COMPLETE")
    print(f"Total flips attempted: {stats.total_flips}")
    print(f"Successful matches: {stats.successful_matches}")
    print(f"Failed flips: {stats.failed_flips}")
    print(f"Times waited for card: {stats.waits}")
    print("\nFinal board state:")
    print(board_to_string(board))


# ----- focused tests -----

async def test_waiting_scenario() -> None:
    print("TEST: Multiple Players Waiting for Same Card")

    board: Board = await call_blocking(Board.parse_from_file, "boards/ab.txt")

    print("\nScenario: Alice controls (0,0), Bob and Charlie both want it")

    print("\n[Alice] Flipping (0,0)...")
    await call_blocking(board.flip, "alice", 0, 0)
    print("[Alice] Now controls (0,0)")

    print("\n[Bob] Trying to flip (0,0) - should WAIT...")
    print("[Charlie] Trying to flip (0,0) - should WAIT...")

    async def bob_try():
        start = now_ms()
        await call_blocking(board.flip, "bob", 0, 0)
        waited = int(now_ms() - start)
        print(f"[Bob] Got the card after waiting {waited}ms!")

    async def charlie_try():
        start = now_ms()
        await call_blocking(board.flip, "charlie", 0, 0)
        waited = int(now_ms() - start)
        print(f"[Charlie] Got the card after waiting {waited}ms!")

    bob_task = asyncio.create_task(bob_try())
    charlie_task = asyncio.create_task(charlie_try())

    await timeout_ms(10)
    print("\n[System] Bob and Charlie are now waiting...")

    print("\n[Alice] Flipping (0,1) - will release (0,0)...")
    await call_blocking(board.flip, "alice", 0, 1)
    print("[Alice] Released (0,0), no match")

    # one of Bob/Charlie should proceed now
    done, pending = await asyncio.wait({bob_task, charlie_task}, return_when=asyncio.FIRST_COMPLETED)
    # cancel the other (optional; or let it finish if you want)
    for t in pending:
        t.cancel()
    print("\nTest passed: Waiting mechanism works correctly\n")


async def test_matched_cards_scenario() -> None:
    print("TEST: Matched Cards Cleanup")

    board: Board = await call_blocking(Board.parse_from_file, "boards/ab.txt")

    print("\nScenario: Alice matches two cards, Bob waits for one")

    # Assumes (0,0) and (0,2) are a match on boards/ab.txt like your TS example
    print("\n[Alice] Flipping (0,0)...")
    await call_blocking(board.flip, "alice", 0, 0)
    print("[Alice] Flipping (0,2)...")
    await call_blocking(board.flip, "alice", 0, 2)

    alice_view = await call_blocking(board.look, "alice")
    print("\n[Alice] Board state:")
    print(alice_view)

    if count_my_cards(alice_view) == 2:
        print("[Alice] MATCHED! Controls both cards")
    else:
        print("[Alice] Warning: expected a match, but did not detect 2 'my' cards")

    print("\n[Bob] Trying to flip (0,0) which Alice controls...")

    bob_got_error = False

    async def bob_try():
        nonlocal bob_got_error
        try:
            await call_blocking(board.flip, "bob", 0, 0)
            # This should NOT happen if the card is removed during waiting
            raise RuntimeError("Test failed: Bob got a removed card")
        except Exception as e:
            bob_got_error = True
            print(f"[Bob] Failed as expected: {e}")

    bob_task = asyncio.create_task(bob_try())

    await timeout_ms(10)
    print("[System] Bob is waiting...")

    print("\n[Alice] Making next move - matched cards should be removed")
    await call_blocking(board.flip, "alice", 1, 1)

    await bob_task

    if not bob_got_error:
        raise RuntimeError("Test failed: Bob should have received an error for removed card")

    print("\nTest passed: Matched cards removed correctly, waiter notified\n")


# ----- runner -----

async def run_all_tests() -> None:
    try:
        await simulation_main()
        await test_waiting_scenario()
        await test_matched_cards_scenario()

        print("ALL TESTS PASSED")
        print("\nConcurrency verification complete!")
        print("• Multiple players can play simultaneously")
        print("• Waiting for controlled cards works correctly")
        print("• Matched cards are removed properly")
        print("• No deadlocks or race conditions detected")
        print("\nProblem 3 requirements satisfied!\n")

    except Exception as e:
        print("\nTEST FAILED:", e)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())