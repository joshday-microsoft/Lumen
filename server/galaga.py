"""A self-playing mock of Galaga for the 32x32 LED wall.

Pure game logic + a render() that returns {(x, y): (r, g, b)} for the lit cells of
the current frame (black elsewhere). The renderer diffs frames and only pushes
changed pixels via Graffiti — so it never full-refreshes the panel (no flashing).

It captures the arcade beats: a colored formation of bugs up top, an AI player
ship at the bottom that strafes and fires, enemies that peel off and dive in
swooping arcs while dropping bombs, explosions, wave clears, and a game-over
reset. No wrap; everything stays on the board.
"""

from __future__ import annotations

import math
import random

# palette
BOSS = (235, 60, 60)        # top-row boss galaga (red)
BUTTERFLY = (235, 120, 225)  # mid row (magenta)
BEE = (240, 220, 70)        # bottom row (yellow)
SHIP = (120, 205, 255)      # player hull
SHIP_TIP = (255, 255, 255)  # player nose
PBULLET = (255, 255, 190)   # player shot
EBULLET = (255, 95, 95)     # enemy bomb
EXPL = [(255, 245, 180), (255, 150, 45), (190, 40, 20)]  # explosion by age
STAR = (30, 30, 48)         # faint starfield

ROW_COLORS = [BOSS, BUTTERFLY, BEE]

# sprite cell offsets (relative to sprite origin)
BUG_CELLS = [(-1, 0), (0, 0), (1, 0), (-1, 1), (1, 1)]      # little bug
SHIP_CELLS = [(0, -1), (-1, 0), (0, 0), (1, 0)]            # ▲ ship


