"""
Authoritative multiplayer prototype server.

Protocol (JSON over WebSocket):
- Client -> Server messages:
  - {"type": "list"}
  - {"type": "create", "name": "My Game"}
  - {"type": "join", "game_id": "...", "player_name": "Alice"}
  - {"type": "input", "game_id": "...", "player_id": "...", "input": {...}}

- Server -> Client messages:
  - {"type": "lobby", "games": [{"id":...,"name":...,"players":n}, ...]}
  - {"type": "joined", "game_id": "...", "player_id": "..."}
  - {"type": "state", "game_id": "...", "snapshot": {...}}

This is intentionally minimal; extend for authentication, UDP, compression, etc.
"""
import asyncio
import json
import logging
import time
from typing import Dict

import websockets

from game_sim import GameInstance

logging.basicConfig(level=logging.INFO)

GAMES: Dict[str, GameInstance] = {}
# mapping websocket -> (game_id, player_id)
CLIENT_MAP = {}

async def send(ws, obj):
    try:
        await ws.send(json.dumps(obj))
    except Exception:
        logging.exception('send failed')


async def broadcast_lobby():
    # send current lobby list to all connected clients
    lobby = {'type':'lobby', 'games':[{'id':g.id,'name':g.name,'players':len(g.players)} for g in GAMES.values()]}
    coros = []
    for ws in list(CLIENT_MAP.keys()):
        coros.append(send(ws, lobby))
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)

async def handle_message(ws, msg):
    try:
        obj = json.loads(msg)
    except Exception:
        return
    t = obj.get('type')
    if t == 'list':
        await send(ws, {'type':'lobby', 'games':[{'id':g.id,'name':g.name,'players':len(g.players)} for g in GAMES.values()]})
    elif t == 'create':
        name = obj.get('name','Game')
        g = GameInstance(name)
        GAMES[g.id] = g
        logging.info(f'game created: id={g.id} name={g.name}')
        await send(ws, {'type':'created','game_id':g.id,'name':g.name})
        # notify all clients that lobby changed
        await broadcast_lobby()
    elif t == 'join':
        gid = obj.get('game_id')
        pname = obj.get('player_name','Player')
        g = GAMES.get(gid)
        if not g:
            await send(ws, {'type':'error','msg':'game not found'})
            return
        pid = str(time.time()) + '_' + pname
        g.add_player(pid, pname)
        CLIENT_MAP[ws] = (gid, pid)
        logging.info(f'player joined: game_id={gid} player_id={pid} name={pname}')
        await send(ws, {'type':'joined','game_id':gid,'player_id':pid})
        # broadcast updated lobby (player counts)
        await broadcast_lobby()
    elif t == 'input':
        gid = obj.get('game_id')
        pid = obj.get('player_id')
        inp = obj.get('input',{})
        g = GAMES.get(gid)
        if g:
            g.apply_input(pid, inp)

async def watcher():
    # Broadcast snapshots periodically
    while True:
        await asyncio.sleep(0.05)
        to_send = []
        for gid, g in list(GAMES.items()):
            g.tick()
            snap = g.snapshot()
            to_send.append((gid, snap))
        if not to_send:
            continue
        # log a short summary
        try:
            summary = ', '.join([f"{gid[:6]}:{len(snap)}p" for gid, snap in to_send])
            logging.info(f"watcher snapshot summary: {summary}")
        except Exception:
            pass
        # broadcast per-game
        for gid, snap in to_send:
            # send to all websockets in CLIENT_MAP belonging to gid
            coros = []
            for ws, (wgid, pid) in list(CLIENT_MAP.items()):
                if wgid == gid:
                    coros.append(send(ws, {'type':'state','game_id':gid,'snapshot':snap}))
            if coros:
                await asyncio.gather(*coros, return_exceptions=True)

async def handler(ws, path=None):
    logging.info('client connected')
    try:
        async for msg in ws:
            await handle_message(ws, msg)
    except websockets.ConnectionClosed:
        pass
    finally:
        # remove mapping and player
        info = CLIENT_MAP.pop(ws, None)
        if info:
            gid, pid = info
            g = GAMES.get(gid)
            if g:
                g.remove_player(pid)
                # if game now empty and previously had players, remove it
                if len(g.players) == 0 and getattr(g, 'ever_had_players', False):
                    try:
                        del GAMES[gid]
                        logging.info(f'game removed (empty): id={gid}')
                    except KeyError:
                        pass
        # broadcast lobby update so clients refresh lists
        try:
            await broadcast_lobby()
        except Exception:
            pass
        logging.info('client disconnected')

async def _server_main(host: str, port: int):
    # Use async context manager for websockets server (compatible with newer websockets)
    async with websockets.serve(handler, host, port):
        logging.info(f"Server running on {host}:{port}")
        await watcher()  # runs until cancelled


def main(host: str = '0.0.0.0', port: int = 8765):
    try:
        asyncio.run(_server_main(host, port))
    except KeyboardInterrupt:
        logging.info('Server shutting down (keyboard interrupt)')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Run MowGrass multiplayer server')
    p.add_argument('--host', default='0.0.0.0')
    p.add_argument('--port', type=int, default=8765)
    args = p.parse_args()
    main(host=args.host, port=args.port)
