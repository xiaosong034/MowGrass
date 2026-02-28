# Multiplayer prototype for MowGrass

This workspace contains a minimal prototype demonstrating how to convert the single-player game into an authoritative multiplayer setup.

Files added:

- `game_sim.py`: lightweight simulation primitives (`GameInstance`, `PlayerState`).
- `server.py`: simple authoritative server using `websockets`. Maintains lobby and game instances and broadcasts snapshots.
- `net_client.py`: minimal client that creates/joins a game and sends periodic position/HP updates.
- `requirements.txt`: contains `websockets` dependency.

Quick start (Windows PowerShell):

```powershell
python -m pip install -r requirements.txt
python server.py
# in another terminal (or multiple) start headless test clients which auto-join or create a room:
python net_client.py ws://localhost:8765
python net_client.py ws://localhost:8765
# or run the Pygame client (will open a window):
python game_main.py --net
```

Notes:
 - This is a prototype to demonstrate the architecture (lobby, authoritative server, simple state sync).
 - The `net_client.py` will auto-join an existing room listed in the lobby or create one if none exist.
 - `game_main.py --net` launches the game in network mode and will render other players using a simple interpolation of server snapshots.
