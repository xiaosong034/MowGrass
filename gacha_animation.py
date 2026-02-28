"""
3D抽卡动画系统 — 伪3D透视投影引擎
========================================
使用透视投影将3D坐标映射到2D屏幕，模拟真实3D效果：
- 3D相机系统（位置、目标、FOV、景深）
- 3D粒子系统（球体发射、深度排序、近大远小）
- 多层3D魔法阵（透视椭圆、不同Z轴高度）
- 3D祭坛（三层旋转平台、发光符文柱）
- 体积光、镜头光晕、冲击波
- 星空背景（视差滚动）
- 品质分化视觉体系（common→legendary 5级渐进）

Phase 0 (0-2s):  镜头穿越星空→推进神殿
Phase 1 (2-4s):  能量汇聚、符文环旋转、环绕上升运镜
Phase 2 (4-6s):  光芒爆发、魔法阵层数按品质分化
Phase 3 (6-8s):  角色/装备显现、冲击波、残影
Phase 4 (8+s):   3D UI结果展示、环绕镜头
========================================
"""

import pygame
import math
import random
import i18n

# ---- 描边文字渲染 ----
def _render_outlined(font, text, color, outline_color=(0, 0, 0), offset=1):
    base = font.render(text, True, color)
    outline = font.render(text, True, outline_color)
    w, h = base.get_size()
    surf = pygame.Surface((w + offset * 2, h + offset * 2), pygame.SRCALPHA)
    for dx in (-offset, 0, offset):
        for dy in (-offset, 0, offset):
            if dx == 0 and dy == 0:
                continue
            surf.blit(outline, (offset + dx, offset + dy))
    surf.blit(base, (offset, offset))
    return surf

# ---- 模块级变量 ----
_screen = None
_font_lg = _font_md = _font_sm = _font_xs = None
WIDTH = HEIGHT = 0

RARITY_COLORS = {
    'common':    (180, 200, 220),
    'uncommon':  (100, 220, 100),
    'rare':      (80, 150, 255),
    'epic':      (180, 80, 255),
    'legendary': (255, 200, 50),
}
RARITY_GLOW = {
    'common':    (200, 220, 255),
    'uncommon':  (120, 255, 120),
    'rare':      (100, 180, 255),
    'epic':      (200, 100, 255),
    'legendary': (255, 220, 80),
}
RARITY_NAMES = {
    'common': '普通', 'uncommon': '优秀', 'rare': '稀有',
    'epic': '史诗', 'legendary': '传说',
}
RARITY_ORDER = ['common', 'uncommon', 'rare', 'epic', 'legendary']


def init(screen, font_lg, font_md, font_sm, font_xs, w, h):
    global _screen, _font_lg, _font_md, _font_sm, _font_xs, WIDTH, HEIGHT
    _screen = screen
    _font_lg = font_lg
    _font_md = font_md
    _font_sm = font_sm
    _font_xs = font_xs
    WIDTH = w
    HEIGHT = h


# ============================================================
#  3D 数学工具
# ============================================================
class Vec3:
    """轻量3D向量"""
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __add__(self, o):
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o):
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s):
        return Vec3(self.x * s, self.y * s, self.z * s)

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self):
        ln = self.length()
        if ln < 1e-9:
            return Vec3(0, 0, 1)
        return Vec3(self.x / ln, self.y / ln, self.z / ln)

    def dot(self, o):
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o):
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def lerp(self, o, t):
        t = max(0.0, min(1.0, t))
        return Vec3(
            self.x + (o.x - self.x) * t,
            self.y + (o.y - self.y) * t,
            self.z + (o.z - self.z) * t,
        )

    def copy(self):
        return Vec3(self.x, self.y, self.z)


def _ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_in_cubic(t):
    t = max(0.0, min(1.0, t))
    return t * t * t


def _ease_out_back(t):
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


# ============================================================
#  3D 相机系统
# ============================================================
class Camera3D:
    """透视投影3D相机"""

    def __init__(self):
        self.position = Vec3(0, 5, -18)
        self.target = Vec3(0, 0, 0)
        self.fov = 60.0
        self.near = 0.1
        self.far = 200.0
        # 震动
        self._shake_intensity = 0.0
        self._shake_timer = 0.0
        self._shake_offset = Vec3()
        # 运镜
        self._move_from_pos = None
        self._move_to_pos = None
        self._move_from_tgt = None
        self._move_to_tgt = None
        self._move_duration = 0.0
        self._move_timer = 0.0
        self._move_ease = _ease_in_out

    def move_to(self, pos, target, duration, ease=None):
        self._move_from_pos = self.position.copy()
        self._move_to_pos = pos.copy() if isinstance(pos, Vec3) else Vec3(*pos)
        self._move_from_tgt = self.target.copy()
        self._move_to_tgt = target.copy() if isinstance(target, Vec3) else Vec3(*target)
        self._move_duration = max(0.01, duration)
        self._move_timer = 0.0
        self._move_ease = ease or _ease_in_out

    def shake(self, intensity, duration):
        self._shake_intensity = intensity
        self._shake_timer = duration

    def update(self, dt):
        if self._move_from_pos is not None:
            self._move_timer += dt
            t = min(1.0, self._move_timer / self._move_duration)
            et = self._move_ease(t)
            self.position = self._move_from_pos.lerp(self._move_to_pos, et)
            self.target = self._move_from_tgt.lerp(self._move_to_tgt, et)
            if t >= 1.0:
                self._move_from_pos = None

        if self._shake_timer > 0:
            self._shake_timer -= dt
            decay = min(1.0, self._shake_timer * 5)
            self._shake_offset = Vec3(
                random.uniform(-1, 1) * self._shake_intensity * decay,
                random.uniform(-1, 1) * self._shake_intensity * decay,
                random.uniform(-0.3, 0.3) * self._shake_intensity * decay,
            )
        else:
            self._shake_offset = Vec3()

    def project(self, world_pos):
        """将3D世界坐标投影到2D屏幕坐标 → (sx, sy, depth, scale) | None"""
        cam_pos = self.position + self._shake_offset

        forward = (self.target - cam_pos).normalized()
        world_up = Vec3(0, 1, 0)
        right = forward.cross(world_up)
        if right.length() < 1e-6:
            right = Vec3(1, 0, 0)
        else:
            right = right.normalized()
        up = right.cross(forward).normalized()

        rel = world_pos - cam_pos
        cz = rel.dot(forward)
        if cz < self.near:
            return None
        cx = rel.dot(right)
        cy = -rel.dot(up)

        aspect = WIDTH / max(1, HEIGHT)
        fov_rad = math.radians(self.fov)
        f = 1.0 / math.tan(fov_rad / 2.0)

        sx = (cx * f / (cz * aspect)) * (WIDTH / 2) + WIDTH / 2
        sy = (cy * f / cz) * (HEIGHT / 2) + HEIGHT / 2
        scale = f / cz

        return (sx, sy, cz, scale)

    def get_effective_pos(self):
        return self.position + self._shake_offset


