"""
Background WebSocket-based network integration for `game_main.py`.

Provides `NetClient` which runs an asyncio websocket client in a
separate thread. It supports creating a game, joining it, sending
periodic input updates, and exposes the latest snapshot received from
the server at `client.latest_snapshot`.
"""
import threading
import asyncio
import json
import time
import threading
import asyncio
import json
import time
import queue
from typing import Optional
from collections import deque

import aiohttp


class NetClient:
    def __init__(self, uri='ws://localhost:8765', proxy: Optional[str] = None, max_retries: int = 5):
        self.uri = uri
        self.proxy = proxy
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.out_q = queue.Queue()
        self.latest_snapshot = {}
        self.game_id = None
        self.player_id = None
        self.connected = False
        # keep a short history of snapshots for interpolation
        self._history = deque(maxlen=32)
        self.max_retries = max_retries

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

    def send_input(self, game_id, player_id, inp: dict):
        self.out_q.put({'type': 'input', 'game_id': game_id, 'player_id': player_id, 'input': inp})

    # Lobby APIs
    def request_lobby(self):
        self.out_q.put({'type': 'list'})

    def create_game(self, name: str):
        self.out_q.put({'type': 'create', 'name': name})

    def join_game(self, game_id: str, player_name: str):
        self.out_q.put({'type': 'join', 'game_id': game_id, 'player_name': player_name})

    # latest lobby snapshot (list of games)
    latest_lobby = []
    latest_created = None
    latest_join = None

    async def _consumer(self, ws):
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    obj = json.loads(msg.data)
                except Exception:
                    continue
                t = obj.get('type')
                if t == 'lobby':
                    # store lobby list
                    self.latest_lobby = obj.get('games', [])
                elif t == 'created':
                    self.latest_created = obj.get('game_id')
                elif t == 'joined':
                    self.latest_join = {'game_id': obj.get('game_id'), 'player_id': obj.get('player_id')}
                    self.game_id = obj.get('game_id')
                    self.player_id = obj.get('player_id')
                    self.connected = True
                elif t == 'state':
                    snap = obj.get('snapshot', {})
                    ts = time.time()
                    self.latest_snapshot = snap
                    try:
                        self._history.append((ts, snap))
                    except Exception:
                        pass

    async def _producer(self, ws):
        # producer will send queued messages placed by API methods
        while not self.stop_event.is_set():
            try:
                try:
                    item = self.out_q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.05)
                    continue
                try:
                    await ws.send_str(json.dumps(item))
                except Exception:
                    # connection likely closing; stop producer
                    return
            except Exception:
                await asyncio.sleep(0.2)

    async def _main(self):
        session = aiohttp.ClientSession()
        try:
            async with session.ws_connect(self.uri, proxy=self.proxy) as ws:
                await ws.send_str(json.dumps({'type': 'list'}))
                consumer_task = asyncio.create_task(self._consumer(ws))
                producer_task = asyncio.create_task(self._producer(ws))
                done, pending = await asyncio.wait([consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
        except Exception:
            self.connected = False
        finally:
            await session.close()

    def _run(self):
        # try to connect up to max_retries times, then give up
        attempt = 0
        while not self.stop_event.is_set() and (self.max_retries <= 0 or attempt < self.max_retries):
            attempt += 1
            print(f"NetClient: connection attempt {attempt}/{self.max_retries if self.max_retries>0 else '∞'} to {self.uri}")
            try:
                asyncio.run(self._main())
                # if _main returns without exception, break out (clean shutdown)
                break
            except Exception as e:
                print(f"NetClient: connection attempt {attempt} failed: {e}")
                if attempt >= self.max_retries and self.max_retries > 0:
                    print(f"NetClient: reached max retries ({self.max_retries}), giving up")
                    break
                # wait a bit then retry (simple backoff)
                time.sleep(min(5, 0.5 * attempt))
                continue

    """
    Background WebSocket-based network integration for `game_main.py`.

    Provides `NetClient` which runs an asyncio websocket client in a
    separate thread. It supports creating a game, joining it, sending
    periodic input updates, and exposes the latest snapshot received from
    the server at `client.latest_snapshot`.
    """
    import threading
    import asyncio
    import json
    import time
    import queue
    from typing import Optional
    from collections import deque

    import aiohttp


    class NetClient:
        def __init__(self, uri='ws://localhost:8765', proxy: Optional[str] = None):
            self.uri = uri
            self.proxy = proxy
            self.thread: Optional[threading.Thread] = None
            self.stop_event = threading.Event()
            self.out_q = queue.Queue()
            self.latest_snapshot = {}
            self.game_id = None
            self.player_id = None
            self.connected = False
            # keep a short history of snapshots for interpolation
            self._history = deque(maxlen=32)

        def start(self):
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

        def stop(self):
            self.stop_event.set()
            if self.thread:
                self.thread.join(timeout=1.0)

        def send_input(self, game_id, player_id, inp: dict):
            self.out_q.put({'type': 'input', 'game_id': game_id, 'player_id': player_id, 'input': inp})

        async def _consumer(self, ws):
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        obj = json.loads(msg.data)
                    except Exception:
                        continue
                    t = obj.get('type')
                    if t == 'lobby':
                        pass
                    elif t == 'created':
                        self.game_id = obj.get('game_id')
                        await ws.send_str(json.dumps({'type': 'join', 'game_id': self.game_id, 'player_name': 'Player' + str(int(time.time()))}))
                    elif t == 'joined':
                        self.game_id = obj.get('game_id')
                        self.player_id = obj.get('player_id')
                        self.connected = True
                    elif t == 'state':
                        snap = obj.get('snapshot', {})
                        ts = time.time()
                        self.latest_snapshot = snap
                        try:
                            self._history.append((ts, snap))
                        except Exception:
                            pass

        async def _producer(self, ws):
            await ws.send_str(json.dumps({'type': 'create', 'name': 'PG_MowGrass_Room'}))
            while not self.stop_event.is_set():
                try:
                    try:
                        item = self.out_q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.05)
                        continue
                    await ws.send_str(json.dumps(item))
                except Exception:
                    await asyncio.sleep(0.2)

        async def _main(self):
            session = aiohttp.ClientSession()
            try:
                async with session.ws_connect(self.uri, proxy=self.proxy) as ws:
                    await ws.send_str(json.dumps({'type': 'list'}))
                    consumer_task = asyncio.create_task(self._consumer(ws))
                    producer_task = asyncio.create_task(self._producer(ws))
                    done, pending = await asyncio.wait([consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED)
                    for t in pending:
                        t.cancel()
            except Exception:
                self.connected = False
            finally:
                await session.close()

        def _run(self):
            try:
                asyncio.run(self._main())
            except Exception:
                pass

        def get_interpolated_snapshot(self, render_time: float = None):
            if render_time is None:
                render_time = time.time()
            if len(self._history) < 2:
                return self.latest_snapshot
            t1, s1 = self._history[-2]
            t2, s2 = self._history[-1]
            if t2 == t1:
                return s2
            alpha = (render_time - t1) / (t2 - t1)
            alpha = max(0.0, min(1.0, alpha))
            out = {}
            for pid in set(list(s1.keys()) + list(s2.keys())):
                p1 = s1.get(pid)
                p2 = s2.get(pid)
                if p1 and p2:
                    try:
                        x = p1.get('x', 0) * (1 - alpha) + p2.get('x', 0) * alpha
                        y = p1.get('y', 0) * (1 - alpha) + p2.get('y', 0) * alpha
                        hp = int(p2.get('hp', p1.get('hp', 100)))
                        out[pid] = dict(x=x, y=y, hp=hp, max_hp=p2.get('max_hp', p1.get('max_hp', 100)))
                    except Exception:
                        out[pid] = p2 or p1
                else:
                    out[pid] = p2 or p1
            return out