class Galaga:
    def __init__(self, n: int, rng: random.Random | None = None):
        self.n = n
        self.rng = rng or random.Random()
        self.stars = [(self.rng.randrange(n), self.rng.randrange(n)) for _ in range(10)]
        self.reset_all()

    # ---------- setup ----------
    def reset_all(self) -> None:
        self.score = 0
        self.wave = 0
        self.lives = 3
        self.px = self.n // 2
        self.pbullets: list[list[int]] = []
        self.ebullets: list[list[int]] = []
        self.divers: list[dict] = []
        self.explosions: list[list] = []   # [x, y, age]
        self.fire_cd = 0
        self.dive_cd = 22
        self.hit_flash = 0
        self.dead = False
        self._new_wave()

    def _new_wave(self) -> None:
        self.wave += 1
        cols = [3, 8, 13, 18, 23, 28]
        rows = [4, 8, 12]
        self.enemies: dict[tuple[int, int], dict] = {}
        for r, ry in enumerate(rows):
            for c, cx in enumerate(cols):
                self.enemies[(c, r)] = {"x": cx, "y": ry, "color": ROW_COLORS[r],
                                        "alive": True, "diving": False}
        self.dive_cd = 30

    # ---------- helpers ----------
    def _alive(self):
        return [e for e in self.enemies.values() if e["alive"] and not e["diving"]]

    def _bug_cells(self, cx, cy):
        for dx, dy in BUG_CELLS:
            x, y = cx + dx, cy + dy
            if 0 <= x < self.n and 0 <= y < self.n:
                yield (x, y)

    def _ship_cells(self):
        for dx, dy in SHIP_CELLS:
            x, y = self.px + dx, self.n - 2 + dy
            if 0 <= x < self.n and 0 <= y < self.n:
                yield (x, y)

    def _boom(self, x, y):
        self.explosions.append([x, y, 0])

    # ---------- AI player ----------
    def _think(self):
        # danger: an enemy bomb or diver bearing down near our column -> dodge
        threats = [b[0] for b in self.ebullets if b[1] > self.n - 12]
        threats += [d["x"] for d in self.divers if d["y"] > self.n - 14]
        for tx in threats:
            if abs(tx - self.px) <= 1:
                self.px += 1 if tx <= self.px else -1
                self.px = max(1, min(self.n - 2, self.px))
                return
        # otherwise hunt: line up under the lowest-value nearest target
        targets = self._alive() + self.divers
        if targets:
            tgt = min(targets, key=lambda e: (abs(e["x"] - self.px), e["y"]))
            if tgt["x"] > self.px:
                self.px += 1
            elif tgt["x"] < self.px:
                self.px -= 1
            self.px = max(1, min(self.n - 2, self.px))
            if abs(tgt["x"] - self.px) <= 1 and self.fire_cd == 0:
                self.pbullets.append([self.px, self.n - 3])
                self.fire_cd = 5

    # ---------- one tick ----------
    def step(self) -> None:
        if self.fire_cd:
            self.fire_cd -= 1
        if self.hit_flash:
            self.hit_flash -= 1

        self._think()

        # player bullets move up
        for b in self.pbullets:
            b[1] -= 1
        self.pbullets = [b for b in self.pbullets if b[1] >= 0]

        # enemy bombs move down
        for b in self.ebullets:
            b[1] += 1
        self.ebullets = [b for b in self.ebullets if b[1] < self.n]

        # spawn a diver
        if self.dive_cd > 0:
            self.dive_cd -= 1
        alive_formation = self._alive()
        if self.dive_cd == 0 and alive_formation:
            e = self.rng.choice(alive_formation)
            e["diving"] = True
            self.divers.append({
                "e": e, "x": e["x"], "y": e["y"], "t": 0,
                "x0": e["x"], "color": e["color"],
                "sway": self.rng.choice((-1, 1)) * (self.rng.random() * 0.5 + 0.4),
            })
            self.dive_cd = self.rng.randint(18, 40)

        # advance divers (swoop: down + sine sway toward player)
        for d in list(self.divers):
            d["t"] += 1
            d["y"] += 1
            target_bias = 0.15 * (self.px - d["x"])
            d["x"] = int(round(d["x0"] + math.sin(d["t"] * 0.4) * 6 * d["sway"] + target_bias * d["t"] / 6))
            d["x"] = max(1, min(self.n - 2, d["x"]))
            if self.rng.random() < 0.06:  # drop a bomb
                self.ebullets.append([d["x"], d["y"] + 1])
            if d["y"] >= self.n - 1:       # survived the run -> back to formation
                d["e"]["diving"] = False
                self.divers.remove(d)

        self._collisions()

        # age explosions
        for ex in self.explosions:
            ex[2] += 1
        self.explosions = [e for e in self.explosions if e[2] < 3]

        # wave cleared?
        if not any(e["alive"] for e in self.enemies.values()):
            self._new_wave()

    def _collisions(self):
        # player bullets vs enemies (formation + divers)
        for b in list(self.pbullets):
            bx, by = b
            hit = False
            for e in self.enemies.values():
                if e["alive"] and not e["diving"] and (bx, by) in set(self._bug_cells(e["x"], e["y"])):
                    e["alive"] = False
                    self._boom(e["x"], e["y"])
                    self.score += 10
                    hit = True
                    break
            if not hit:
                for d in list(self.divers):
                    if (bx, by) in set(self._bug_cells(d["x"], d["y"])):
                        d["e"]["alive"] = False
                        self.divers.remove(d)
                        self._boom(d["x"], d["y"])
                        self.score += 20
                        hit = True
                        break
            if hit:
                self.pbullets.remove(b)

        # enemy bombs / divers vs player
        ship = set(self._ship_cells())
        struck = any((bx, by) in ship for bx, by in self.ebullets)
        struck = struck or any(
            ship & set(self._bug_cells(d["x"], d["y"])) for d in self.divers
        )
        if struck and self.hit_flash == 0:
            self._boom(self.px, self.n - 2)
            self.lives -= 1
            self.hit_flash = 12
            self.ebullets.clear()
            for d in list(self.divers):
                d["e"]["diving"] = False
            self.divers.clear()
            if self.lives <= 0:
                self.dead = True

    # ---------- render ----------
    def render(self) -> dict:
        cells: dict[tuple[int, int], tuple[int, int, int]] = {}
        for (sx, sy) in self.stars:
            cells[(sx, sy)] = STAR
        # formation
        for e in self.enemies.values():
            if e["alive"] and not e["diving"]:
                for c in self._bug_cells(e["x"], e["y"]):
                    cells[c] = e["color"]
        # divers
        for d in self.divers:
            for c in self._bug_cells(d["x"], d["y"]):
                cells[c] = d["color"]
        # bullets
        for (bx, by) in self.ebullets:
            if 0 <= bx < self.n and 0 <= by < self.n:
                cells[(bx, by)] = EBULLET
        for (bx, by) in self.pbullets:
            if 0 <= bx < self.n and 0 <= by < self.n:
                cells[(bx, by)] = PBULLET
        # player (blink while hit)
        if self.hit_flash == 0 or self.hit_flash % 2 == 0:
            for i, c in enumerate(self._ship_cells()):
                cells[c] = SHIP_TIP if i == 0 else SHIP
        # explosions on top
        for (ex, ey, age) in self.explosions:
            col = EXPL[min(age, len(EXPL) - 1)]
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                x, y = ex + dx, ey + dy
                if 0 <= x < self.n and 0 <= y < self.n:
                    cells[(x, y)] = col
        return cells