# ============================================================
#  3D 粒子系统
# ============================================================
class Particle3D:
    __slots__ = ('pos', 'vel', 'life', 'max_life', 'color', 'size', 'kind',
                 'trail', 'gravity')

    def __init__(self, pos, vel, life, color, size=3.0, kind='dot', gravity=0.0):
        self.pos = pos.copy() if isinstance(pos, Vec3) else Vec3(*pos)
        self.vel = vel.copy() if isinstance(vel, Vec3) else Vec3(*vel)
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.kind = kind
        self.trail = []
        self.gravity = gravity

    def update(self, dt):
        if self.kind == 'trail':
            self.trail.append(self.pos.copy())
            if len(self.trail) > 8:
                self.trail.pop(0)
        self.vel.y -= self.gravity * dt
        self.pos = self.pos + self.vel * dt
        self.life -= dt

    def draw(self, surface, camera):
        if self.life <= 0:
            return
        proj = camera.project(self.pos)
        if proj is None:
            return
        sx, sy, depth, scale = proj
        if sx < -100 or sx > WIDTH + 100 or sy < -100 or sy > HEIGHT + 100:
            return

        alpha_frac = max(0.0, self.life / self.max_life)
        alpha = int(255 * alpha_frac)
        r, g, b = self.color
        draw_size = max(1, int(self.size * scale * 80))

        if self.kind == 'dot':
            if draw_size > 0:
                ds = min(draw_size, 30)
                ps = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (r, g, b, alpha), (ds, ds), ds)
                surface.blit(ps, (int(sx - ds), int(sy - ds)))

        elif self.kind == 'spark':
            ds = min(draw_size, 25)
            if ds > 0:
                # 核心
                ps = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
                cr = min(255, r + 60)
                cg = min(255, g + 60)
                cb = min(255, b + 60)
                pygame.draw.circle(ps, (cr, cg, cb, alpha), (ds, ds), ds)
                surface.blit(ps, (int(sx - ds), int(sy - ds)))
                # 光晕
                gr = ds * 3
                if gr > 3 and gr < 150:
                    gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (r, g, b, max(1, alpha // 4)),
                                       (gr, gr), gr)
                    surface.blit(gs, (int(sx - gr), int(sy - gr)))

        elif self.kind == 'trail':
            for i, tp in enumerate(self.trail):
                tp_proj = camera.project(tp)
                if tp_proj is None:
                    continue
                tpx, tpy, _, tps = tp_proj
                trail_a = int(alpha * (i + 1) / (len(self.trail) + 1) * 0.5)
                ts = max(1, min(20, int(self.size * tps * 60)))
                tsurf = pygame.Surface((ts * 2, ts * 2), pygame.SRCALPHA)
                pygame.draw.circle(tsurf, (r, g, b, trail_a), (ts, ts), ts)
                surface.blit(tsurf, (int(tpx - ts), int(tpy - ts)))
            ds = min(draw_size, 25)
            if ds > 0:
                ps = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (min(255, r + 80), min(255, g + 80),
                                        min(255, b + 80), alpha),
                                   (ds, ds), ds)
                surface.blit(ps, (int(sx - ds), int(sy - ds)))

        elif self.kind == 'ring':
            ds = min(draw_size, 40)
            if ds > 2:
                ps = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (r, g, b, alpha), (ds, ds), ds,
                                   max(1, ds // 4))
                surface.blit(ps, (int(sx - ds), int(sy - ds)))


# ============================================================
#  3D 星空背景
# ============================================================
class Starfield:
    def __init__(self, count=300):
        self.stars = []
        for _ in range(count):
            self.stars.append({
                'pos': Vec3(
                    random.uniform(-80, 80),
                    random.uniform(-60, 60),
                    random.uniform(20, 120),
                ),
                'brightness': random.uniform(0.3, 1.0),
                'size': random.uniform(0.5, 2.0),
                'twinkle_phase': random.uniform(0, math.pi * 2),
            })
        self.nebula_blobs = []
        for _ in range(10):
            self.nebula_blobs.append({
                'pos': Vec3(
                    random.uniform(-50, 50),
                    random.uniform(-40, 40),
                    random.uniform(40, 100),
                ),
                'radius': random.uniform(8, 25),
                'color': random.choice([
                    (60, 30, 100), (30, 50, 100), (80, 20, 60),
                    (20, 60, 80), (50, 20, 80),
                ]),
                'alpha': random.uniform(8, 22),
            })

    def draw(self, surface, camera, t):
        for nb in self.nebula_blobs:
            proj = camera.project(nb['pos'])
            if proj is None:
                continue
            sx, sy, depth, scale = proj
            r = max(5, min(200, int(nb['radius'] * scale * 80)))
            if sx < -r or sx > WIDTH + r or sy < -r or sy > HEIGHT + r:
                continue
            a = int(nb['alpha'] * max(0.2, min(1.0, 30.0 / depth)))
            ns = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ns, (*nb['color'], min(255, a)), (r, r), r)
            r2 = r // 2
            if r2 > 2:
                pygame.draw.circle(ns, (*nb['color'], min(255, a // 2)),
                                   (r, r), r2)
            surface.blit(ns, (int(sx - r), int(sy - r)))

        for star in self.stars:
            proj = camera.project(star['pos'])
            if proj is None:
                continue
            sx, sy, depth, scale = proj
            if sx < -5 or sx > WIDTH + 5 or sy < -5 or sy > HEIGHT + 5:
                continue
            twinkle = (math.sin(t * 3 + star['twinkle_phase']) + 1) * 0.5
            brightness = star['brightness'] * (0.6 + twinkle * 0.4)
            alpha = min(255, int(255 * brightness * max(0.2, min(1.0, 20.0 / depth))))
            s = max(1, min(8, int(star['size'] * scale * 60)))
            if s <= 1:
                ix, iy = int(sx), int(sy)
                if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                    try:
                        surface.set_at((ix, iy), (200, 210, 240, alpha))
                    except Exception:
                        pass
            else:
                ps = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (220, 225, 255, alpha), (s, s), s)
                surface.blit(ps, (int(sx - s), int(sy - s)))


# ============================================================
#  3D 祭坛
# ============================================================
class Altar3D:
    def __init__(self):
        self.position = Vec3(0, 0, 0)
        self.platform_angles = [0.0, 0.0, 0.0]
        self.platform_speeds = [0.3, -0.2, 0.15]
        self.crystal_pulse = 0.0
        self.crystal_energy = 0.0

    def update(self, dt, total_t):
        for i in range(3):
            self.platform_angles[i] += self.platform_speeds[i] * dt
        self.crystal_pulse = (math.sin(total_t * 3) + 1) * 0.5

    def draw(self, surface, camera, t, color, energy=0.0):
        cx, cy, cz = self.position.x, self.position.y, self.position.z

        # 三层平台
        platform_params = [
            (2.5, -0.6, 0),
            (2.0, -0.3, 1),
            (1.5,  0.0, 2),
        ]
        for radius, y_off, ai in platform_params:
            self._draw_platform_ring(surface, camera,
                                     Vec3(cx, cy + y_off, cz),
                                     radius, self.platform_angles[ai],
                                     color, 16)

        # 四根符文柱
        pillar_positions = [
            Vec3(cx + 1.8, cy, cz + 1.8),
            Vec3(cx - 1.8, cy, cz + 1.8),
            Vec3(cx + 1.8, cy, cz - 1.8),
            Vec3(cx - 1.8, cy, cz - 1.8),
        ]
        for pp in pillar_positions:
            self._draw_pillar(surface, camera, t, pp, color, energy)

        # 水晶球
        crystal_y = cy + 2.0 + math.sin(t * 2) * 0.15
        crystal_pos = Vec3(cx, crystal_y, cz)
        proj = camera.project(crystal_pos)
        if proj:
            sx, sy, depth, scale = proj
            cr = max(4, min(50, int(1.2 * scale * 80)))

            # 外层光晕
            glow_r = int(cr * (1.5 + energy * 1.5 + self.crystal_pulse * 0.3))
            if glow_r > 3 and glow_r < 200:
                gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                ga = int(20 + energy * 60 + self.crystal_pulse * 20)
                pygame.draw.circle(gs, (*color, min(255, ga)),
                                   (glow_r, glow_r), glow_r)
                surface.blit(gs, (int(sx - glow_r), int(sy - glow_r)))

            # 球体
            ball_r = min(255, 40 + int(color[0] * 0.3 * energy))
            ball_g = min(255, 30 + int(color[1] * 0.3 * energy))
            ball_b = min(255, 60 + int(color[2] * 0.3 * energy))
            pygame.draw.circle(surface, (ball_r, ball_g, ball_b),
                               (int(sx), int(sy)), cr)
            pygame.draw.circle(surface, color, (int(sx), int(sy)),
                               cr, max(1, cr // 8))

            # 高光
            hl_r = max(2, cr // 3)
            hl_x = int(sx - cr * 0.25)
            hl_y = int(sy - cr * 0.25)
            hls = pygame.Surface((hl_r * 2, hl_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(hls, (255, 255, 255, int(100 + energy * 80)),
                               (hl_r, hl_r), hl_r)
            surface.blit(hls, (hl_x - hl_r, hl_y - hl_r))

            # 内部能量
            if energy > 0.1:
                for ei in range(3):
                    ea = t * (3 + ei) + ei * 2.1
                    er = cr * 0.5 * energy
                    epx = int(sx + math.cos(ea) * er)
                    epy = int(sy + math.sin(ea) * er)
                    es = max(2, int(cr * 0.15))
                    eps = pygame.Surface((es * 2, es * 2), pygame.SRCALPHA)
                    pygame.draw.circle(eps, (*color, int(120 * energy)),
                                       (es, es), es)
                    surface.blit(eps, (epx - es, epy - es))

    def _draw_platform_ring(self, surface, camera, center, radius, angle,
                            color, segments):
        points_2d = []
        for i in range(segments):
            a = angle + 2 * math.pi * i / segments
            wp = Vec3(center.x + math.cos(a) * radius,
                      center.y,
                      center.z + math.sin(a) * radius)
            proj = camera.project(wp)
            if proj:
                points_2d.append((int(proj[0]), int(proj[1]), proj[2]))

        if len(points_2d) >= 3:
            poly = [(p[0], p[1]) for p in points_2d]
            ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(ps, (*color, 15), poly)
            pygame.draw.polygon(ps, (*color, 60), poly, 1)
            surface.blit(ps, (0, 0))

            for i, (px, py, pd) in enumerate(points_2d):
                if i % 4 == 0:
                    ds = max(1, min(10, int(0.15 / max(0.5, pd / 10) * 10)))
                    dp = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
                    pygame.draw.circle(dp, (*color, 140), (ds, ds), ds)
                    surface.blit(dp, (px - ds, py - ds))

    def _draw_pillar(self, surface, camera, t, pos, color, energy):
        base_pos = pos
        top_pos = Vec3(pos.x, pos.y + 2.5, pos.z)
        p_base = camera.project(base_pos)
        p_top = camera.project(top_pos)
        if p_base is None or p_top is None:
            return

        bx, by = int(p_base[0]), int(p_base[1])
        tx, ty = int(p_top[0]), int(p_top[1])
        tb = max(2, min(12, int(0.12 * p_base[3] * 80)))
        tt = max(2, min(10, int(0.1 * p_top[3] * 80)))

        pts = [(bx - tb, by), (bx + tb, by), (tx + tt, ty), (tx - tt, ty)]
        ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(ps, (50, 45, 65, 180), pts)
        pygame.draw.polygon(ps, (*color, 60), pts, 1)
        surface.blit(ps, (0, 0))

        if energy > 0.05:
            for ri in range(3):
                rune_t = (t * 0.8 + ri / 3.0) % 1.0
                ry = by + (ty - by) * rune_t
                rx = bx + (tx - bx) * rune_t
                rune_s = max(2, int(tb * (0.5 + energy * 0.5)))
                ra = int(120 * energy * (1.0 - abs(rune_t - 0.5) * 2))
                rs = pygame.Surface((rune_s * 2, rune_s * 2), pygame.SRCALPHA)
                pygame.draw.circle(rs, (*color, min(255, ra)),
                                   (rune_s, rune_s), rune_s)
                surface.blit(rs, (int(rx - rune_s), int(ry - rune_s)))


# ============================================================
#  3D 魔法阵
# ============================================================
class MagicCircle3D:
    def __init__(self, ring_count, color, glow_color):
        self.rings = []
        self.color = color
        self.glow_color = glow_color
        for i in range(ring_count):
            self.rings.append({
                'radius': 2.5 + i * 1.2,
                'y_offset': -0.5 + i * 0.8,
                'angle': random.uniform(0, math.pi * 2),
                'speed': (0.8 + i * 0.3) * (1 if i % 2 == 0 else -1),
                'segments': 6 + i * 2,
                'alpha': 200 - i * 25,
                'inner_ratio': 0.55 + i * 0.05,
            })
        self.expand = 0.0

    def update(self, dt, expand_target=1.0):
        for ring in self.rings:
            ring['angle'] += ring['speed'] * dt
        self.expand += (expand_target - self.expand) * dt * 3

    def draw(self, surface, camera, center, t):
        if self.expand < 0.01:
            return

        for ri, ring in enumerate(self.rings):
            r = ring['radius'] * self.expand
            y = center.y + ring['y_offset'] * self.expand
            angle = ring['angle']
            segments = ring['segments']
            alpha = int(ring['alpha'] * min(1.0, self.expand))
            inner_r = r * ring['inner_ratio']

            outer_pts = []
            inner_pts = []
            for i in range(segments):
                a = angle + 2 * math.pi * i / segments
                wp = Vec3(center.x + math.cos(a) * r, y,
                          center.z + math.sin(a) * r)
                proj = camera.project(wp)
                if proj:
                    outer_pts.append((int(proj[0]), int(proj[1]), proj[2]))

                a2 = -angle * 0.7 + 2 * math.pi * i / segments
                wp2 = Vec3(center.x + math.cos(a2) * inner_r, y,
                           center.z + math.sin(a2) * inner_r)
                proj2 = camera.project(wp2)
                if proj2:
                    inner_pts.append((int(proj2[0]), int(proj2[1]), proj2[2]))

            if len(outer_pts) >= 3:
                poly = [(p[0], p[1]) for p in outer_pts]
                col = self.color if ri % 2 == 0 else self.glow_color
                ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(ps, (*col, max(1, alpha // 5)), poly)
                pygame.draw.polygon(ps, (*col, min(255, alpha)), poly, 1)
                surface.blit(ps, (0, 0))

                center_proj = camera.project(Vec3(center.x, y, center.z))
                if center_proj:
                    cpx, cpy = int(center_proj[0]), int(center_proj[1])
                    for px, py, pd in outer_pts:
                        la = max(1, min(255, alpha // 3))
                        ps2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        pygame.draw.line(ps2, (*col, la),
                                         (cpx, cpy), (px, py), 1)
                        surface.blit(ps2, (0, 0))

                for px, py, pd in outer_pts:
                    ds = max(2, min(12, int(0.1 * 80 / max(1.0, pd / 5))))
                    dsurf = pygame.Surface((ds * 2, ds * 2), pygame.SRCALPHA)
                    pygame.draw.circle(dsurf, (*col, min(255, alpha)),
                                       (ds, ds), ds)
                    surface.blit(dsurf, (px - ds, py - ds))

            if len(inner_pts) >= 3:
                poly2 = [(p[0], p[1]) for p in inner_pts]
                col2 = self.glow_color if ri % 2 == 0 else self.color
                ps3 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(ps3, (*col2, max(1, min(255, alpha // 3))),
                                    poly2, 1)
                surface.blit(ps3, (0, 0))


# ============================================================
#  体积光柱
# ============================================================
class LightBeam3D:
    def __init__(self):
        self.intensity = 0.0
        self.target_intensity = 0.0
        self.color = (200, 200, 255)
        self.width = 1.0
        self.height = 20.0

    def update(self, dt):
        self.intensity += (self.target_intensity - self.intensity) * dt * 4

    def draw(self, surface, camera, base_pos, t):
        if self.intensity < 0.01:
            return

        layers = 10
        for i in range(layers):
            frac = i / layers
            y = base_pos.y + 2.0 + frac * self.height * self.intensity
            w = self.width * (1.0 - frac * 0.3) * self.intensity

            pts_3d = [
                Vec3(base_pos.x - w, y, base_pos.z),
                Vec3(base_pos.x + w, y, base_pos.z),
                Vec3(base_pos.x + w, y + self.height / layers, base_pos.z),
                Vec3(base_pos.x - w, y + self.height / layers, base_pos.z),
            ]
            pts_2d = []
            for p in pts_3d:
                proj = camera.project(p)
                if proj:
                    pts_2d.append((int(proj[0]), int(proj[1])))
            if len(pts_2d) >= 3:
                a = int(50 * self.intensity * (1.0 - frac * 0.5))
                ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(ps, (*self.color, min(255, a)), pts_2d)
                surface.blit(ps, (0, 0))

        # 中心亮线
        bp = camera.project(Vec3(base_pos.x, base_pos.y + 2.0, base_pos.z))
        tp = camera.project(Vec3(base_pos.x,
                                 base_pos.y + 2.0 + self.height * self.intensity,
                                 base_pos.z))
        if bp and tp:
            a = min(255, int(180 * self.intensity))
            lw = max(1, int(3 * self.intensity))
            ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(ps, (*self.color, a),
                             (int(bp[0]), int(bp[1])),
                             (int(tp[0]), int(tp[1])), lw)
            surface.blit(ps, (0, 0))

        # 符文上升
        if self.intensity > 0.3:
            for ri in range(int(5 * self.intensity)):
                rf = ((t * 0.3 + ri / 5.0) % 1.0)
                ry = base_pos.y + 2.0 + rf * self.height * self.intensity * 0.8
                ra = t * 3 + ri * 1.2
                rx = base_pos.x + math.cos(ra) * self.width * 0.5 * self.intensity
                rz = base_pos.z + math.sin(ra) * self.width * 0.5 * self.intensity
                proj = camera.project(Vec3(rx, ry, rz))
                if proj:
                    rsx, rsy = int(proj[0]), int(proj[1])
                    rs = max(2, min(12, int(0.1 * proj[3] * 80)))
                    ra_alpha = int(80 * self.intensity * (1 - rf))
                    rsf = pygame.Surface((rs * 2, rs * 2), pygame.SRCALPHA)
                    pygame.draw.rect(rsf, (*self.color, min(255, ra_alpha)),
                                     (rs // 2, rs // 2, rs, rs), 1)
                    pygame.draw.line(rsf, (*self.color, min(255, ra_alpha)),
                                     (rs, 0), (rs, rs * 2), 1)
                    pygame.draw.line(rsf, (*self.color, min(255, ra_alpha)),
                                     (0, rs), (rs * 2, rs), 1)
                    surface.blit(rsf, (rsx - rs, rsy - rs))


# ============================================================
#  冲击波
# ============================================================
class Shockwave3D:
    def __init__(self, center, color, max_radius=8.0, duration=1.0):
        self.center = center.copy()
        self.color = color
        self.max_radius = max_radius
        self.duration = duration
        self.timer = 0.0
        self.active = True

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.duration:
            self.active = False

    def draw(self, surface, camera, t):
        if not self.active or self.timer < 0:
            return
        frac = max(0, self.timer) / self.duration
        radius = self.max_radius * _ease_out_cubic(frac)
        alpha = int(200 * (1.0 - frac))

        segments = 24
        pts = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            wp = Vec3(self.center.x + math.cos(a) * radius,
                      self.center.y,
                      self.center.z + math.sin(a) * radius)
            proj = camera.project(wp)
            if proj:
                pts.append((int(proj[0]), int(proj[1])))

        if len(pts) >= 3:
            ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(ps, (*self.color, max(1, alpha // 5)), pts)
            pygame.draw.polygon(ps, (*self.color, max(1, min(255, alpha))),
                                pts, max(1, int(3 * (1 - frac))))
            surface.blit(ps, (0, 0))


# ============================================================
#  浮动光球
# ============================================================
class OrbitalOrb:
    def __init__(self, center, radius, speed, y_offset, color, phase=0):
        self.center = center
        self.radius = radius
        self.speed = speed
        self.y_offset = y_offset
        self.color = color
        self.phase = phase
        self.size = 0.15

    def draw(self, surface, camera, t):
        a = t * self.speed + self.phase
        pos = Vec3(
            self.center.x + math.cos(a) * self.radius,
            self.center.y + self.y_offset + math.sin(t * 2 + self.phase) * 0.3,
            self.center.z + math.sin(a) * self.radius,
        )
        proj = camera.project(pos)
        if proj is None:
            return
        sx, sy, depth, scale = proj
        s = max(2, min(15, int(self.size * scale * 80)))

        gr = s * 3
        if gr > 3 and gr < 120:
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*self.color, 30), (gr, gr), gr)
            surface.blit(gs, (int(sx - gr), int(sy - gr)))
        ps = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*self.color, 220), (s, s), s)
        surface.blit(ps, (int(sx - s), int(sy - s)))


# ============================================================
#  五角星工具
# ============================================================
def _star_points(cx, cy, outer_r, inner_r, points=5):
    result = []
    for i in range(points * 2):
        angle = math.pi / 2 + math.pi * i / points
        r = outer_r if i % 2 == 0 else inner_r
        result.append((int(cx + r * math.cos(angle)),
                        int(cy - r * math.sin(angle))))
    return result


# ============================================================
#  主动画控制器
# ============================================================
class GachaAnimation:
    """3D抽卡动画 — 保持与game_main.py相同的API接口"""

    def __init__(self, results, equipment_db):
        self.results = results
        self.equipment_db = equipment_db
        self.phase = 0
        self.phase_timer = 0.0
        self.total_timer = 0.0
        self.finished = False
        self.skip_requested = False

        # 最高品质
        self.best_rarity = 'common'
        for _, rarity in results:
            if RARITY_ORDER.index(rarity) > RARITY_ORDER.index(self.best_rarity):
                self.best_rarity = rarity
        self.rarity_index = RARITY_ORDER.index(self.best_rarity)

        self.color = RARITY_COLORS.get(self.best_rarity, (200, 200, 200))
        self.glow_color = RARITY_GLOW.get(self.best_rarity, (220, 220, 255))

        # 品质决定时长
        if self.rarity_index >= 4:
            self.phase_durations = [2.0, 2.5, 2.5, 2.5, 999.0]
        elif self.rarity_index >= 3:
            self.phase_durations = [2.0, 2.0, 2.0, 2.0, 999.0]
        else:
            self.phase_durations = [1.5, 1.5, 1.5, 2.0, 999.0]

        # 3D场景
        self.camera = Camera3D()
        self.camera.position = Vec3(0, 12, -45)
        self.camera.target = Vec3(0, 2, 0)

        self.starfield = Starfield(350)
        self.altar = Altar3D()
        self.particles = []

        # 魔法阵层数
        ring_counts = [1, 2, 2, 3, 5]
        mc_count = ring_counts[min(self.rarity_index, 4)]
        self.magic_circle = MagicCircle3D(mc_count, self.color, self.glow_color)

        self.light_beam = LightBeam3D()
        self.light_beam.color = self.color

        self.shockwaves = []
        self.orbs = []
        self.flash_alpha = 0.0

        # 光球数量
        orb_counts = [0, 0, 4, 12, 24]
        self.orb_count = orb_counts[min(self.rarity_index, 4)]

        # 传说星座
        self.constellation_lines = []
        if self.rarity_index >= 4:
            self._gen_constellation()

        # 时间冻结
        self.time_freeze = 0.0

        # 阶段局部状态
        self._phase2_burst_done = False
        self._draw_constellation_flag = False

        # Phase 0 相机
        self.camera.move_to(
            Vec3(0, 4, -12), Vec3(0, 1.5, 0),
            duration=2.0, ease=_ease_in_out
        )

    def _gen_constellation(self):
        pts = [Vec3(random.uniform(-4, 4), random.uniform(6, 14),
                     random.uniform(-3, 3)) for _ in range(8)]
        used = set()
        for i in range(len(pts)):
            j = random.randint(0, len(pts) - 1)
            if i != j and (i, j) not in used and (j, i) not in used:
                self.constellation_lines.append((pts[i], pts[j]))
                used.add((i, j))
        for i in range(len(pts) - 1):
            if (i, i + 1) not in used:
                self.constellation_lines.append((pts[i], pts[i + 1]))

    def skip(self):
        self.skip_requested = True
        self.phase = 4
        self.phase_timer = 0
        self.particles.clear()
        self.shockwaves.clear()
        self.orbs.clear()
        self.magic_circle.expand = 0
        self.light_beam.intensity = 0
        self.light_beam.target_intensity = 0
        self.flash_alpha = 0
        self.camera.position = Vec3(0, 3, -10)
        self.camera.target = Vec3(0, 1.5, 0)
        self.camera._move_from_pos = None

    def update(self, dt):
        if self.finished:
            return

        # 时间冻结
        if self.time_freeze > 0:
            self.time_freeze -= dt
            self.camera.update(dt)
            if self.flash_alpha > 0:
                self.flash_alpha = max(0, self.flash_alpha - dt * 300)
            return

        self.total_timer += dt
        self.phase_timer += dt

        # 阶段推进
        if self.phase < 4 and self.phase_timer >= self.phase_durations[self.phase]:
            self.phase_timer -= self.phase_durations[self.phase]
            self.phase += 1
            self._on_phase_enter(self.phase)

        self.camera.update(dt)
        self.altar.update(dt, self.total_timer)
        self.magic_circle.update(dt)
        self.light_beam.update(dt)

        for sw in self.shockwaves:
            sw.update(dt)
        self.shockwaves = [sw for sw in self.shockwaves if sw.active]

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - dt * 300)

        self._update_phase(dt)

    def _on_phase_enter(self, phase):
        if phase == 1:
            self.camera.move_to(
                Vec3(8, 6, -8), Vec3(0, 2, 0),
                duration=self.phase_durations[1], ease=_ease_in_out
            )
        elif phase == 2:
            self.camera.move_to(
                Vec3(0, 3, -4), Vec3(0, 2, 0),
                duration=0.4, ease=_ease_in_cubic
            )
            self.light_beam.target_intensity = 0.5 + self.rarity_index * 0.2
            self.light_beam.width = 0.5 + self.rarity_index * 0.3
            self._phase2_burst_done = False
            if self.rarity_index >= 4:
                self.time_freeze = 0.3
        elif phase == 3:
            self.camera.move_to(
                Vec3(0, 3.5, -9), Vec3(0, 2, 0),
                duration=1.5, ease=_ease_out_cubic
            )
            self.flash_alpha = 255
            self.camera.shake(0.8 + self.rarity_index * 0.4, 0.5)

            for i in range(1 + self.rarity_index):
                sw = Shockwave3D(
                    Vec3(0, 0.5, 0), self.glow_color,
                    max_radius=5.0 + i * 2 + self.rarity_index,
                    duration=0.8 + i * 0.3
                )
                sw.timer = -i * 0.15
                self.shockwaves.append(sw)

            for i in range(self.orb_count):
                orb = OrbitalOrb(
                    center=Vec3(0, 2, 0),
                    radius=3.0 + random.uniform(-0.5, 0.5),
                    speed=0.8 + random.uniform(-0.2, 0.2),
                    y_offset=random.uniform(-1, 3),
                    color=self.glow_color,
                    phase=2 * math.pi * i / max(1, self.orb_count),
                )
                self.orbs.append(orb)

            self.light_beam.target_intensity = 0.2
        elif phase == 4:
            self.camera.position = Vec3(0, 3, -10)
            self.camera.target = Vec3(0, 1.5, 0)
            self.light_beam.target_intensity = 0
            self.magic_circle.expand = 0
            self.orbs.clear()

    def _update_phase(self, dt):
        t = self.total_timer

        if self.phase == 0:
            # 星尘飘过
            if random.random() < 0.35:
                cam = self.camera.get_effective_pos()
                offset = Vec3(random.uniform(-8, 8), random.uniform(-5, 5),
                              random.uniform(-3, 3))
                self.particles.append(Particle3D(
                    cam + offset,
                    Vec3(random.uniform(-1, 1), random.uniform(0.5, 2),
                         random.uniform(-1, 1)),
                    random.uniform(1.0, 2.5), self.glow_color,
                    random.uniform(0.03, 0.08), 'dot'
                ))
            energy = min(1.0, self.phase_timer / self.phase_durations[0])
            self.altar.crystal_energy = energy * 0.3

        elif self.phase == 1:
            # 环绕运镜
            frac = self.phase_timer / self.phase_durations[1]
            orbit_angle = frac * math.pi * 1.2
            orbit_r = 10 - frac * 2
            orbit_y = 5 + frac * 2
            target_pos = Vec3(math.sin(orbit_angle) * orbit_r, orbit_y,
                              -math.cos(orbit_angle) * orbit_r)
            self.camera.position = self.camera.position.lerp(target_pos, dt * 2)
            self.camera.target = Vec3(0, 1.5, 0)

            # 汇聚粒子
            spawn_count = 2 + self.rarity_index * 2
            for _ in range(spawn_count):
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(8, 18)
                start = Vec3(math.cos(angle) * dist, 3 + random.uniform(-2, 3),
                             math.sin(angle) * dist)
                diff = Vec3(0, 2.0, 0) - start
                vel = diff.normalized() * random.uniform(3, 7)
                self.particles.append(Particle3D(
                    start, vel, random.uniform(1.0, 2.5), self.color,
                    random.uniform(0.04, 0.1), 'trail'
                ))

            energy = min(1.0, self.phase_timer / self.phase_durations[1])
            self.altar.crystal_energy = 0.3 + energy * 0.7
            self.magic_circle.update(dt, expand_target=energy * 0.3)

        elif self.phase == 2:
            frac = self.phase_timer / self.phase_durations[2]

            if frac > 0.15 and not self._phase2_burst_done:
                self._phase2_burst_done = True
                self.flash_alpha = min(255, 200 + self.rarity_index * 15)
                self.camera.shake(1.0 + self.rarity_index * 0.5, 0.6)
                self.camera.move_to(
                    Vec3(0, 5, -16), Vec3(0, 1, 0),
                    duration=1.5, ease=_ease_out_cubic
                )
                for _ in range(30 + self.rarity_index * 20):
                    angle = random.uniform(0, math.pi * 2)
                    elev = random.uniform(-math.pi / 3, math.pi / 3)
                    spd = random.uniform(3, 12)
                    vel = Vec3(
                        math.cos(angle) * math.cos(elev) * spd,
                        math.sin(elev) * spd + 2,
                        math.sin(angle) * math.cos(elev) * spd
                    )
                    self.particles.append(Particle3D(
                        Vec3(0, 2, 0), vel,
                        random.uniform(0.8, 2.0), self.glow_color,
                        random.uniform(0.05, 0.15), 'spark'
                    ))

            self.magic_circle.update(dt, expand_target=1.0)

            if frac > 0.2:
                self.light_beam.target_intensity = 0.8 + self.rarity_index * 0.15

            self._draw_constellation_flag = (self.rarity_index >= 4 and frac > 0.4)

            if self.rarity_index >= 4:
                rainbow = [(255, 80, 80), (255, 200, 50), (80, 255, 80),
                           (80, 200, 255), (200, 80, 255)]
                idx = int(t * 2) % len(rainbow)
                self.magic_circle.color = rainbow[idx]
                self.magic_circle.glow_color = rainbow[(idx + 1) % len(rainbow)]

        elif self.phase == 3:
            frac = self.phase_timer / self.phase_durations[3]
            orbit_angle = frac * math.pi * 0.5
            self.camera.position = Vec3(
                math.sin(orbit_angle) * 9,
                3.5 - frac * 0.5,
                -math.cos(orbit_angle) * 9
            )
            self.camera.target = Vec3(0, 2, 0)

            if random.random() < 0.3:
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(1, 4)
                self.particles.append(Particle3D(
                    Vec3(math.cos(angle) * dist, random.uniform(0, 4),
                         math.sin(angle) * dist),
                    Vec3(0, random.uniform(0.5, 1.5), 0),
                    random.uniform(1, 2.5), self.glow_color,
                    random.uniform(0.02, 0.06), 'dot'
                ))

        elif self.phase == 4:
            orbit_angle = self.phase_timer * 0.15
            self.camera.position = Vec3(
                math.sin(orbit_angle) * 10,
                3.0 + math.sin(self.total_timer * 0.3) * 0.3,
                -math.cos(orbit_angle) * 10
            )
            self.camera.target = Vec3(0, 1.5, 0)

            if random.random() < 0.12:
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(3, 8)
                self.particles.append(Particle3D(
                    Vec3(math.cos(angle) * dist, random.uniform(-1, 0),
                         math.sin(angle) * dist),
                    Vec3(0, random.uniform(0.3, 1.0), 0),
                    random.uniform(2, 4), self.glow_color,
                    random.uniform(0.02, 0.05), 'dot'
                ))

    def draw(self, surface):
        if self.finished:
            return {}
        buttons = {}
        t = self.total_timer

        # 背景
        surface.fill((4, 3, 10))
        self.starfield.draw(surface, self.camera, t)

        # 场景元素
        if self.phase <= 3:
            self.altar.draw(surface, self.camera, t, self.color,
                            self.altar.crystal_energy)
            self.magic_circle.draw(surface, self.camera, Vec3(0, 0, 0), t)
            self.light_beam.draw(surface, self.camera, Vec3(0, 0, 0), t)

            for sw in self.shockwaves:
                sw.draw(surface, self.camera, t)
            for orb in self.orbs:
                orb.draw(surface, self.camera, t)

            if self.phase == 2 and self._draw_constellation_flag:
                self._draw_constellation(surface, t)

        # 深度排序粒子
        visible = []
        for p in self.particles:
            proj = self.camera.project(p.pos)
            if proj:
                visible.append((proj[2], p))
        visible.sort(key=lambda x: -x[0])
        for _, p in visible:
            p.draw(surface, self.camera)

        # Phase 2 品质文字
        if self.phase == 2:
            frac = self.phase_timer / self.phase_durations[2]
            if frac > 0.4:
                rn = i18n.rarity_name(self.best_rarity)
                star_str = '★' * (self.rarity_index + 1)
                txt_font = _font_lg if self.rarity_index >= 3 else _font_md
                txt = _render_outlined(txt_font, f"{star_str} {rn} {star_str}",
                                       self.glow_color)
                txt_a = int(min(255, (frac - 0.4) * 600))
                ts = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
                ts.blit(txt, (0, 0))
                ts.set_alpha(txt_a)
                scale_f = 1.0 + max(0, (0.6 - frac)) * 2
                if scale_f > 1.01:
                    tw = max(1, int(txt.get_width() * scale_f))
                    th = max(1, int(txt.get_height() * scale_f))
                    ts = pygame.transform.smoothscale(ts, (tw, th))
                surface.blit(ts, (WIDTH // 2 - ts.get_width() // 2,
                                  HEIGHT // 5 - ts.get_height() // 2))

        # Phase 3 显现
        if self.phase == 3:
            self._draw_reveal(surface, t)

        # Phase 4 结果
        if self.phase == 4:
            self._draw_final_results(surface, buttons, t)

        # 闪白
        if self.flash_alpha > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fc = self.glow_color if self.rarity_index >= 3 else (255, 255, 255)
            flash.fill((*fc, int(min(255, self.flash_alpha))))
            surface.blit(flash, (0, 0))

        # 跳过提示
        if self.phase < 4:
            skip_txt = _render_outlined(_font_xs, i18n.t("点击任意处跳过"), (100, 100, 120))
            surface.blit(skip_txt, (WIDTH - skip_txt.get_width() - 20,
                                    HEIGHT - 30))

        # 暗角
        if self.phase <= 2:
            self._draw_vignette(surface)

        return buttons

    def _draw_constellation(self, surface, t):
        for p1, p2 in self.constellation_lines:
            pr1 = self.camera.project(p1)
            pr2 = self.camera.project(p2)
            if pr1 and pr2:
                a = int(60 + math.sin(t * 2) * 30)
                ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(ps, (*self.glow_color, min(255, a)),
                                 (int(pr1[0]), int(pr1[1])),
                                 (int(pr2[0]), int(pr2[1])), 1)
                surface.blit(ps, (0, 0))
                for pr in (pr1, pr2):
                    s = max(2, min(10, int(0.08 * pr[3] * 80)))
                    psurf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
                    pygame.draw.circle(psurf, (*self.glow_color,
                                                min(255, a + 40)),
                                       (s, s), s)
                    surface.blit(psurf, (int(pr[0] - s), int(pr[1] - s)))

    def _draw_vignette(self, surface):
        edge_alpha = 40
        border = 100
        v = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for side in range(4):
            if side == 0:
                r = pygame.Rect(0, 0, WIDTH, border)
            elif side == 1:
                r = pygame.Rect(0, HEIGHT - border, WIDTH, border)
            elif side == 2:
                r = pygame.Rect(0, 0, border, HEIGHT)
            else:
                r = pygame.Rect(WIDTH - border, 0, border, HEIGHT)
            es = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            es.fill((0, 0, 0, edge_alpha))
            v.blit(es, r)
        surface.blit(v, (0, 0))

    def _draw_reveal(self, surface, t):
        frac = self.phase_timer / self.phase_durations[3]
        if not self.results:
            return

        if len(self.results) == 1:
            tidx, rarity = self.results[0]
            tpl = self.equipment_db[tidx]
            rc = RARITY_COLORS.get(rarity, (200, 200, 200))
            gc = RARITY_GLOW.get(rarity, (220, 220, 255))
            ri = RARITY_ORDER.index(rarity)

            reveal_pos = Vec3(0, 2.5, 0)

            # 品质登场差异
            if ri <= 1:
                drop_t = min(1.0, frac * 3)
                actual_y = 2.5 + (1 - _ease_out_cubic(drop_t)) * 5
                reveal_pos = Vec3(0, actual_y, 0)
            elif ri >= 3 and frac < 0.5:
                for gi, go in enumerate([(-2, 0), (2, 0), (0, -2)]):
                    gp3 = Vec3(go[0], 2.5, go[1])
                    gp = self.camera.project(gp3)
                    if gp:
                        ga = int(80 * (1 - frac * 2))
                        self._draw_equip_icon(surface, gp[0], gp[1],
                                              gp[3], tpl, rc, gc, ga)

            if ri >= 4 and frac > 0.3 and frac < 0.6:
                crack_a = int(200 * (1 - abs(frac - 0.45) * 6))
                proj = self.camera.project(reveal_pos)
                if proj:
                    for ci in range(6):
                        ca = random.uniform(0, math.pi * 2)
                        cl = random.uniform(30, 80)
                        cx_c = int(proj[0] + math.cos(ca) * random.uniform(10, 40))
                        cy_c = int(proj[1] + math.sin(ca) * random.uniform(10, 40))
                        ex = int(cx_c + math.cos(ca) * cl)
                        ey = int(cy_c + math.sin(ca) * cl)
                        ps = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        pygame.draw.line(ps, (*gc, min(255, max(1, crack_a))),
                                         (cx_c, cy_c), (ex, ey), 2)
                        surface.blit(ps, (0, 0))

            proj = self.camera.project(reveal_pos)
            if proj:
                appear_a = int(min(255, frac * 400))
                if ri <= 1:
                    appear_a = int(min(255, _ease_out_cubic(min(1, frac * 3)) * 255))
                self._draw_equip_icon(surface, proj[0], proj[1], proj[3],
                                       tpl, rc, gc, appear_a)

                if frac > 0.5:
                    name_a = int(min(255, (frac - 0.5) * 500))
                    slot_names = {s: i18n.slot_name(s) for s in ['weapon', 'armor', 'accessory', 'rune']}
                    nt = _render_outlined(_font_md, tpl[0], rc)
                    ns = pygame.Surface(nt.get_size(), pygame.SRCALPHA)
                    ns.blit(nt, (0, 0))
                    ns.set_alpha(name_a)
                    surface.blit(ns, (WIDTH // 2 - nt.get_width() // 2,
                                      int(proj[1]) + 60))

                    rn = i18n.rarity_name(rarity)
                    sn = slot_names.get(tpl[1], '')
                    it = _render_outlined(_font_sm, f"{rn} · {sn}", gc)
                    inf = pygame.Surface(it.get_size(), pygame.SRCALPHA)
                    inf.blit(it, (0, 0))
                    inf.set_alpha(name_a)
                    surface.blit(inf, (WIDTH // 2 - it.get_width() // 2,
                                       int(proj[1]) + 95))

    def _draw_equip_icon(self, surface, sx, sy, scale, tpl, color,
                          glow_color, alpha=255):
        size = max(20, min(80, int(1.5 * scale * 80)))

        if alpha > 30:
            gr = int(size * 1.5)
            if gr > 3 and gr < 200:
                gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*glow_color, max(1, alpha // 5)),
                                   (gr, gr), gr)
                surface.blit(gs, (int(sx - gr), int(sy - gr)))

        icon_s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.rect(icon_s, (15, 12, 25, min(255, int(alpha * 0.8))),
                         (0, 0, size * 2, size * 2), border_radius=8)
        pygame.draw.rect(icon_s, (*color, min(255, alpha)),
                         (0, 0, size * 2, size * 2), 3, border_radius=8)

        slot = tpl[1]
        cx_i, cy_i = size, size
        ir = size // 2

        if slot == 'weapon':
            pts = [(cx_i, cy_i - ir), (cx_i + ir // 3, cy_i),
                   (cx_i, cy_i + ir), (cx_i - ir // 3, cy_i)]
            pygame.draw.polygon(icon_s, (*color, min(255, alpha)), pts)
            pygame.draw.line(icon_s, (*glow_color, min(255, alpha)),
                             (cx_i - ir // 2, cy_i + ir // 2),
                             (cx_i + ir // 2, cy_i + ir // 2), 2)
        elif slot == 'armor':
            pygame.draw.circle(icon_s, (*color, min(255, alpha)),
                               (cx_i, cy_i), ir, 3)
            pygame.draw.line(icon_s, (*color, min(255, alpha)),
                             (cx_i, cy_i - ir // 2), (cx_i, cy_i + ir // 2), 2)
            pygame.draw.line(icon_s, (*color, min(255, alpha)),
                             (cx_i - ir // 2, cy_i), (cx_i + ir // 2, cy_i), 2)
        elif slot == 'accessory':
            pygame.draw.circle(icon_s, (*color, min(255, alpha)),
                               (cx_i, cy_i), ir, 2)
            pygame.draw.circle(icon_s, (*glow_color, min(255, alpha)),
                               (cx_i, cy_i), ir // 2)
        else:
            pts = [(cx_i, cy_i - ir), (cx_i + ir, cy_i),
                   (cx_i, cy_i + ir), (cx_i - ir, cy_i)]
            pygame.draw.polygon(icon_s, (*color, min(255, alpha)), pts, 2)
            pygame.draw.circle(icon_s, (*glow_color, min(255, alpha)),
                               (cx_i, cy_i), ir // 3)

        surface.blit(icon_s, (int(sx - size), int(sy - size)))

    def _draw_final_results(self, surface, buttons, t):
        # 远景祭坛装饰
        self.altar.draw(surface, self.camera, t, self.color, 0.1)

        cx = WIDTH // 2
        slot_names = {'weapon': '武器', 'armor': '护甲',
                      'accessory': '饰品', 'rune': '符文'}

        # 标题
        title = _render_outlined(_font_lg, "— 召唤结果 —",
                                 RARITY_COLORS.get(self.best_rarity, (200, 200, 200)))
        surface.blit(title, (cx - title.get_width() // 2, 25))

        if len(self.results) == 1:
            self._draw_single_card(surface, t, slot_names, cx)
        else:
            self._draw_multi_cards(surface, t, slot_names, cx)

        # 确认按钮
        btn_w, btn_h = 220, 48
        btn_rect = pygame.Rect(cx - btn_w // 2, HEIGHT - 60, btn_w, btn_h)
        mx, my = pygame.mouse.get_pos()
        hover = btn_rect.collidepoint(mx, my)
        bc = self.color if hover else tuple(max(0, c - 40) for c in self.color)

        bs = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        pygame.draw.rect(bs, (*bc, 50 if hover else 25),
                         (0, 0, btn_w, btn_h), border_radius=10)
        pygame.draw.rect(bs, (*bc, 200),
                         (0, 0, btn_w, btn_h), 2, border_radius=10)
        surface.blit(bs, btn_rect)
        bt = _render_outlined(_font_sm, "确认", (240, 240, 250))
        surface.blit(bt, (cx - bt.get_width() // 2,
                          btn_rect.y + btn_h // 2 - bt.get_height() // 2))
        buttons['gacha_confirm'] = btn_rect

    def _draw_single_card(self, surface, t, slot_names, cx):
        tidx, rarity = self.results[0]
        tpl = self.equipment_db[tidx]
        rc = RARITY_COLORS.get(rarity, (200, 200, 200))
        gc = RARITY_GLOW.get(rarity, (220, 220, 255))

        card_w, card_h = 320, 420
        card_x = cx - card_w // 2
        card_y = 75

        # 光晕
        pulse = (math.sin(t * 2) + 1) * 0.5
        glow_s = pygame.Surface((card_w + 80, card_h + 80), pygame.SRCALPHA)
        ga = int(15 + pulse * 15)
        pygame.draw.rect(glow_s, (*rc, ga),
                         (0, 0, card_w + 80, card_h + 80), border_radius=24)
        surface.blit(glow_s, (card_x - 40, card_y - 40))

        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card, (12, 10, 22, 230),
                         (0, 0, card_w, card_h), border_radius=14)
        pygame.draw.rect(card, (*rc, 200),
                         (0, 0, card_w, card_h), 3, border_radius=14)

        pygame.draw.rect(card, (*rc, 40), (8, 8, card_w - 16, 42),
                         border_radius=6)

        nt = _render_outlined(_font_md, tpl[0], rc)
        card.blit(nt, (card_w // 2 - nt.get_width() // 2, 14))

        sn = slot_names.get(tpl[1], '')
        rn = RARITY_NAMES.get(rarity, '')
        it = _render_outlined(_font_sm, f"{rn} · {sn}", gc)
        card.blit(it, (card_w // 2 - it.get_width() // 2, 58))

        star_count = RARITY_ORDER.index(rarity) + 1
        star_tw = star_count * 26
        for si in range(star_count):
            sx_s = card_w // 2 - star_tw // 2 + si * 26 + 10
            bob = math.sin(t * 3 + si * 0.5) * 2
            pygame.draw.polygon(card, (*gc, 220),
                                _star_points(sx_s, 100 + int(bob), 10, 5))
            sts = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(sts, (*gc, 40), (12, 12), 12)
            card.blit(sts, (sx_s - 12, 88 + int(bob)))

        pygame.draw.line(card, (*rc, 60), (20, 122), (card_w - 20, 122), 1)

        self._draw_slot_icon_card(card, card_w // 2, 170, tpl[1], rc, gc, 40)

        stat_y = 230
        for k, v in tpl[3].items():
            st = _render_outlined(_font_sm, f"{k}: +{v}", (235, 235, 245))
            card.blit(st, (card_w // 2 - st.get_width() // 2, stat_y))
            stat_y += 32

        ri = RARITY_ORDER.index(rarity)
        dot_tw = (ri + 1) * 10
        for dj in range(ri + 1):
            dx = card_w // 2 - dot_tw // 2 + dj * 10 + 3
            pygame.draw.circle(card, rc, (dx, card_h - 18), 3)

        surface.blit(card, (card_x, card_y))

    def _draw_multi_cards(self, surface, t, slot_names, cx):
        cols = 5
        card_w, card_h = 195, 195
        spacing_x, spacing_y = 12, 12
        total_w = cols * card_w + (cols - 1) * spacing_x
        start_x = cx - total_w // 2
        start_y = 85

        for i, (tidx, rarity) in enumerate(self.results):
            col = i % cols
            row = i // cols
            rx = start_x + col * (card_w + spacing_x)
            ry = start_y + row * (card_h + spacing_y)
            tpl = self.equipment_db[tidx]
            rc = RARITY_COLORS.get(rarity, (200, 200, 200))
            gc = RARITY_GLOW.get(rarity, (220, 220, 255))

            appear_delay = i * 0.06
            appear_t = max(0, self.phase_timer - appear_delay)
            if appear_t <= 0:
                continue
            card_alpha = min(1.0, appear_t * 4)
            card_scale = min(1.0, appear_t * 3)

            aw = max(10, int(card_w * card_scale))
            ah = max(10, int(card_h * card_scale))

            card = pygame.Surface((aw, ah), pygame.SRCALPHA)
            pygame.draw.rect(card, (12, 10, 22, int(220 * card_alpha)),
                             (0, 0, aw, ah), border_radius=8)
            pygame.draw.rect(card, (*rc, int(180 * card_alpha)),
                             (0, 0, aw, ah), 2, border_radius=8)

            bar_h = max(1, int(28 * card_scale))
            pygame.draw.rect(card, (*rc, int(30 * card_alpha)),
                             (4, 4, aw - 8, bar_h), border_radius=4)

            nt = _render_outlined(_font_sm, tpl[0], rc)
            if nt.get_width() < aw - 8:
                nt_s = pygame.Surface(nt.get_size(), pygame.SRCALPHA)
                nt_s.blit(nt, (0, 0))
                nt_s.set_alpha(int(255 * card_alpha))
                card.blit(nt_s, (aw // 2 - nt.get_width() // 2,
                                 max(2, int(6 * card_scale))))

            rn = RARITY_NAMES.get(rarity, '')
            sn = slot_names.get(tpl[1], '')
            rt = _render_outlined(_font_xs, f"{rn} · {sn}", gc)
            if rt.get_width() < aw - 6:
                rt_s = pygame.Surface(rt.get_size(), pygame.SRCALPHA)
                rt_s.blit(rt, (0, 0))
                rt_s.set_alpha(int(255 * card_alpha))
                card.blit(rt_s, (aw // 2 - rt.get_width() // 2,
                                 max(2, int(34 * card_scale))))

            star_count = RARITY_ORDER.index(rarity) + 1
            star_tw = star_count * 16
            for si in range(star_count):
                sxx = aw // 2 - star_tw // 2 + si * 16 + 6
                syy = max(2, int(58 * card_scale))
                bob = math.sin(t * 3 + si * 0.4 + i) * 1.5
                pygame.draw.polygon(card, (*gc, int(200 * card_alpha)),
                                    _star_points(sxx, syy + int(bob), 6, 3))

            stat_y = max(2, int(80 * card_scale))
            for sk, sv in list(tpl[3].items())[:3]:
                st = _render_outlined(_font_xs, f"{sk}: +{sv}",
                                      (225, 225, 240))
                st_s = pygame.Surface(st.get_size(), pygame.SRCALPHA)
                st_s.blit(st, (0, 0))
                st_s.set_alpha(int(255 * card_alpha))
                card.blit(st_s, (aw // 2 - st.get_width() // 2, stat_y))
                stat_y += max(1, int(20 * card_scale))

            ri_v = RARITY_ORDER.index(rarity)
            for dj in range(ri_v + 1):
                pygame.draw.circle(card, (*rc, int(200 * card_alpha)),
                                   (8 + dj * 8, ah - 10), 3)

            ox = (card_w - aw) // 2
            oy = (card_h - ah) // 2
            surface.blit(card, (rx + ox, ry + oy))

    def _draw_slot_icon_card(self, card_surf, cx, cy, slot, color,
                              glow_color, size):
        if slot == 'weapon':
            pts = [(cx, cy - size), (cx + size // 3, cy + size // 4),
                   (cx, cy + size), (cx - size // 3, cy + size // 4)]
            pygame.draw.polygon(card_surf, color, pts)
            pygame.draw.line(card_surf, glow_color,
                             (cx - size // 2, cy + size - 5),
                             (cx + size // 2, cy + size - 5), 3)
        elif slot == 'armor':
            pygame.draw.circle(card_surf, color, (cx, cy), size, 4)
            pygame.draw.circle(card_surf, glow_color, (cx, cy), size // 2, 2)
            pygame.draw.line(card_surf, color,
                             (cx, cy - size // 2), (cx, cy + size // 2), 2)
        elif slot == 'accessory':
            pygame.draw.circle(card_surf, color, (cx, cy), size, 2)
            pygame.draw.circle(card_surf, glow_color, (cx, cy), size // 2)
        else:
            pts = [(cx, cy - size), (cx + size, cy),
                   (cx, cy + size), (cx - size, cy)]
            pygame.draw.polygon(card_surf, color, pts, 2)
            pygame.draw.circle(card_surf, glow_color, (cx, cy), size // 3)

    def handle_click(self, pos):
        if self.phase < 4:
            self.skip()
            return False
        elif self.phase == 4:
            btn_w, btn_h = 220, 48
            btn_rect = pygame.Rect(WIDTH // 2 - btn_w // 2, HEIGHT - 60,
                                   btn_w, btn_h)
            if btn_rect.collidepoint(pos):
                self.finished = True
                return True
        return False
