"""Self-playing Snake for the LED wall — classic rules.

Pure game logic (no I/O) so it stays testable. Real Snake rules:
  - The board has BORDERS. Running into a wall kills the snake. No wrap-around.
  - Running into your own body kills the snake.
  - Either death is terminal (`dead`) → the renderer does a hard reset.

The AI is deliberately DUMB: no pathfinding. It mostly beelines toward the food but
wanders off at random (see WANDER), so it boxes itself in fast and dies often —
short, erratic, entertaining games rather than a near-perfect immortal snake.
"""

from __future__ import annotations

import random
from collections import deque

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class SnakeGame:
    def __init__(self, n: int, rng: random.Random | None = None):
        self.n = n
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        c = self.n // 2
        # head first; start length 3 heading right
        self.snake: deque[tuple[int, int]] = deque([(c, c), (c - 1, c), (c - 2, c)])
        self.body: set[tuple[int, int]] = set(self.snake)
        self.grow = 0
        self.dead = False
        self.score = 0
        self.steps = 0
        self._spawn_food()

    def _in_bounds(self, cell) -> bool:
        x, y = cell
        return 0 <= x < self.n and 0 <= y < self.n

    def _spawn_food(self) -> None:
        free = [(x, y) for y in range(self.n) for x in range(self.n) if (x, y) not in self.body]
        self.food = self.rng.choice(free) if free else None

    WANDER = 0.15  # chance of a random move instead of beelining — the "dumb" knob

    def _choose(self):
        """A dumb, hungry snake: no pathfinding. It mostly beelines toward the food
        (nearest safe step by Manhattan distance) but WANDERs off at random, so it
        boxes itself in fast and dies often. The returned cell MAY be a wall (out of
        bounds) or its own body — step() turns that into a death."""
        head = self.snake[0]
        hx, hy = head
        fx, fy = self.food if self.food else head
        blocked = set(self.body)
        if self.grow == 0:
            blocked.discard(self.snake[-1])  # the tail cell vacates this move

        moves = []
        for dx, dy in DIRS:
            nb = (hx + dx, hy + dy)
            safe = self._in_bounds(nb) and nb not in blocked
            dist = abs(nb[0] - fx) + abs(nb[1] - fy)
            moves.append((0 if safe else 1, dist, nb))

        safe_moves = [m for m in moves if m[0] == 0]
        if safe_moves and self.rng.random() < self.WANDER:
            return self.rng.choice(safe_moves)[2]   # wander (a "mistake")
        moves.sort(key=lambda m: (m[0], m[1]))       # safe first, then toward food
        return moves[0][2]

    def step(self) -> None:
        """Advance one tick; set self.dead on wall- or self-collision."""
        self.steps += 1
        nxt = self._choose()
        if not self._in_bounds(nxt):          # hit a border
            self.dead = True
            return
        frees_tail = self.grow == 0
        occupied = self.body - ({self.snake[-1]} if frees_tail else set())
        if nxt in occupied:                    # ran into itself
            self.dead = True
            return

        self.snake.appendleft(nxt)
        self.body.add(nxt)
        if nxt == self.food:
            self.grow += 3
            self.score += 1
            self._spawn_food()
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.discard(self.snake.pop())
