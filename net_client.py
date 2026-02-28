"""
Headless test client (aiohttp) for the multiplayer prototype.

Usage:
  python net_client.py ws://SERVER:PORT [proxy]

Prints lobby/created/joined/state messages and sends periodic inputs.
"""
import asyncio
import json
import random
import sys
import time
import aiohttp


async def interact(uri, proxy: str = None):
    print('net_client: connecting to', uri, 'proxy=', proxy)
    session = aiohttp.ClientSession()
    try:
        async with session.ws_connect(uri, proxy=proxy) as ws:
            print('net_client: connected')
            await ws.send_str(json.dumps({'type': 'list'}))

            async def sender():
                await asyncio.sleep(0.1)
                await ws.send_str(json.dumps({'type': 'create', 'name': 'Demo Game'}))

            async def receiver():
                player_id = None
                game_id = None
                while True:
                    msg = await ws.receive()
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    obj = json.loads(msg.data)
                    t = obj.get('type')
                    if t == 'lobby':
                        games = obj.get('games')
                        print('Lobby:', games)
                        if games:
                            gid = games[0]['id']
                            await ws.send_str(json.dumps({'type': 'join', 'game_id': gid, 'player_name': 'Client' + str(int(time.time()))}))
                        else:
                            await ws.send_str(json.dumps({'type': 'create', 'name': 'Demo Game'}))
                    elif t == 'created':
                        game_id = obj['game_id']
                        print('Created game', game_id)
                        await ws.send_str(json.dumps({'type': 'join', 'game_id': game_id, 'player_name': 'Client' + str(int(time.time()))}))
                    elif t == 'joined':
                        game_id = obj['game_id']; player_id = obj['player_id']
                        print('Joined', game_id, 'as', player_id)
                        asyncio.create_task(send_inputs(ws, game_id, player_id))
                    elif t == 'state':
                        gid = obj.get('game_id')
                        snap = obj.get('snapshot', {})
                        print(f"State {gid}: players={len(snap)}")

            async def send_inputs(ws, game_id, player_id):
                x = 0.0; y = 0.0; hp = 100; score = 0
                while True:
                    x += random.uniform(-5, 5)
                    y += random.uniform(-5, 5)
                    hp = max(0, hp - random.choice([0, 0, 0, 1]))
                    score += random.choice([0, 1])
                    inp = {'x': x, 'y': y, 'hp': hp, 'score': score}
                    try:
                        await ws.send_str(json.dumps({'type': 'input', 'game_id': game_id, 'player_id': player_id, 'input': inp}))
                    except Exception as e:
                        print('send_inputs: send_str failed', e)
                        return
                    await asyncio.sleep(0.1)

            await asyncio.gather(sender(), receiver())
    except Exception as e:
        print('net_client: connection error', repr(e))
    finally:
        await session.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python net_client.py ws://SERVER:PORT [proxy]')
        sys.exit(1)
    uri = sys.argv[1]
    proxy = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(interact(uri, proxy=proxy))
