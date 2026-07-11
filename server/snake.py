"""Self-playing Snake for the LED wall — classic rules.

Pure game logic (no I/O) so it stays testable. Real Snake rules:
  - The board has BORDERS. Running into a wall kills the snake. No wrap-around.
  - Running into your own body kills the snake.
  - Either death is terminal (`dead`) → the renderer does a hard reset.

The AI is a *hungry* snake, not a perfect one: it takes the shortest safe path to
the food when one exists (BFS), but when the food is walled off it charges greedily
toward it and can splat into a wall or its own tail. So it plays a real game and
genuinely dies — no immortal wall-crawling.
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

    def _free_neighbors(self, cell, blocked):
        """In-bounds, non-blocked neighbors — used for pathfinding only."""
        x, y = cell
        for dx, dy in DIRS:
            nb = (x + dx, y + dy)
            if self._in_bounds(nb) and nb not in blocked:
                yield nb

    def _bfs(self, start, goal, blocked):
        if goal is None:
            return None
        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == goal:
                path = [cur]
                while prev[cur] is not None:
                    cur = prev[cur]
                    path.append(cur)
                return path[::-1]
            for nb in self._free_neighbors(cur, blocked):
                if nb not in prev:
                    prev[nb] = cur
                    q.append(nb)
        return None

    def _choose(self):
        """Return the next head cell — which MAY be a wall (out of bounds) or the
        snake's own body when the snake has boxed itself in. step() turns that into
        a death. No survival cheat: a hungry snake commits to chasing the food."""
        head = self.snake[0]
        blocked = set(self.body)
        if self.grow == 0:
            blocked.discard(self.snake[-1])  # the tail cell vacates this move
        path = self._bfs(head, self.food, blocked)
        if path and len(path) >= 2:
            return path[1]
        # boxed off from the food: prefer a still-safe move, else charge greedily
        # toward the food (Manhattan) — which may well be into a wall or the body.
        fx, fy = self.food if self.food else head
        hx, hy = head
        best, best_key = None, None
        for dx, dy in DIRS:
            nb = (hx + dx, hy + dy)
            safe = self._in_bounds(nb) and nb not in blocked
            dist = abs(nb[0] - fx) + abs(nb[1] - fy)
            key = (0 if safe else 1, dist)  # safe first, then closest to food
            if best_key is None or key < best_key:
                best_key, best = key, nb
        return best

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
