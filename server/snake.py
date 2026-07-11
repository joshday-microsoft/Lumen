"""Self-playing Snake for the LED wall.

Pure game logic (no I/O) so it stays testable. The board is walled (bounded), and
the AI treats walls as blocked cells — so it never drives into an edge. That means
the only way the snake dies is by trapping itself against its own body, which is
the reset trigger Josh asked for, while keeping the snake one clean continuous
shape on screen (no edge-wrapping into disconnected pieces).

The AI does BFS toward the food, with a flood-fill survival fallback when the food
isn't safely reachable. It plays a purposeful game, grows, and eventually boxes
itself in — then it's `dead`.

step() returns the *changed* cells for the frame so the renderer can update only
those pixels (fast over BLE) instead of redrawing the whole board.
"""

from __future__ import annotations

import random
from collections import deque

# roles the renderer maps to colors
HEAD, BODY, BG, FOOD = "head", "body", "bg", "food"

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

    # ---- helpers ----
    def _spawn_food(self) -> None:
        free = [(x, y) for y in range(self.n) for x in range(self.n) if (x, y) not in self.body]
        self.food = self.rng.choice(free) if free else None

    def _neighbors(self, cell):
        x, y = cell
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.n and 0 <= ny < self.n:  # walled board, no wrap
                yield (nx, ny)

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
            for nb in self._neighbors(cur):
                if nb not in prev and nb not in blocked:
                    prev[nb] = cur
                    q.append(nb)
        return None

    def _open_space(self, start, blocked, limit=80):
        seen = {start}
        q = deque([start])
        while q and len(seen) < limit:
            cur = q.popleft()
            for nb in self._neighbors(cur):
                if nb not in seen and nb not in blocked:
                    seen.add(nb)
                    q.append(nb)
        return len(seen)

    def _choose(self):
        head = self.snake[0]
        blocked = set(self.body)
        if self.grow == 0:
            blocked.discard(self.snake[-1])  # the tail cell will vacate this move
        path = self._bfs(head, self.food, blocked)
        if path and len(path) >= 2:
            return path[1]
        # no safe path to food: survive — head for the most open space
        best, best_space = None, -1
        for nb in self._neighbors(head):
            if nb in blocked:
                continue
            sp = self._open_space(nb, blocked)
            if sp > best_space:
                best_space, best = sp, nb
        return best

    # ---- main tick ----
    def step(self):
        """Advance one tick. Returns a list of (x, y, role) changed cells.
        Sets self.dead on self-collision (no change list needed then)."""
        self.steps += 1
        old_head = self.snake[0]
        nxt = self._choose()
        if nxt is None:
            self.dead = True
            return []
        tail = self.snake[-1]
        frees_tail = self.grow == 0
        occupied = self.body - ({tail} if frees_tail else set())
        if nxt in occupied:
            self.dead = True
            return []

        changes = [(old_head[0], old_head[1], BODY), (nxt[0], nxt[1], HEAD)]
        self.snake.appendleft(nxt)
        self.body.add(nxt)

        ate = nxt == self.food
        if ate:
            self.grow += 3
            self.score += 1
            self._spawn_food()
            if self.food is not None:
                changes.append((self.food[0], self.food[1], FOOD))

        if self.grow > 0:
            self.grow -= 1
        else:
            t = self.snake.pop()
            self.body.discard(t)
            if t != nxt:
                changes.append((t[0], t[1], BG))
        return changes

    def full_cells(self):
        """All lit cells for a from-scratch paint (start / after reset)."""
        cells = []
        for i, (x, y) in enumerate(self.snake):
            cells.append((x, y, HEAD if i == 0 else BODY))
        if self.food is not None:
            cells.append((self.food[0], self.food[1], FOOD))
        return cells

    def body_cells(self):
        return list(self.snake)
