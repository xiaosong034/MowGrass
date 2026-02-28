"""
Minimal game simulation module for multiplayer prototype.

Contains lightweight PlayerState and GameInstance classes
that the authoritative server will use to track and broadcast
player positions, HP, equipment and score.
"""
from dataclasses import dataclass, asdict
import time
import threading
import uuid
from typing import Dict


@dataclass
class PlayerState:
    id: str
    name: str
    x: float = 0.0
    y: float = 0.0
    hp: int = 100
    max_hp: int = 100
    score: int = 0
    equipment: Dict = None

    def to_dict(self):
        return asdict(self)


class GameInstance:
    def __init__(self, name: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.players: Dict[str, PlayerState] = {}
        self.lock = threading.Lock()
        self.last_tick = time.time()
        self.created_at = time.time()
        self.ever_had_players = False

    def add_player(self, pid: str, name: str):
        with self.lock:
            ps = PlayerState(id=pid, name=name, x=0.0, y=0.0, equipment={})
            self.players[pid] = ps
            self.ever_had_players = True
            return ps

    def remove_player(self, pid: str):
        with self.lock:
            if pid in self.players:
                del self.players[pid]

    def apply_input(self, pid: str, inp: dict):
        """Apply a minimal input dict to the player's state.

        Expected keys: x, y, hp, score, equipment (partial)
        """
        with self.lock:
            p = self.players.get(pid)
            if not p:
                return
            if 'x' in inp: p.x = float(inp['x'])
            if 'y' in inp: p.y = float(inp['y'])
            if 'hp' in inp: p.hp = int(inp['hp'])
            if 'score' in inp: p.score = int(inp['score'])
            if 'equipment' in inp:
                # shallow merge
                if p.equipment is None: p.equipment = {}
                p.equipment.update(inp['equipment'])

    def snapshot(self):
        with self.lock:
            return {pid: p.to_dict() for pid, p in self.players.items()}

    def tick(self):
        # placeholder for server-side simulation (AI, monsters, collisions)
        self.last_tick = time.time()
