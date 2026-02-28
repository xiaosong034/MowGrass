"""
Boss模块 - 割草游戏Boss系统
包含多种Boss类型，每种Boss有独特的攻击模式和外观
"""

import pygame
import math
import random
import i18n

# ============================================================
#  常量 (会在 init() 中从主模块同步)
# ============================================================
WIDTH, HEIGHT = 1200, 800
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 68, 68)
PINK = (255, 100, 200)
CYAN = (78, 205, 196)
YELLOW = (255, 255, 0)
ORANGE = (255, 170, 0)
PURPLE = (170, 68, 255)

# ---- 描边文字渲染 ----
def _render_outlined(font, text, color, outline_color=(0, 0, 0), offset=1):
    """渲染带黑色描边的文字, 返回 Surface"""
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

# 外部引用 (在 init() 中注入)
_player = None
_swords = None
_screen_shake = None
_create_particles = None
_play_sfx = None
_font_sm = None
_font_xs = None

def init(player, swords_ref, screen_shake, create_particles_fn, play_sfx_fn, font_sm, font_xs, width=1200, height=800):
    """初始化Boss模块，注入主游戏的引用"""
    global _player, _swords, _screen_shake, _create_particles, _play_sfx
    global _font_sm, _font_xs, WIDTH, HEIGHT
    _player = player
    _swords = swords_ref
    _screen_shake = screen_shake
    _create_particles = create_particles_fn
    _play_sfx = play_sfx_fn
    _font_sm = font_sm
    _font_xs = font_xs
    WIDTH = width
    HEIGHT = height


# ============================================================
#  Boss基类
# ============================================================
class BossBase:
    """所有Boss的基类"""

    # Boss类型名称 (子类覆盖)
    BOSS_NAME = "BOSS"
    BOSS_TITLE = ""

    # 入场动画时长配置
    ENTRANCE_DURATION = 4.0      # 总入场时间
    ENTRANCE_WARN_END = 1.5      # 警告阶段结束时间
    ENTRANCE_SLIDE_END = 3.0     # 滑入阶段结束时间
    ENTRANCE_READY_END = 4.0     # 准备阶段结束时间

    def __init__(self, x, y, boss_level=1):
        self.boss_level = boss_level
        # 入场动画状态
        self.entrance_active = True
        self.entrance_timer = 0.0
        self.entrance_stage = 0     # 0=警告, 1=滑入, 2=亮相, 3=完成
        self.entrance_start_y = -120  # 从屏幕外出发
        self.entrance_target_x = x
        self.entrance_target_y = y
        self.x = x
        self.y = self.entrance_start_y
        # 基本属性
        self.health = self._calc_health()
        self.max_health = self.health
        self.size = self._calc_size()
        self.speed = self._calc_speed()
        self.damage = self._calc_damage()
        self.last_hit = 0
        self.flash_timer = 0
        self.phase = 0          # Boss阶段 (血量降低时切换)
        self.attack_timer = 0
        self.attack_interval = 3.0
        self.color_cycle = 0
        self.alive = True
        self.roar_played = False
        self.boss_bullets = []
        self.anim_timer = 0     # 动画计时器
        # 入场专用粒子/效果
        self._entrance_particles = []
        self._shockwave_radius = 0
        self._shockwave_alpha = 0
        self.entrance_scale = 0.1    # 入场缩放 0.1 → 1.0
        self.entrance_alpha = 0      # 入场透明度 0 → 255

    # ---- 显示属性 (用于UI显示翻译后的文本) ----
    @property
    def display_name(self):
        """返回翻译后的Boss名称"""
        return i18n.t(self.BOSS_NAME)

    @property
    def display_title(self):
        """返回翻译后的Boss称号"""
        return i18n.t(self.BOSS_TITLE)

    def _calc_health(self):
        return 500 * self.boss_level

    def _calc_size(self):
        return 60  # Boss大小固定，不随等级变化

    def _calc_speed(self):
        return 30 + self.boss_level * 5

    def _calc_damage(self):
        return 20 * self.boss_level

    def get_phase(self):
        """根据血量返回阶段: 0=满血, 1=半血, 2=濒死"""
        ratio = self.health / self.max_health
        if ratio > 0.6:
            return 0
        elif ratio > 0.3:
            return 1
        else:
            return 2

    def get_color(self):
        """Boss颜色循环"""
        self.color_cycle += 0.02
        r = int(128 + 127 * math.sin(self.color_cycle))
        g = int(128 + 127 * math.sin(self.color_cycle + 2.1))
        b = int(128 + 127 * math.sin(self.color_cycle + 4.2))
        return (r, g, b)

    def _do_attack(self, dt):
        """子类覆盖 - 发动攻击"""
        pass

    def _draw_body(self, surface, sx, sy, color):
        """子类覆盖 - 绘制Boss身体"""
        pygame.draw.circle(surface, color, (sx, sy), self.size)
        pygame.draw.circle(surface, WHITE, (sx, sy), self.size, 3)

    def _draw_extra(self, surface, sx, sy, shake):
        """子类覆盖 - 绘制额外效果"""
        pass

    def _update_entrance(self, dt):
        """更新入场动画"""
        self.entrance_timer += dt
        t = self.entrance_timer

        # 阶段0: 警告 (0 ~ 1.5s)
        if t < self.ENTRANCE_WARN_END:
            self.entrance_stage = 0
            # Boss在屏幕外等待
            self.y = self.entrance_start_y
            self.entrance_scale = 0.1
            self.entrance_alpha = max(0, min(255, int(255 * (t / self.ENTRANCE_WARN_END) * 0.3)))

        # 阶段1: Boss从上方滑入 (1.5 ~ 3.0s)
        elif t < self.ENTRANCE_SLIDE_END:
            self.entrance_stage = 1
            prog = (t - self.ENTRANCE_WARN_END) / (self.ENTRANCE_SLIDE_END - self.ENTRANCE_WARN_END)
            # ease-out cubic
            ease = 1 - (1 - prog) ** 3
            self.y = self.entrance_start_y + (self.entrance_target_y - self.entrance_start_y) * ease
            self.x = self.entrance_target_x
            # 缩放和透明度随进度增长
            self.entrance_scale = 0.3 + 0.7 * ease
            self.entrance_alpha = max(0, min(255, int(80 + 175 * ease)))
            # 滑入过程中产生尾焰粒子
            if random.random() < 0.6:
                self._entrance_particles.append([
                    self.x + random.uniform(-self.size * 0.5, self.size * 0.5),
                    self.y + self.size,
                    random.uniform(-30, 30),
                    random.uniform(40, 120),
                    random.uniform(0.3, 0.7),
                    random.uniform(0.3, 0.7),  # max_life
                ])

        # 阶段2: 亮相 —— 震动 + 冲击波 (3.0 ~ 4.0s)
        elif t < self.ENTRANCE_READY_END:
            self.entrance_scale = 1.0
            self.entrance_alpha = 255
            if self.entrance_stage < 2:
                self.entrance_stage = 2
                self.y = self.entrance_target_y
                # 落地震动
                if _screen_shake:
                    _screen_shake.trigger(18, 0.5)
                if _play_sfx:
                    _play_sfx('boss_roar')
                self.roar_played = True
                # 产生大量粒子
                if _create_particles:
                    _create_particles(self.x, self.y, 40, 'boss_death')
                self._shockwave_radius = 0
                self._shockwave_alpha = 255
            # 冲击波扩张
            self._shockwave_radius += 400 * dt
            self._shockwave_alpha = max(0, self._shockwave_alpha - 300 * dt)

        # 阶段3: 入场完成
        else:
            self.entrance_active = False
            self.entrance_stage = 3
            self.y = self.entrance_target_y
            self.entrance_scale = 1.0
            self.entrance_alpha = 255

        # 更新入场粒子
        for p in self._entrance_particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self._entrance_particles = [p for p in self._entrance_particles if p[4] > 0]

    def _draw_entrance(self, surface, shake):
        """绘制入场动画的全屏效果"""
        t = self.entrance_timer
        sh = shake
        sw, sh_h = WIDTH, HEIGHT

        # --- 阶段0: 警告 ---
        if self.entrance_stage == 0:
            # 暗幕
            dark = pygame.Surface((sw, sh_h), pygame.SRCALPHA)
            alpha = max(0, min(200, int(180 * min(1, t / 0.5))))
            dark.fill((0, 0, 0, alpha))
            surface.blit(dark, (0, 0))

            # 闪烁警告条
            if math.sin(t * 12) > 0:
                stripe_h = 60
                stripe_surf = pygame.Surface((sw, stripe_h), pygame.SRCALPHA)
                stripe_surf.fill((200, 0, 0, 140))
                surface.blit(stripe_surf, (0, sh_h // 2 - stripe_h // 2))

            # "WARNING" 文字 (闪烁)
            blink = math.sin(t * 8) > -0.3
            if blink and _font_sm:
                # 主文字
                warn_text = "⚠ WARNING ⚠"
                wt = _render_outlined(_font_sm, warn_text, RED)
                surface.blit(wt, (sw // 2 - wt.get_width() // 2, sh_h // 2 - 60))

                # Boss名称预告
                name = f"{self.display_title} - {self.display_name}"
                nt = _render_outlined(_font_sm, name, YELLOW)
                surface.blit(nt, (sw // 2 - nt.get_width() // 2, sh_h // 2 + 10))

            # 左右扫描线
            scan_x = int((t * 3 % 1.0) * sw)
            pygame.draw.line(surface, (255, 0, 0, 180), (scan_x, 0), (scan_x, sh_h), 2)
            pygame.draw.line(surface, (255, 0, 0, 180), (sw - scan_x, 0), (sw - scan_x, sh_h), 2)

            # 角落装饰线
            corner_len = 40
            corner_c = RED
            for cx, cy, dx, dy in [(0, 0, 1, 1), (sw, 0, -1, 1), (0, sh_h, 1, -1), (sw, sh_h, -1, -1)]:
                pygame.draw.line(surface, corner_c, (cx, cy), (cx + dx * corner_len, cy), 3)
                pygame.draw.line(surface, corner_c, (cx, cy), (cx, cy + dy * corner_len), 3)

        # --- 阶段1: 滑入 ---
        elif self.entrance_stage == 1:
            prog = (t - self.ENTRANCE_WARN_END) / (self.ENTRANCE_SLIDE_END - self.ENTRANCE_WARN_END)
            # 暗幕渐退
            dark = pygame.Surface((sw, sh_h), pygame.SRCALPHA)
            dark_alpha = max(0, min(200, int(180 * (1 - prog * 0.6))))
            dark.fill((0, 0, 0, dark_alpha))
            surface.blit(dark, (0, 0))

            # 入场粒子 (火焰尾迹)
            for p in self._entrance_particles:
                px, py = int(p[0] + sh[0]), int(p[1] + sh[1])
                life_ratio = p[4] / p[5]
                r = max(1, int(6 * life_ratio))
                a = max(0, min(255, int(255 * life_ratio)))
                # 火焰颜色
                colors = [(255, 200, 50, a), (255, 100, 0, a), (255, 50, 0, a)]
                c = random.choice(colors)
                ps = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, c, (r, r), r)
                surface.blit(ps, (px - r, py - r))

            # Boss名称浮现 (从底部上升)
            name_prog = min(1.0, prog * 2)
            if _font_sm and name_prog > 0.3:
                name = f"{self.display_title}"
                nt = _render_outlined(_font_sm, name, self._get_entrance_color())
                name_y = int(sh_h * 0.35 + (1 - name_prog) * 50)
                a = max(0, min(255, int(255 * (name_prog - 0.3) / 0.7)))
                nt.set_alpha(a)
                surface.blit(nt, (sw // 2 - nt.get_width() // 2, name_y))

                # Boss名
                bn = _render_outlined(_font_sm, self.display_name, WHITE)
                bn.set_alpha(a)
                surface.blit(bn, (sw // 2 - bn.get_width() // 2, name_y + 35))

        # --- 阶段2: 亮相冲击波 ---
        elif self.entrance_stage == 2:
            # 冲击波
            if self._shockwave_radius > 0 and self._shockwave_alpha > 0:
                sw_radius = int(self._shockwave_radius)
                sw_alpha = max(0, min(255, int(self._shockwave_alpha)))
                boss_sx = int(self.x + sh[0])
                boss_sy = int(self.y + sh[1])
                if sw_radius > 3:
                    ring_surf = pygame.Surface((sw_radius * 2 + 4, sw_radius * 2 + 4), pygame.SRCALPHA)
                    ec = self._get_entrance_color()
                    pygame.draw.circle(ring_surf, (*ec, sw_alpha), (sw_radius + 2, sw_radius + 2), sw_radius, max(2, sw_radius // 8))
                    surface.blit(ring_surf, (boss_sx - sw_radius - 2, boss_sy - sw_radius - 2))

            # Lv 文字闪现
            prog = (t - self.ENTRANCE_SLIDE_END) / (self.ENTRANCE_READY_END - self.ENTRANCE_SLIDE_END)
            if _font_sm and prog < 0.8:
                lv_text = f"Lv.{self.boss_level}"
                lt = _render_outlined(_font_sm, lv_text, YELLOW)
                a = max(0, min(255, int(255 * (1 - prog / 0.8))))
                lt.set_alpha(a)
                lx = sw // 2 - lt.get_width() // 2
                ly = int(sh_h * 0.30 - prog * 30)
                surface.blit(lt, (lx, ly))

    def _get_entrance_color(self):
        """入场特效颜色 - 子类可覆盖匹配Boss主题"""
        return YELLOW

    def _draw_entrance_scene(self, surface, shake, sx, sy, color):
        """绘制入场动画完整场景 - 子类可完全覆盖实现独特入场"""
        # 阶段0只画警告UI, 不画Boss本体
        if self.entrance_stage == 0:
            self._draw_entrance(surface, shake)
            return

        # 阶段1+: 画Boss本体 + 入场特效
        # 光环 (入场时更强烈)
        glow_size = self.size * 4
        glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        ec = self._get_entrance_color()
        pulse = 0.5 + 0.5 * math.sin(self.entrance_timer * 6)
        glow_a = max(0, min(255, int(80 * pulse)))
        pygame.draw.circle(glow_surf, (*ec, glow_a),
                           (glow_size // 2, glow_size // 2), glow_size // 2)
        surface.blit(glow_surf, (sx - glow_size // 2, sy - glow_size // 2))

        # 画本体
        self._draw_body(surface, sx, sy, color)

        # 画入场UI叠加层
        self._draw_entrance(surface, shake)

    def update(self, dt, game_time):
        if not self.alive:
            return

        self.anim_timer += dt

        # 入场动画阶段
        if self.entrance_active:
            self._update_entrance(dt)
            return

        if not self.roar_played:
            if _play_sfx:
                _play_sfx('boss_roar')
            self.roar_played = True

        # 更新阶段
        self.phase = self.get_phase()

        # 追踪玩家
        if _player:
            dx = _player.x - self.x
            dy = _player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0 and dist > self.size:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt

        if self.flash_timer > 0:
            self.flash_timer -= dt

        now = pygame.time.get_ticks()

        # 攻击
        self.attack_timer -= dt
        if self.attack_timer <= 0:
            interval = max(1.0, self.attack_interval - self.boss_level * 0.3)
            # 濒死时攻击更快
            if self.phase == 2:
                interval *= 0.6
            elif self.phase == 1:
                interval *= 0.8
            self.attack_timer = interval
            self._do_attack(dt)

        # 更新弹幕
        if _player:
            for b in self.boss_bullets:
                b[0] += b[2] * dt
                b[1] += b[3] * dt
                b[4] -= dt
                pd = math.hypot(b[0] - _player.x, b[1] - _player.y)
                if pd < 25:
                    _player.take_damage(self.damage * 0.5 * dt * 60)
                    b[4] = 0
            self.boss_bullets = [b for b in self.boss_bullets if b[4] > 0]

        # 武器伤害判定
        self._check_weapon_damage(dt, now)

        # 碰撞伤害
        if _player:
            dist = math.hypot(_player.x - self.x, _player.y - self.y)
            if dist < self.size + 25:
                _player.take_damage(self.damage * dt)

        if self.health <= 0:
            self.alive = False

    def _check_weapon_damage(self, dt, now):
        """检查玩家武器对Boss的伤害"""
        if not _player:
            return

        dist = math.hypot(_player.x - self.x, _player.y - self.y)

        # 毒气伤害
        if 'poison' in _player.weapons:
            pw = _player.weapons['poison']
            poison_range = 60 + pw['level'] * 25
            if dist < poison_range and now - self.last_hit > 400:
                damage = pw['level'] * 8
                if pw.get('activated'):
                    damage *= 2
                if pw.get('ultimate'):
                    damage *= 2
                self.health -= damage
                self.last_hit = now
                self.flash_timer = 0.1
                if _create_particles:
                    _create_particles(self.x, self.y, 5, 'poison')

        # 光剑伤害
        if 'sword' in _player.weapons and _swords:
            swords_list = _swords() if callable(_swords) else _swords
            for sword in swords_list:
                sd = math.hypot(sword[0] - self.x, sword[1] - self.y)
                if sd < self.size + 10 and now - self.last_hit > 200:
                    damage = _player.weapons['sword']['level'] * 20
                    if _player.weapons['sword'].get('ultimate'):
                        damage *= 2
                    self.health -= damage
                    self.last_hit = now
                    self.flash_timer = 0.1
                    if _create_particles:
                        _create_particles(self.x, self.y, 8, 'sword_hit')

    def draw(self, surface, shake):
        if not self.alive:
            return

        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])
        color = WHITE if self.flash_timer > 0 else self.get_color()

        # 入场动画阶段的特殊绘制 (子类可覆盖 _draw_entrance_scene 实现独特入场)
        if self.entrance_active:
            self._draw_entrance_scene(surface, shake, sx, sy, color)
            return

        # --- 正常战斗绘制 ---
        # 光环
        glow_surf = pygame.Surface((self.size * 4, self.size * 4), pygame.SRCALPHA)
        r_c = max(0, min(255, int(color[0])))
        g_c = max(0, min(255, int(color[1])))
        b_c = max(0, min(255, int(color[2])))
        pygame.draw.circle(glow_surf, (r_c, g_c, b_c, 30),
                           (self.size * 2, self.size * 2), self.size * 2)
        surface.blit(glow_surf, (sx - self.size * 2, sy - self.size * 2))

        # 身体 (子类可覆盖)
        self._draw_body(surface, sx, sy, color)

        # 额外效果 (子类可覆盖)
        self._draw_extra(surface, sx, sy, shake)

        # 血条 (屏幕顶部)
        self._draw_health_bar(surface, shake, color)

        # 弹幕
        self._draw_bullets(surface, shake)

    def _draw_health_bar(self, surface, shake, color):
        bar_w = 400
        bar_h = 20
        bar_x = WIDTH // 2 - bar_w // 2 + int(shake[0])
        bar_y = 10 + int(shake[1])

        # 背景
        pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=5)
        # 血量
        hp_ratio = max(0, self.health / self.max_health)
        fill_color = (
            max(0, min(255, int(255 * (1 - hp_ratio)))),
            max(0, min(255, int(255 * hp_ratio))),
            50
        )
        pygame.draw.rect(surface, fill_color, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=5)
        # 边框
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=5)

        # Boss名称
        name = f"{self.display_name} Lv.{self.boss_level}"
        if self.BOSS_TITLE:
            name = f"{self.display_title} - {name}"
        if _font_sm:
            name_surf = _render_outlined(_font_sm, name, color)
            surface.blit(name_surf, (WIDTH // 2 - name_surf.get_width() // 2 + int(shake[0]),
                                      bar_y + bar_h + 2 + int(shake[1])))

        # 阶段指示
        if self.phase >= 1 and _font_xs:
            phase_names = ["", "▲ 狂暴化 ▲", "▲▲ 濒死暴走 ▲▲"]
            phase_colors = [WHITE, ORANGE, RED]
            pt = _render_outlined(_font_xs, phase_names[self.phase], phase_colors[self.phase])
            surface.blit(pt, (WIDTH // 2 - pt.get_width() // 2 + int(shake[0]),
                               bar_y + bar_h + 24 + int(shake[1])))

    def _draw_bullets(self, surface, shake):
        for b in self.boss_bullets:
            bsx = int(b[0] + shake[0])
            bsy = int(b[1] + shake[1])
            # 弹幕颜色根据Boss类型不同
            bullet_color = self._get_bullet_color()
            pygame.draw.circle(surface, bullet_color, (bsx, bsy), 5)
            pygame.draw.circle(surface, WHITE, (bsx, bsy), 5, 1)

    def _get_bullet_color(self):
        return PINK


# ============================================================
#  Boss类型1: 骷髅王 (经典圆形弹幕)
# ============================================================
class SkullKing(BossBase):
    BOSS_NAME = "骷髅王"
    BOSS_TITLE = "亡灵领主"
    ENTRANCE_DURATION = 6.0
    ENTRANCE_WARN_END = 1.0
    ENTRANCE_SLIDE_END = 4.5
    ENTRANCE_READY_END = 6.0

    def _get_entrance_color(self):
        return PINK

    def __init__(self, x, y, boss_level=1):
        super().__init__(x, y, boss_level)
        self.float_offset = 0
        self.crown_angle = 0
        self.bone_particles = []   # [x, y, vx, vy, life]
        # --- 独特入场状态 ---
        self._sk_crack_segments = []   # 地面裂缝
        self._sk_bone_pieces = []      # 飞来的骨头碎片
        self._sk_crown_sparks = []     # 王冠火花
        self._sk_cloak_alpha = 0       # 披风透明度
        self._sk_eye_flame = 0         # 眼焰透明度
        self._sk_shockwave_triggered = False

    def _calc_health(self):
        return 500 * self.boss_level

    # ---- 骷髅王独特入场: 地裂 → 骨手 → 骷髅升起 → 披风+王冠 → 眼焰 ----
    def _update_entrance(self, dt):
        self.entrance_timer += dt
        t = self.entrance_timer
        tx, ty = self.entrance_target_x, self.entrance_target_y

        if t < self.ENTRANCE_WARN_END:  # Phase0: 警告+地裂
            self.entrance_stage = 0
            self.y = self.entrance_start_y
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
            if len(self._sk_crack_segments) < 10 and random.random() < dt * 8:
                cx = tx + random.uniform(-100, 100)
                cy = ty + random.uniform(-20, 60)
                self._sk_crack_segments.append([cx, cy, random.uniform(-50, 50), random.uniform(-25, 15), 0])
        elif t < 2.5:  # Phase1: 骨手+骷髅升起
            self.entrance_stage = 1
            prog = (t - self.ENTRANCE_WARN_END) / 1.5
            ease = 1 - (1 - prog) ** 2
            self.x = tx
            self.y = ty + int(180 * (1 - ease))
            self.entrance_scale = 0.3 + 0.3 * ease
            self.entrance_alpha = max(0, min(255, int(200 * ease)))
            for c in self._sk_crack_segments:
                c[4] = min(1.0, c[4] + dt * 2)
            if random.random() < dt * 6:
                a = random.uniform(0, math.pi * 2)
                d = random.uniform(200, 400)
                self._sk_bone_pieces.append([tx + math.cos(a)*d, ty + math.sin(a)*d, -math.cos(a)*300, -math.sin(a)*300, 1.5])
        elif t < 4.0:  # Phase2: 骨骼组装+披风
            self.entrance_stage = 2
            prog = (t - 2.5) / 1.5
            self.y = ty
            self.entrance_scale = 0.6 + 0.3 * prog
            self.entrance_alpha = max(0, min(255, int(200 + 55 * prog)))
            self._sk_cloak_alpha = min(255, int(255 * prog))
        elif t < 5.5:  # Phase3: 王冠凝聚+眼焰点燃
            self.entrance_stage = 2
            prog = (t - 4.0) / 1.5
            self.entrance_scale = 0.9 + 0.1 * prog
            self.entrance_alpha = 255
            self._sk_cloak_alpha = 255
            self._sk_eye_flame = min(255, int(255 * prog))
            if random.random() < dt * 10:
                self._sk_crown_sparks.append([tx + random.uniform(-30, 30), ty - self.size * 0.7, random.uniform(-50, 50), random.uniform(-80, -20), 0.8])
        elif t < self.ENTRANCE_READY_END:  # Phase4: 冲击波
            self.entrance_scale = 1.0
            self.entrance_alpha = 255
            if not self._sk_shockwave_triggered:
                self._sk_shockwave_triggered = True
                self._shockwave_radius = 0
                self._shockwave_alpha = 255
                if _screen_shake: _screen_shake.trigger(18, 0.5)
                if _play_sfx: _play_sfx('boss_roar')
                self.roar_played = True
                if _create_particles: _create_particles(self.x, self.y, 40, 'boss_death')
            self._shockwave_radius += 400 * dt
            self._shockwave_alpha = max(0, self._shockwave_alpha - 300 * dt)
        else:
            self.entrance_active = False
            self.entrance_stage = 3
            self.y = ty
            self.entrance_scale = 1.0
            self.entrance_alpha = 255

        for bp in self._sk_bone_pieces:
            bp[0] += bp[2] * dt; bp[1] += bp[3] * dt; bp[4] -= dt
            dx = tx - bp[0]; dy = ty - bp[1]; d = max(1, math.hypot(dx, dy))
            bp[2] += dx/d * 200 * dt; bp[3] += dy/d * 200 * dt
        self._sk_bone_pieces = [b for b in self._sk_bone_pieces if b[4] > 0]
        for cs in self._sk_crown_sparks:
            cs[0] += cs[2]*dt; cs[1] += cs[3]*dt; cs[4] -= dt*2
        self._sk_crown_sparks = [c for c in self._sk_crown_sparks if c[4] > 0]

    def _draw_entrance_scene(self, surface, shake, sx, sy, color):
        t = self.entrance_timer
        sh = shake
        sw_w, sw_h = WIDTH, HEIGHT

        if self.entrance_stage == 0:
            dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
            dark.fill((0, 0, 0, max(0, min(200, int(180 * min(1, t/0.5))))))
            surface.blit(dark, (0, 0))
            if math.sin(t*12) > 0:
                ss = pygame.Surface((sw_w, 60), pygame.SRCALPHA); ss.fill((200, 0, 0, 140))
                surface.blit(ss, (0, sw_h//2 - 30))
            if math.sin(t*8) > -0.3 and _font_sm:
                wt = _render_outlined(_font_sm, "☠ WARNING ☠", RED)
                surface.blit(wt, (sw_w//2 - wt.get_width()//2, sw_h//2 - 60))
                nt = _render_outlined(_font_sm, f"{self.display_title} - {self.display_name}", PINK)
                surface.blit(nt, (sw_w//2 - nt.get_width()//2, sw_h//2 + 10))
            for cx, cy, dx, dy, p in self._sk_crack_segments:
                if p > 0:
                    pygame.draw.line(surface, PINK, (int(cx+sh[0]), int(cy+sh[1])), (int(cx+dx*p+sh[0]), int(cy+dy*p+sh[1])), max(1, int(3*p)))
            return

        # Phase 1+: 暗幕渐退
        prog_t = min(1.0, (t - self.ENTRANCE_WARN_END) / 3.0)
        dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
        dark.fill((0, 0, 0, max(0, min(200, int(150*(1-prog_t*0.7))))))
        surface.blit(dark, (0, 0))
        # 地裂
        for cx, cy, dx, dy, p in self._sk_crack_segments:
            if p > 0:
                pygame.draw.line(surface, PINK, (int(cx+sh[0]), int(cy+sh[1])), (int(cx+dx*p+sh[0]), int(cy+dy*p+sh[1])), max(1, int(3*p)))
        # 骨片飞入
        for bx, by, _, _, bl in self._sk_bone_pieces:
            if bl > 0:
                bs = pygame.Surface((12, 12), pygame.SRCALPHA)
                pa = max(0, min(255, int(255*min(1, bl))))
                pygame.draw.ellipse(bs, (255, 255, 230, pa), (1, 3, 10, 6))
                surface.blit(bs, (int(bx+sh[0])-6, int(by+sh[1])-6))
        # 光环
        gs = int(self.size * 4 * max(0.1, self.entrance_scale))
        if gs > 0:
            gsf = pygame.Surface((gs, gs), pygame.SRCALPHA)
            pulse = 0.5 + 0.5*math.sin(t*6)
            pygame.draw.circle(gsf, (255, 100, 200, max(0, min(80, int(80*pulse)))), (gs//2, gs//2), gs//2)
            surface.blit(gsf, (sx-gs//2, sy-gs//2))
        # Boss本体
        self._draw_body(surface, sx, sy, color)
        # 王冠火花
        for csx, csy, _, _, cl in self._sk_crown_sparks:
            if cl > 0:
                pa = max(0, min(255, int(255*cl/0.8)))
                psf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(psf, (255, 215, 0, pa), (4, 4), max(1, int(4*cl)))
                surface.blit(psf, (int(csx+sh[0])-4, int(csy+sh[1])-4))
        # 冲击波
        if self._shockwave_radius > 0 and self._shockwave_alpha > 0:
            sr = int(self._shockwave_radius); sa = max(0, min(255, int(self._shockwave_alpha)))
            if sr > 3:
                rs = pygame.Surface((sr*2+4, sr*2+4), pygame.SRCALPHA)
                pygame.draw.circle(rs, (255, 100, 200, sa), (sr+2, sr+2), sr, max(2, sr//8))
                surface.blit(rs, (sx-sr-2, sy-sr-2))
        # 标题文字
        if t > 1.5 and t < 5.5 and _font_sm:
            ta = max(0, min(255, int(255*min(1, (t-1.5)/1.5))))
            if t > 5.0: ta = max(0, min(255, int(255*(5.5-t)/0.5)))
            nt = _render_outlined(_font_sm, self.display_title, PINK); nt.set_alpha(ta)
            surface.blit(nt, (sw_w//2 - nt.get_width()//2, int(sw_h*0.28)))
            bn = _render_outlined(_font_sm, self.display_name, WHITE); bn.set_alpha(ta)
            surface.blit(bn, (sw_w//2 - bn.get_width()//2, int(sw_h*0.28)+35))

    def update(self, dt, game_time):
        if self.entrance_active:
            super().update(dt, game_time)
            return
        # 漂浮动画
        self.float_offset = math.sin(game_time * 2) * 5
        # 王冠旋转
        self.crown_angle += dt * 2
        # 更新骨刺粒子
        for p in self.bone_particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt * 2
        self.bone_particles = [p for p in self.bone_particles if p[4] > 0]
        super().update(dt, game_time)

    def _do_attack(self, dt):
        """圆形弹幕 - 越低血量弹幕越密集"""
        bullet_count = 8 + self.boss_level * 4
        if self.phase >= 1:
            bullet_count += 4
        if self.phase >= 2:
            bullet_count += 4

        for i in range(bullet_count):
            angle = (2 * math.pi / bullet_count) * i + self.color_cycle
            speed = 150 + self.phase * 30
            bvx = math.cos(angle) * speed
            bvy = math.sin(angle) * speed
            self.boss_bullets.append([self.x, self.y, bvx, bvy, 3.0])

        # 攻击时生成骨刺粒子
        for _ in range(6):
            a = random.uniform(0, math.pi * 2)
            sp = random.uniform(30, 80)
            self.bone_particles.append([
                self.x, self.y,
                math.cos(a) * sp, math.sin(a) * sp,
                1.0
            ])

        if _screen_shake:
            _screen_shake.trigger(6, 0.2)
        if _play_sfx:
            _play_sfx('explosion')

    def _draw_body(self, surface, sx, sy, color):
        scale = self.entrance_scale if self.entrance_active else 1.0
        alpha = self.entrance_alpha if self.entrance_active else 255
        fy = sy + (self.float_offset if not self.entrance_active else 0)
        sz = self.size

        # 披风 / 暗影
        cloak_w = int(90 * scale)
        cloak_h = int(130 * scale)
        if cloak_w > 0 and cloak_h > 0:
            cs = pygame.Surface((cloak_w, cloak_h), pygame.SRCALPHA)
            cloak_c = (color[0], max(0, color[1] // 3), max(0, color[2] // 2), max(0, min(255, alpha - 40)))
            pygame.draw.ellipse(cs, cloak_c, (0, 0, cloak_w, cloak_h))
            surface.blit(cs, (sx - cloak_w // 2, int(fy - 30 * scale)))

        # 骷髅身体
        body_r = int(sz * 0.7 * scale)
        if body_r > 0:
            bs = pygame.Surface((body_r * 2 + 4, body_r * 2 + 4), pygame.SRCALPHA)
            body_c = (255, 255, 255, max(0, min(255, alpha)))
            pygame.draw.ellipse(bs, body_c, (2, 2, int(body_r * 1.5), body_r * 2))
            surface.blit(bs, (sx - body_r, int(fy - body_r * 0.3)))

        # 骷髅头
        head_r = int(sz * 0.55 * scale)
        if head_r > 1:
            head_c = (250, 245, 230, max(0, min(255, alpha)))
            pygame.draw.circle(surface, head_c, (sx, int(fy - sz * 0.25 * scale)), head_r)
            pygame.draw.circle(surface, (200, 190, 180, max(0, min(255, alpha))),
                               (sx, int(fy - sz * 0.25 * scale)), head_r, max(1, int(2 * scale)))

        # 眼窝 (红色三角形 + 发光)
        eye_r = int(sz // 4 * scale)
        if eye_r > 1:
            for ex_off in [-1, 1]:
                eye_cx = sx + ex_off * int(sz * 0.28 * scale)
                eye_cy = int(fy - sz * 0.35 * scale)
                # 发光效果
                glow_r = eye_r + int(4 * scale)
                gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (255, 0, 0, max(0, min(255, alpha // 3))), (glow_r, glow_r), glow_r)
                surface.blit(gs, (eye_cx - glow_r, eye_cy - glow_r))
                # 三角形眼窝
                tri = [
                    (eye_cx - eye_r, eye_cy + int(eye_r * 0.3)),
                    (eye_cx + eye_r, eye_cy + int(eye_r * 0.3)),
                    (eye_cx, eye_cy - eye_r),
                ]
                pygame.draw.polygon(surface, RED, tri)

        # 王冠
        crown_y = int(fy - sz * 0.65 * scale)
        crown_w = int(sz * 0.7 * scale)
        if crown_w > 2:
            spikes = 5
            crown_pts = []
            for i in range(spikes * 2 + 1):
                px = sx - crown_w // 2 + i * crown_w // (spikes * 2)
                if i % 2 == 0:
                    spike_h = int(20 * scale + math.sin(self.crown_angle + i) * 3 * scale)
                    py = crown_y - spike_h
                else:
                    py = crown_y
                crown_pts.append((px, py))
            crown_pts.append((sx + crown_w // 2, crown_y + int(8 * scale)))
            crown_pts.append((sx - crown_w // 2, crown_y + int(8 * scale)))
            crown_c = (255, 215, 0, max(0, min(255, alpha)))
            cs2 = pygame.Surface((crown_w + 20, int(50 * scale) + 20), pygame.SRCALPHA)
            shifted = [(p[0] - sx + crown_w // 2 + 10, p[1] - crown_y + int(30 * scale)) for p in crown_pts]
            if len(shifted) >= 3:
                pygame.draw.polygon(cs2, crown_c, shifted)
            surface.blit(cs2, (sx - crown_w // 2 - 10, crown_y - int(30 * scale)))

        # 嘴巴 (锯齿形)
        mouth_y = int(fy - sz * 0.05 * scale)
        teeth = 8
        points = []
        for i in range(teeth):
            mx = sx - int(sz * 0.4 * scale) + i * int(sz * 0.8 * scale) // max(1, teeth - 1)
            my = mouth_y + (int(7 * scale) if i % 2 == 0 else int(-7 * scale))
            points.append((mx, my))
        if len(points) >= 2:
            pygame.draw.lines(surface, WHITE, False, points, max(1, int(3 * scale)))

        # 骨刺粒子
        for bx, by, _, _, bl in self.bone_particles:
            if bl <= 0:
                continue
            pa = max(0, min(255, int(255 * bl)))
            bps = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(bps, (255, 255, 255, pa), (4, 4), max(1, int(3 * bl)))
            surface.blit(bps, (int(bx) - 4, int(by) - 4))

    def _get_bullet_color(self):
        return PINK


# ============================================================
#  Boss类型2: 毒液巨兽 (螺旋弹幕 + 毒雾)
# ============================================================
class VenomBeast(BossBase):
    BOSS_NAME = "毒液巨兽"
    BOSS_TITLE = "深渊之王"
    ENTRANCE_DURATION = 6.5
    ENTRANCE_WARN_END = 1.0
    ENTRANCE_SLIDE_END = 5.0
    ENTRANCE_READY_END = 6.5

    def _get_entrance_color(self):
        return (0, 255, 100)

    def __init__(self, x, y, boss_level=1):
        super().__init__(x, y, boss_level)
        self.spiral_angle = 0
        self.fog_timer = 0
        self.tentacle_angles = [random.uniform(0, math.pi * 2) for _ in range(6)]
        self.pulse_phase = 0
        self.droplets = []  # [dx, dy, vx, vy, life, max_life]
        # --- 独特入场状态 ---
        self._vb_pool_radius = 0
        self._vb_bubbles = []     # [x, y, vy, size, life]
        self._vb_rise_prog = 0    # 巨兽升起进度
        self._vb_solidify = 0     # 固化进度 0~1
        self._vb_eye_open = 0     # 眼睛张开度 0~1
        self._vb_shockwave_done = False

    def _calc_health(self):
        return 600 * self.boss_level

    def _calc_speed(self):
        return 25 + self.boss_level * 3  # 慢但肉

    # ---- 毒液巨兽独特入场: 毒池 → 冒泡 → 巨兽升起 → 固化 → 睁眼 ----
    def _update_entrance(self, dt):
        self.entrance_timer += dt
        t = self.entrance_timer
        tx, ty = self.entrance_target_x, self.entrance_target_y

        if t < self.ENTRANCE_WARN_END:  # Phase0: 警告
            self.entrance_stage = 0
            self.y = self.entrance_start_y
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
            self._vb_pool_radius = min(120, int(t / self.ENTRANCE_WARN_END * 120))
        elif t < 2.5:  # Phase1: 毒池扩大+冒泡
            self.entrance_stage = 1
            prog = (t - self.ENTRANCE_WARN_END) / 1.5
            self._vb_pool_radius = 120 + int(60 * prog)
            self.x = tx
            self.y = ty + 100
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
            if random.random() < dt * 12:
                bx = tx + random.uniform(-self._vb_pool_radius * 0.7, self._vb_pool_radius * 0.7)
                by = ty + random.uniform(20, 60)
                self._vb_bubbles.append([bx, by, random.uniform(-80, -30), random.uniform(3, 8), random.uniform(0.5, 1.2)])
        elif t < 4.0:  # Phase2: 巨兽从毒池中升起
            self.entrance_stage = 1
            prog = (t - 2.5) / 1.5
            ease = 1 - (1 - prog) ** 3
            self._vb_rise_prog = ease
            self.x = tx
            self.y = ty + int(100 * (1 - ease))
            self.entrance_scale = 0.3 + 0.5 * ease
            self.entrance_alpha = max(0, min(255, int(200 * ease)))
            if random.random() < dt * 15:
                bx = tx + random.uniform(-80, 80)
                by = self.y + self.size * 0.5
                self._vb_bubbles.append([bx, by, random.uniform(-100, -40), random.uniform(4, 10), random.uniform(0.4, 0.8)])
        elif t < 5.0:  # Phase3: 身体固化
            self.entrance_stage = 2
            prog = (t - 4.0) / 1.0
            self._vb_solidify = prog
            self.y = ty
            self.entrance_scale = 0.8 + 0.2 * prog
            self.entrance_alpha = max(0, min(255, int(200 + 55 * prog)))
            if prog > 0.5:
                self._vb_eye_open = min(1.0, (prog - 0.5) * 2)
        elif t < self.ENTRANCE_READY_END:  # Phase4: 睁眼+毒爆冲击波
            self.entrance_scale = 1.0
            self.entrance_alpha = 255
            self._vb_solidify = 1.0
            self._vb_eye_open = 1.0
            if not self._vb_shockwave_done:
                self._vb_shockwave_done = True
                self._shockwave_radius = 0
                self._shockwave_alpha = 255
                if _screen_shake: _screen_shake.trigger(15, 0.5)
                if _play_sfx: _play_sfx('boss_roar')
                self.roar_played = True
                if _create_particles: _create_particles(self.x, self.y, 40, 'boss_death')
            self._shockwave_radius += 350 * dt
            self._shockwave_alpha = max(0, self._shockwave_alpha - 250 * dt)
        else:
            self.entrance_active = False
            self.entrance_stage = 3
            self.y = ty
            self.entrance_scale = 1.0
            self.entrance_alpha = 255

        for b in self._vb_bubbles:
            b[0] += random.uniform(-10, 10) * dt
            b[1] += b[2] * dt
            b[4] -= dt
        self._vb_bubbles = [b for b in self._vb_bubbles if b[4] > 0]

    def _draw_entrance_scene(self, surface, shake, sx, sy, color):
        t = self.entrance_timer
        sh = shake
        sw_w, sw_h = WIDTH, HEIGHT
        tx = int(self.entrance_target_x + sh[0])
        ty_s = int(self.entrance_target_y + sh[1])

        if self.entrance_stage == 0:
            dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
            dark.fill((0, 0, 0, max(0, min(200, int(180 * min(1, t / 0.5))))))
            surface.blit(dark, (0, 0))
            if math.sin(t * 12) > 0:
                ss = pygame.Surface((sw_w, 60), pygame.SRCALPHA); ss.fill((0, 150, 0, 140))
                surface.blit(ss, (0, sw_h // 2 - 30))
            if math.sin(t * 8) > -0.3 and _font_sm:
                wt = _render_outlined(_font_sm, "\u2620 WARNING \u2620", (0, 255, 100))
                surface.blit(wt, (sw_w // 2 - wt.get_width() // 2, sw_h // 2 - 60))
                nt = _render_outlined(_font_sm, f"{self.display_title} - {self.display_name}", (0, 255, 100))
                surface.blit(nt, (sw_w // 2 - nt.get_width() // 2, sw_h // 2 + 10))
            # 毒池开始形成
            if self._vb_pool_radius > 5:
                ps = pygame.Surface((self._vb_pool_radius * 2 + 4, 40), pygame.SRCALPHA)
                pygame.draw.ellipse(ps, (0, 150, 0, 100), (0, 0, self._vb_pool_radius * 2 + 4, 40))
                surface.blit(ps, (tx - self._vb_pool_radius - 2, ty_s + 20))
            return

        # Phase 1+:
        prog_t = min(1.0, (t - self.ENTRANCE_WARN_END) / 3.0)
        dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
        dark.fill((0, 0, 0, max(0, min(200, int(160 * (1 - prog_t * 0.7))))))
        surface.blit(dark, (0, 0))
        # 毒池
        pr = max(1, self._vb_pool_radius)
        pool_h = max(1, int(30 + 15 * math.sin(t * 3)))
        ps = pygame.Surface((pr * 2 + 4, pool_h + 4), pygame.SRCALPHA)
        pool_a = max(0, min(180, int(180 * (1 - max(0, self._vb_solidify) * 0.5))))
        pygame.draw.ellipse(ps, (0, 180, 50, pool_a), (0, 0, pr * 2 + 4, pool_h + 4))
        pygame.draw.ellipse(ps, (0, 255, 80, max(0, min(255, pool_a + 30))), (0, 0, pr * 2 + 4, pool_h + 4), 2)
        surface.blit(ps, (tx - pr - 2, ty_s + int(self.size * 0.4)))
        # 气泡
        for bx, by, _, bsz, bl in self._vb_bubbles:
            if bl > 0:
                ba = max(0, min(255, int(200 * bl)))
                br = max(1, int(bsz * bl))
                bsf = pygame.Surface((br * 2 + 2, br * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(bsf, (0, 255, 100, ba), (br + 1, br + 1), br)
                pygame.draw.circle(bsf, (150, 255, 150, max(0, ba // 2)), (br + 1, br + 1), br, 1)
                surface.blit(bsf, (int(bx + sh[0]) - br - 1, int(by + sh[1]) - br - 1))
        # 光环
        if self.entrance_scale > 0.1:
            gs = int(self.size * 4 * self.entrance_scale)
            if gs > 0:
                gsf = pygame.Surface((gs, gs), pygame.SRCALPHA)
                pulse = 0.5 + 0.5 * math.sin(t * 5)
                pygame.draw.circle(gsf, (0, 255, 100, max(0, min(60, int(60 * pulse)))), (gs // 2, gs // 2), gs // 2)
                surface.blit(gsf, (sx - gs // 2, sy - gs // 2))
        # Boss本体
        if self.entrance_alpha > 10:
            self._draw_body(surface, sx, sy, color)
        # 冲击波
        if self._shockwave_radius > 0 and self._shockwave_alpha > 0:
            sr = int(self._shockwave_radius); sa = max(0, min(255, int(self._shockwave_alpha)))
            if sr > 3:
                rs = pygame.Surface((sr * 2 + 4, sr * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(rs, (0, 255, 100, sa), (sr + 2, sr + 2), sr, max(2, sr // 8))
                surface.blit(rs, (sx - sr - 2, sy - sr - 2))
        # 标题
        if 1.5 < t < 5.5 and _font_sm:
            ta = max(0, min(255, int(255 * min(1, (t - 1.5) / 1.5))))
            if t > 5.0: ta = max(0, min(255, int(255 * (5.5 - t) / 0.5)))
            nt = _render_outlined(_font_sm, self.display_title, (0, 255, 100)); nt.set_alpha(ta)
            surface.blit(nt, (sw_w // 2 - nt.get_width() // 2, int(sw_h * 0.28)))
            bn = _render_outlined(_font_sm, self.display_name, WHITE); bn.set_alpha(ta)
            surface.blit(bn, (sw_w // 2 - bn.get_width() // 2, int(sw_h * 0.28) + 35))

    def update(self, dt, game_time):
        if self.entrance_active:
            super().update(dt, game_time)
            return
        # 脉动
        self.pulse_phase += dt * 3
        # 产生毒液滴
        if random.random() < dt * 3:
            self.droplets.append([
                random.uniform(-10, 10), 0,
                random.uniform(-20, 20), random.uniform(30, 60),
                random.uniform(1.0, 2.0), random.uniform(1.0, 2.0),
            ])
        # 更新毒液滴
        for d in self.droplets:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[4] -= dt * 0.5
        self.droplets = [d for d in self.droplets if d[4] > 0]
        super().update(dt, game_time)

    def _do_attack(self, dt):
        """螺旋弹幕"""
        arms = 3 + self.phase
        bullets_per_arm = 3 + self.boss_level
        for arm in range(arms):
            base = self.spiral_angle + (2 * math.pi / arms) * arm
            for j in range(bullets_per_arm):
                angle = base + j * 0.3
                speed = 120 + j * 20
                bvx = math.cos(angle) * speed
                bvy = math.sin(angle) * speed
                self.boss_bullets.append([self.x, self.y, bvx, bvy, 3.5])
        self.spiral_angle += 0.5

        if _screen_shake:
            _screen_shake.trigger(5, 0.15)
        if _play_sfx:
            _play_sfx('explosion')

    def _draw_body(self, surface, sx, sy, color):
        scale = self.entrance_scale if self.entrance_active else 1.0
        alpha = self.entrance_alpha if self.entrance_active else 255
        sz = self.size
        pulse = 1 + math.sin(self.pulse_phase) * 0.06 if not self.entrance_active else 1

        # 触手 (分段绘制)
        for i, ta in enumerate(self.tentacle_angles):
            ta += 0.02
            self.tentacle_angles[i] = ta
            length = sz * 1.5 * scale
            wave = math.sin(self.anim_timer * 3 + i) * 15 * scale
            segments = 5
            prev = (sx, sy)
            for j in range(1, segments + 1):
                t = j / segments
                seg_angle = ta + t * math.pi / 4
                seg_x = sx + math.cos(seg_angle) * (length * t) + wave * t
                seg_y = sy + math.sin(seg_angle) * (length * t) + wave * t * 0.5
                width = max(1, int((6 - j) * scale))
                g = max(0, min(255, int(color[1] * (1 - t * 0.5))))
                seg_c = (0, g, 0, max(0, min(255, int(alpha * (1 - t * 0.3)))))
                ls = pygame.Surface((abs(int(seg_x - prev[0])) + width * 2 + 2,
                                     abs(int(seg_y - prev[1])) + width * 2 + 2), pygame.SRCALPHA)
                # 简化: 直接画线
                tentacle_c = (0, g, 0)
                pygame.draw.line(surface, tentacle_c, (int(prev[0]), int(prev[1])),
                                 (int(seg_x), int(seg_y)), width)
                prev = (seg_x, seg_y)
            # 触手末端圆
            pygame.draw.circle(surface, (0, max(0, min(255, int(color[1] * 0.5))), 0),
                               (int(prev[0]), int(prev[1])), max(1, int(4 * scale)))

        # 背部尖刺
        spike_count = 5
        for i in range(spike_count):
            spike_x = sx + int((-spike_count // 2 + i) * 15 * scale)
            spike_y = int(sy - sz * scale * 0.8)
            sh_val = int(12 * scale + math.sin(self.anim_timer * 2 + i) * 3 * scale)
            spike_pts = [
                (spike_x, spike_y),
                (spike_x - int(6 * scale), spike_y + sh_val),
                (spike_x + int(6 * scale), spike_y + sh_val),
            ]
            spike_c = (0, max(0, min(255, int(150 * pulse))), 0)
            pygame.draw.polygon(surface, spike_c, spike_pts)

        # 主体 (脉动)
        body_r = int(sz * scale * pulse)
        body_color = (0, max(0, min(255, int(color[1] * pulse))),
                      max(0, min(255, int(color[2] // 2))))
        if body_r > 0:
            pygame.draw.circle(surface, body_color, (sx, sy), body_r)
            pygame.draw.circle(surface, (0, 200, 0), (sx, sy), body_r, max(1, int(3 * scale)))

        # 眼睛 (一只大眼)
        eye_r = int(sz // 3 * scale)
        if eye_r > 1:
            eye_y = int(sy - sz * 0.15 * scale)
            pygame.draw.circle(surface, (200, 255, 0), (sx, eye_y), eye_r)
            pygame.draw.circle(surface, BLACK, (sx, eye_y), eye_r // 2)
            # 瞳孔跟踪玩家
            if _player:
                dx = _player.x - sx
                dy = _player.y - sy
                d = max(1, math.hypot(dx, dy))
                po = eye_r // 3
                px = sx + int(dx / d * po)
                py = eye_y + int(dy / d * po)
                pygame.draw.circle(surface, BLACK, (px, py), eye_r // 3)
            # 眼睛光泽
            pygame.draw.circle(surface, WHITE, (sx - eye_r // 3, eye_y - eye_r // 3),
                               max(1, eye_r // 5))

        # 毒液滴
        for dx, dy, _, _, dl, ml in self.droplets:
            if dl <= 0:
                continue
            drip_a = max(0, min(255, int(200 * (dl / ml))))
            drip_r = max(1, int(4 * scale * (dl / ml)))
            drip_x = int(sx + dx * scale)
            drip_y = int(sy + dy * scale + sz * 0.5 * scale)
            ds = pygame.Surface((drip_r * 2 + 2, drip_r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(ds, (0, 255, 0, drip_a), (drip_r + 1, drip_r + 1), drip_r)
            surface.blit(ds, (drip_x - drip_r - 1, drip_y - drip_r - 1))

    def _get_bullet_color(self):
        return (100, 255, 100)


# ============================================================
#  Boss类型3: 烈焰魔将 (扇形弹幕 + 冲锋)
# ============================================================
class FlameGeneral(BossBase):
    BOSS_NAME = "烈焰魔将"
    BOSS_TITLE = "战场霸主"
    ENTRANCE_DURATION = 6.0
    ENTRANCE_WARN_END = 1.0
    ENTRANCE_SLIDE_END = 4.5
    ENTRANCE_READY_END = 6.0

    def _get_entrance_color(self):
        return ORANGE

    def __init__(self, x, y, boss_level=1):
        super().__init__(x, y, boss_level)
        self.charge_timer = 0
        self.charging = False
        self.charge_dir = (0, 0)
        self.charge_speed = 400
        self.flame_trail = []  # [(x, y, life)]
        # --- 独特入场状态 ---
        self._fg_pillar_height = 0
        self._fg_ring_radius = 0
        self._fg_ring_alpha = 0
        self._fg_sparks = []      # [x, y, vx, vy, life]
        self._fg_armor_prog = 0   # 盔甲成形进度
        self._fg_weapon_prog = 0  # 武器出现进度
        self._fg_shockwave_done = False

    def _calc_health(self):
        return 450 * self.boss_level

    def _calc_speed(self):
        return 40 + self.boss_level * 8  # 快

    # ---- 烈焰魔将独特入场: 火柱 → 火环 → 人形成型 → 铠甲冷却 → 兵器 → 爆发 ----
    def _update_entrance(self, dt):
        self.entrance_timer += dt
        t = self.entrance_timer
        tx, ty = self.entrance_target_x, self.entrance_target_y

        if t < self.ENTRANCE_WARN_END:  # Phase0: 警告
            self.entrance_stage = 0
            self.y = self.entrance_start_y
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
        elif t < 2.0:  # Phase1: 火柱喷发
            self.entrance_stage = 1
            prog = (t - self.ENTRANCE_WARN_END) / 1.0
            self._fg_pillar_height = min(250, int(250 * prog))
            self.x = tx
            self.y = ty
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
            if random.random() < dt * 15:
                self._fg_sparks.append([
                    tx + random.uniform(-20, 20), ty - self._fg_pillar_height * random.uniform(0.3, 1.0),
                    random.uniform(-100, 100), random.uniform(-150, -50), random.uniform(0.3, 0.8)])
            if prog > 0.5 and _screen_shake:
                _screen_shake.trigger(5, 0.1)
        elif t < 3.0:  # Phase2: 火环扩散 + 人形轮廓
            self.entrance_stage = 1
            prog = (t - 2.0) / 1.0
            self._fg_ring_radius = int(200 * prog)
            self._fg_ring_alpha = max(0, int(200 * (1 - prog)))
            self.entrance_scale = 0.3 + 0.3 * prog
            self.entrance_alpha = max(0, min(255, int(180 * prog)))
            if random.random() < dt * 10:
                a = random.uniform(0, math.pi * 2)
                self._fg_sparks.append([
                    tx + math.cos(a) * self._fg_ring_radius * 0.5, ty + math.sin(a) * self._fg_ring_radius * 0.5,
                    math.cos(a) * 80, math.sin(a) * 80 - 50, random.uniform(0.3, 0.6)])
        elif t < 4.0:  # Phase3: 铠甲成型
            self.entrance_stage = 2
            prog = (t - 3.0) / 1.0
            self._fg_armor_prog = prog
            self.entrance_scale = 0.6 + 0.3 * prog
            self.entrance_alpha = max(0, min(255, int(180 + 75 * prog)))
        elif t < 4.5:  # Phase4: 兵器出现
            self.entrance_stage = 2
            prog = (t - 4.0) / 0.5
            self._fg_weapon_prog = prog
            self._fg_armor_prog = 1.0
            self.entrance_scale = 0.9 + 0.1 * prog
            self.entrance_alpha = 255
        elif t < self.ENTRANCE_READY_END:  # Phase5: 火焰爆发冲击波
            self.entrance_scale = 1.0
            self.entrance_alpha = 255
            if not self._fg_shockwave_done:
                self._fg_shockwave_done = True
                self._shockwave_radius = 0
                self._shockwave_alpha = 255
                if _screen_shake: _screen_shake.trigger(20, 0.5)
                if _play_sfx: _play_sfx('boss_roar')
                self.roar_played = True
                if _create_particles: _create_particles(self.x, self.y, 50, 'boss_death')
            self._shockwave_radius += 450 * dt
            self._shockwave_alpha = max(0, self._shockwave_alpha - 300 * dt)
        else:
            self.entrance_active = False
            self.entrance_stage = 3
            self.y = ty
            self.entrance_scale = 1.0
            self.entrance_alpha = 255

        for s in self._fg_sparks:
            s[0] += s[2] * dt; s[1] += s[3] * dt; s[3] += 100 * dt; s[4] -= dt * 2
        self._fg_sparks = [s for s in self._fg_sparks if s[4] > 0]

    def _draw_entrance_scene(self, surface, shake, sx, sy, color):
        t = self.entrance_timer
        sh = shake
        sw_w, sw_h = WIDTH, HEIGHT
        tx = int(self.entrance_target_x + sh[0])
        ty_s = int(self.entrance_target_y + sh[1])

        if self.entrance_stage == 0:
            dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
            dark.fill((0, 0, 0, max(0, min(200, int(180 * min(1, t / 0.5))))))
            surface.blit(dark, (0, 0))
            if math.sin(t * 12) > 0:
                ss = pygame.Surface((sw_w, 60), pygame.SRCALPHA); ss.fill((200, 80, 0, 140))
                surface.blit(ss, (0, sw_h // 2 - 30))
            if math.sin(t * 8) > -0.3 and _font_sm:
                wt = _render_outlined(_font_sm, "\u2622 WARNING \u2622", ORANGE)
                surface.blit(wt, (sw_w // 2 - wt.get_width() // 2, sw_h // 2 - 60))
                nt = _render_outlined(_font_sm, f"{self.display_title} - {self.display_name}", ORANGE)
                surface.blit(nt, (sw_w // 2 - nt.get_width() // 2, sw_h // 2 + 10))
            return

        # Phase 1+:
        prog_t = min(1.0, (t - self.ENTRANCE_WARN_END) / 3.0)
        dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
        dark.fill((0, 0, 0, max(0, min(200, int(160 * (1 - prog_t * 0.7))))))
        surface.blit(dark, (0, 0))
        # 火柱
        if self._fg_pillar_height > 5:
            pw = max(1, int(40 + 15 * math.sin(t * 8)))
            ph = self._fg_pillar_height
            psurf = pygame.Surface((pw + 10, ph + 10), pygame.SRCALPHA)
            # 外层火焰 (橙)
            pygame.draw.rect(psurf, (255, 120, 0, 180), (2, 5, pw + 6, ph))
            # 内层火焰 (黄)
            iw = max(1, pw - 10)
            pygame.draw.rect(psurf, (255, 220, 50, 200), (7, 5, iw, ph))
            # 核心 (白)
            cw = max(1, iw - 10)
            if cw > 0:
                pygame.draw.rect(psurf, (255, 255, 200, 150), (12, 10, cw, ph - 10))
            surface.blit(psurf, (tx - pw // 2 - 5, ty_s - ph - 5))
        # 火环
        if self._fg_ring_radius > 5 and self._fg_ring_alpha > 0:
            rr = self._fg_ring_radius
            rsf = pygame.Surface((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(rsf, (255, 150, 0, max(0, min(255, self._fg_ring_alpha))), (rr + 2, rr + 2), rr, max(2, rr // 6))
            surface.blit(rsf, (tx - rr - 2, ty_s - rr - 2))
        # 火花粒子
        for sx2, sy2, _, _, sl in self._fg_sparks:
            if sl > 0:
                pa = max(0, min(255, int(255 * sl)))
                pr = max(1, int(5 * sl))
                cs = random.choice([(255, 200, 50, pa), (255, 120, 0, pa), (255, 80, 0, pa)])
                psf = pygame.Surface((pr * 2 + 2, pr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(psf, cs, (pr + 1, pr + 1), pr)
                surface.blit(psf, (int(sx2 + sh[0]) - pr - 1, int(sy2 + sh[1]) - pr - 1))
        # 光环
        if self.entrance_scale > 0.1:
            gs = int(self.size * 4 * self.entrance_scale)
            if gs > 0:
                gsf = pygame.Surface((gs, gs), pygame.SRCALPHA)
                pulse = 0.5 + 0.5 * math.sin(t * 7)
                pygame.draw.circle(gsf, (255, 150, 0, max(0, min(80, int(80 * pulse)))), (gs // 2, gs // 2), gs // 2)
                surface.blit(gsf, (sx - gs // 2, sy - gs // 2))
        # Boss本体
        if self.entrance_alpha > 10:
            self._draw_body(surface, sx, sy, color)
        # 冲击波
        if self._shockwave_radius > 0 and self._shockwave_alpha > 0:
            sr = int(self._shockwave_radius); sa = max(0, min(255, int(self._shockwave_alpha)))
            if sr > 3:
                rs = pygame.Surface((sr * 2 + 4, sr * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(rs, (255, 150, 0, sa), (sr + 2, sr + 2), sr, max(2, sr // 8))
                surface.blit(rs, (sx - sr - 2, sy - sr - 2))
        # 标题
        if 1.5 < t < 5.0 and _font_sm:
            ta = max(0, min(255, int(255 * min(1, (t - 1.5) / 1.0))))
            if t > 4.5: ta = max(0, min(255, int(255 * (5.0 - t) / 0.5)))
            nt = _render_outlined(_font_sm, self.display_title, ORANGE); nt.set_alpha(ta)
            surface.blit(nt, (sw_w // 2 - nt.get_width() // 2, int(sw_h * 0.28)))
            bn = _render_outlined(_font_sm, self.display_name, WHITE); bn.set_alpha(ta)
            surface.blit(bn, (sw_w // 2 - bn.get_width() // 2, int(sw_h * 0.28) + 35))

    def _do_attack(self, dt):
        """扇形弹幕 + 偶尔冲锋"""
        if _player and random.random() < 0.3 and not self.charging:
            # 冲锋
            self.charging = True
            self.charge_timer = 0.8
            dx = _player.x - self.x
            dy = _player.y - self.y
            d = max(1, math.hypot(dx, dy))
            self.charge_dir = (dx / d, dy / d)
            if _play_sfx:
                _play_sfx('boss_roar')
            if _screen_shake:
                _screen_shake.trigger(8, 0.3)
        else:
            # 扇形弹幕朝玩家方向
            if _player:
                base_angle = math.atan2(_player.y - self.y, _player.x - self.x)
            else:
                base_angle = self.color_cycle
            spread = math.pi / 3  # 60度扇形
            count = 5 + self.boss_level * 2 + self.phase * 2
            for i in range(count):
                angle = base_angle - spread / 2 + (spread / max(1, count - 1)) * i
                speed = 180 + self.phase * 40
                bvx = math.cos(angle) * speed
                bvy = math.sin(angle) * speed
                self.boss_bullets.append([self.x, self.y, bvx, bvy, 2.5])

            if _screen_shake:
                _screen_shake.trigger(5, 0.15)
            if _play_sfx:
                _play_sfx('explosion')

    def update(self, dt, game_time):
        # 入场动画期间跳过冲锋逻辑
        if self.entrance_active:
            super().update(dt, game_time)
            return
        # 冲锋逻辑
        if self.charging:
            self.charge_timer -= dt
            self.x += self.charge_dir[0] * self.charge_speed * dt
            self.y += self.charge_dir[1] * self.charge_speed * dt
            # 火焰轨迹
            self.flame_trail.append([self.x, self.y, 1.0])
            if self.charge_timer <= 0:
                self.charging = False
                if _screen_shake:
                    _screen_shake.trigger(10, 0.2)

        # 更新火焰轨迹
        for ft in self.flame_trail:
            ft[2] -= dt * 2
            # 火焰伤害玩家
            if _player:
                fd = math.hypot(ft[0] - _player.x, ft[1] - _player.y)
                if fd < 20 and ft[2] > 0:
                    _player.take_damage(self.damage * 0.3 * dt)
        self.flame_trail = [ft for ft in self.flame_trail if ft[2] > 0]

        super().update(dt, game_time)

    def _draw_body(self, surface, sx, sy, color):
        # 火焰轨迹
        for fx, fy, fl in self.flame_trail:
            fsx = int(fx)
            fsy = int(fy)
            alpha = max(0, min(255, int(fl * 200)))
            size = max(1, int(10 * fl))
            fs = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(fs, (255, 100, 0, alpha), (size, size), size)
            surface.blit(fs, (fsx - size, fsy - size))

        # 主体 (橙红色调)
        body_color = (max(0, min(255, int(color[0]))), max(0, min(255, int(color[1]) // 3)), 0)
        pygame.draw.circle(surface, body_color, (sx, sy), self.size)

        # 盔甲纹路
        armor_color = (200, 150, 50)
        pygame.draw.circle(surface, armor_color, (sx, sy), self.size, 4)
        # 十字线条
        pygame.draw.line(surface, armor_color, (sx - self.size, sy), (sx + self.size, sy), 2)
        pygame.draw.line(surface, armor_color, (sx, sy - self.size), (sx, sy + self.size), 2)

        # 眼睛 (燃烧的眼)
        eye_r = self.size // 5
        for ex_offset in [-self.size // 3, self.size // 3]:
            # 外焰
            pygame.draw.circle(surface, ORANGE, (sx + ex_offset, sy - self.size // 5), eye_r + 2)
            # 内焰
            pygame.draw.circle(surface, YELLOW, (sx + ex_offset, sy - self.size // 5), eye_r)
            # 瞳孔
            pygame.draw.circle(surface, RED, (sx + ex_offset, sy - self.size // 5), eye_r // 2)

        # 冲锋指示
        if self.charging:
            indicator = pygame.Surface((self.size * 3, self.size * 3), pygame.SRCALPHA)
            pygame.draw.circle(indicator, (255, 50, 0, 60), (self.size * 3 // 2, self.size * 3 // 2), self.size * 3 // 2)
            surface.blit(indicator, (sx - self.size * 3 // 2, sy - self.size * 3 // 2))

    def _get_bullet_color(self):
        return ORANGE


# ============================================================
#  Boss类型4: 虚空之眼 (追踪弹 + 时停)
# ============================================================
class VoidEye(BossBase):
    BOSS_NAME = "虚空之眼"
    BOSS_TITLE = "次元裂隙"
    ENTRANCE_DURATION = 6.5
    ENTRANCE_WARN_END = 1.0
    ENTRANCE_SLIDE_END = 5.0
    ENTRANCE_READY_END = 6.5

    def _get_entrance_color(self):
        return PURPLE

    def __init__(self, x, y, boss_level=1):
        super().__init__(x, y, boss_level)
        self.iris_angle = 0
        self.ring_angles = [0, 0, 0]  # 三层旋转环
        # --- 独特入场状态 ---
        self._ve_rift_width = 0    # 裂隙宽度
        self._ve_rift_height = 0   # 裂隙高度
        self._ve_energy_pts = []   # 能量粒子 [x, y, vx, vy, life]
        self._ve_eye_emerge = 0    # 眼球浮现进度 0~1
        self._ve_tentacles = []    # 触手 [angle, length, wave_phase]
        self._ve_shockwave_done = False

    def _calc_health(self):
        return 550 * self.boss_level

    def _calc_speed(self):
        return 20 + self.boss_level * 4  # 慢速飘浮

    # ---- 虚空之眼独特入场: 次元裂缝 → 裂缝扩大 → 眼球浮现 → 触手伸展 → 裂隙闭合 ----
    def _update_entrance(self, dt):
        self.entrance_timer += dt
        t = self.entrance_timer
        tx, ty = self.entrance_target_x, self.entrance_target_y

        if t < self.ENTRANCE_WARN_END:  # Phase0: 警告
            self.entrance_stage = 0
            self.y = self.entrance_start_y
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
            self._ve_rift_width = min(5, t / self.ENTRANCE_WARN_END * 5)
            self._ve_rift_height = min(20, t / self.ENTRANCE_WARN_END * 20)
        elif t < 2.5:  # Phase1: 裂缝扩大 + 紫色能量喷涌
            self.entrance_stage = 1
            prog = (t - self.ENTRANCE_WARN_END) / 1.5
            ease = 1 - (1 - prog) ** 2
            self._ve_rift_width = 5 + 80 * ease
            self._ve_rift_height = 20 + 150 * ease
            self.x = tx
            self.y = ty
            self.entrance_scale = 0.0
            self.entrance_alpha = 0
            if random.random() < dt * 12:
                a = random.uniform(-math.pi, math.pi)
                d = random.uniform(0, self._ve_rift_width * 0.5)
                self._ve_energy_pts.append([
                    tx + math.cos(a) * d, ty + math.sin(a) * self._ve_rift_height * 0.3,
                    random.uniform(-60, 60), random.uniform(-100, -30), random.uniform(0.4, 1.0)])
        elif t < 4.0:  # Phase2: 眼球从裂缝深处浮现
            self.entrance_stage = 1
            prog = (t - 2.5) / 1.5
            ease = 1 - (1 - prog) ** 3
            self._ve_eye_emerge = ease
            self._ve_rift_width = 85 - 30 * ease  # 裂缝略微收缩
            self.entrance_scale = 0.2 + 0.6 * ease
            self.entrance_alpha = max(0, min(255, int(220 * ease)))
            # 生成触手
            if len(self._ve_tentacles) < 6 and random.random() < dt * 4:
                self._ve_tentacles.append([random.uniform(0, math.pi * 2), 0, random.uniform(0, math.pi * 2)])
        elif t < 5.0:  # Phase3: 触手伸展 + 旋转环形成
            self.entrance_stage = 2
            prog = (t - 4.0) / 1.0
            self._ve_eye_emerge = 1.0
            self.entrance_scale = 0.8 + 0.2 * prog
            self.entrance_alpha = max(0, min(255, int(220 + 35 * prog)))
            self._ve_rift_width = max(10, 55 - 45 * prog)
            for ten in self._ve_tentacles:
                ten[1] = min(self.size * 1.5, ten[1] + 80 * dt)
        elif t < self.ENTRANCE_READY_END:  # Phase4: 裂隙闭合+冲击波
            self.entrance_scale = 1.0
            self.entrance_alpha = 255
            self._ve_rift_width = max(0, self._ve_rift_width - 50 * dt)
            if not self._ve_shockwave_done:
                self._ve_shockwave_done = True
                self._shockwave_radius = 0
                self._shockwave_alpha = 255
                if _screen_shake: _screen_shake.trigger(16, 0.5)
                if _play_sfx: _play_sfx('boss_roar')
                self.roar_played = True
                if _create_particles: _create_particles(self.x, self.y, 40, 'boss_death')
            self._shockwave_radius += 380 * dt
            self._shockwave_alpha = max(0, self._shockwave_alpha - 280 * dt)
        else:
            self.entrance_active = False
            self.entrance_stage = 3
            self.y = ty
            self.entrance_scale = 1.0
            self.entrance_alpha = 255

        for ep in self._ve_energy_pts:
            ep[0] += ep[2] * dt; ep[1] += ep[3] * dt; ep[4] -= dt
        self._ve_energy_pts = [e for e in self._ve_energy_pts if e[4] > 0]
        for ten in self._ve_tentacles:
            ten[2] += dt * 3

    def _draw_entrance_scene(self, surface, shake, sx, sy, color):
        t = self.entrance_timer
        sh = shake
        sw_w, sw_h = WIDTH, HEIGHT
        tx = int(self.entrance_target_x + sh[0])
        ty_s = int(self.entrance_target_y + sh[1])

        if self.entrance_stage == 0:
            dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
            dark.fill((0, 0, 0, max(0, min(200, int(180 * min(1, t / 0.5))))))
            surface.blit(dark, (0, 0))
            if math.sin(t * 10) > 0:
                ss = pygame.Surface((sw_w, 60), pygame.SRCALPHA); ss.fill((100, 0, 200, 120))
                surface.blit(ss, (0, sw_h // 2 - 30))
            if math.sin(t * 8) > -0.3 and _font_sm:
                wt = _render_outlined(_font_sm, "\u25C6 WARNING \u25C6", PURPLE)
                surface.blit(wt, (sw_w // 2 - wt.get_width() // 2, sw_h // 2 - 60))
                nt = _render_outlined(_font_sm, f"{self.display_title} - {self.display_name}", PURPLE)
                surface.blit(nt, (sw_w // 2 - nt.get_width() // 2, sw_h // 2 + 10))
            # 小裂缝预兆
            if self._ve_rift_width > 1:
                rw = int(self._ve_rift_width); rh = int(self._ve_rift_height)
                if rw > 0 and rh > 0:
                    rsf = pygame.Surface((rw * 2 + 4, rh * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.ellipse(rsf, (100, 0, 200, 120), (0, 0, rw * 2 + 4, rh * 2 + 4))
                    surface.blit(rsf, (tx - rw - 2, ty_s - rh - 2))
            return

        # Phase 1+:
        prog_t = min(1.0, (t - self.ENTRANCE_WARN_END) / 3.0)
        dark = pygame.Surface((sw_w, sw_h), pygame.SRCALPHA)
        dark.fill((0, 0, 0, max(0, min(200, int(160 * (1 - prog_t * 0.6))))))
        surface.blit(dark, (0, 0))
        # 次元裂缝
        rw = max(1, int(self._ve_rift_width)); rh = max(1, int(self._ve_rift_height))
        if rw > 0 and rh > 0:
            rsf = pygame.Surface((rw * 2 + 20, rh * 2 + 20), pygame.SRCALPHA)
            cx, cy = rw + 10, rh + 10
            # 外层光芒
            pygame.draw.ellipse(rsf, (170, 68, 255, 60), (0, 0, rw * 2 + 20, rh * 2 + 20))
            # 裂缝本体 (深紫)
            pygame.draw.ellipse(rsf, (40, 0, 80, 200), (10, 10, rw * 2, rh * 2))
            # 边缘脉动
            edge_a = max(0, min(255, int(150 + 60 * math.sin(t * 5))))
            pygame.draw.ellipse(rsf, (170, 68, 255, edge_a), (10, 10, rw * 2, rh * 2), max(1, int(3 + 2 * math.sin(t * 4))))
            surface.blit(rsf, (tx - rw - 10, ty_s - rh - 10))
        # 能量粒子
        for ex, ey, _, _, el in self._ve_energy_pts:
            if el > 0:
                pa = max(0, min(255, int(255 * el)))
                pr = max(1, int(4 * el))
                psf = pygame.Surface((pr * 2 + 2, pr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(psf, (200, 100, 255, pa), (pr + 1, pr + 1), pr)
                surface.blit(psf, (int(ex + sh[0]) - pr - 1, int(ey + sh[1]) - pr - 1))
        # 触手 (从裂缝中伸出)
        for ta, tl, tw in self._ve_tentacles:
            if tl > 0:
                segs = 5
                prev = (tx, ty_s)
                for j in range(1, segs + 1):
                    frac = j / segs
                    wave = math.sin(tw + frac * 3) * 12 * frac
                    nx = tx + int(math.cos(ta) * tl * frac + wave * math.sin(ta))
                    ny = ty_s + int(math.sin(ta) * tl * frac + wave * math.cos(ta))
                    w = max(1, int((5 - j) * self.entrance_scale))
                    pygame.draw.line(surface, (150, 50, 220), prev, (nx, ny), w)
                    prev = (nx, ny)
                pygame.draw.circle(surface, (200, 80, 255), prev, max(1, int(3 * self.entrance_scale)))
        # 光环
        if self.entrance_scale > 0.1:
            gs = int(self.size * 4 * self.entrance_scale)
            if gs > 0:
                gsf = pygame.Surface((gs, gs), pygame.SRCALPHA)
                pulse = 0.5 + 0.5 * math.sin(t * 6)
                pygame.draw.circle(gsf, (170, 68, 255, max(0, min(60, int(60 * pulse)))), (gs // 2, gs // 2), gs // 2)
                surface.blit(gsf, (sx - gs // 2, sy - gs // 2))
        # Boss本体
        if self.entrance_alpha > 10:
            self._draw_body(surface, sx, sy, color)
        # 冲击波
        if self._shockwave_radius > 0 and self._shockwave_alpha > 0:
            sr = int(self._shockwave_radius); sa = max(0, min(255, int(self._shockwave_alpha)))
            if sr > 3:
                rs = pygame.Surface((sr * 2 + 4, sr * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(rs, (170, 68, 255, sa), (sr + 2, sr + 2), sr, max(2, sr // 8))
                surface.blit(rs, (sx - sr - 2, sy - sr - 2))
        # 标题
        if 1.5 < t < 5.5 and _font_sm:
            ta2 = max(0, min(255, int(255 * min(1, (t - 1.5) / 1.5))))
            if t > 5.0: ta2 = max(0, min(255, int(255 * (5.5 - t) / 0.5)))
            nt = _render_outlined(_font_sm, self.display_title, PURPLE); nt.set_alpha(ta2)
            surface.blit(nt, (sw_w // 2 - nt.get_width() // 2, int(sw_h * 0.28)))
            bn = _render_outlined(_font_sm, self.display_name, WHITE); bn.set_alpha(ta2)
            surface.blit(bn, (sw_w // 2 - bn.get_width() // 2, int(sw_h * 0.28) + 35))

    def _do_attack(self, dt):
        """追踪弹 - 子弹会缓慢追踪玩家"""
        count = 4 + self.boss_level + self.phase * 2
        for i in range(count):
            angle = (2 * math.pi / count) * i + self.color_cycle
            speed = 100
            bvx = math.cos(angle) * speed
            bvy = math.sin(angle) * speed
            # 追踪弹用额外数据标记 [x, y, vx, vy, life, is_tracking]
            self.boss_bullets.append([self.x, self.y, bvx, bvy, 4.0])

        if _screen_shake:
            _screen_shake.trigger(4, 0.15)
        if _play_sfx:
            _play_sfx('explosion')

    def update(self, dt, game_time):
        # 入场动画期间跳过追踪逻辑
        if self.entrance_active:
            super().update(dt, game_time)
            return
        # 让弹幕有轻微追踪效果
        if _player:
            for b in self.boss_bullets:
                dx = _player.x - b[0]
                dy = _player.y - b[1]
                d = max(1, math.hypot(dx, dy))
                # 轻微转向
                tracking_force = 30 + self.phase * 15
                b[2] += (dx / d) * tracking_force * dt
                b[3] += (dy / d) * tracking_force * dt
                # 限速
                spd = math.hypot(b[2], b[3])
                max_spd = 180
                if spd > max_spd:
                    b[2] = b[2] / spd * max_spd
                    b[3] = b[3] / spd * max_spd

        # 旋转环
        for i in range(len(self.ring_angles)):
            self.ring_angles[i] += (1.5 + i * 0.5) * dt * (1 if i % 2 == 0 else -1)

        super().update(dt, game_time)

    def _draw_body(self, surface, sx, sy, color):
        # 旋转环
        ring_colors = [(100, 0, 200), (150, 0, 255), (80, 0, 180)]
        for i, (ra, rc) in enumerate(zip(self.ring_angles, ring_colors)):
            ring_r = self.size + 10 + i * 12
            ring_surf = pygame.Surface((ring_r * 2 + 10, ring_r * 2 + 10), pygame.SRCALPHA)
            center = (ring_r + 5, ring_r + 5)
            # 环上的节点
            nodes = 4 + i * 2
            for j in range(nodes):
                na = ra + (2 * math.pi / nodes) * j
                nx = center[0] + int(math.cos(na) * ring_r)
                ny = center[1] + int(math.sin(na) * ring_r)
                pygame.draw.circle(ring_surf, (*rc, 180), (nx, ny), 4)
            # 环线
            pygame.draw.circle(ring_surf, (*rc, 60), center, ring_r, 2)
            surface.blit(ring_surf, (sx - ring_r - 5, sy - ring_r - 5))

        # 主体 (紫色漩涡)
        body_color = (max(0, min(255, int(color[0]) // 2)),
                      0,
                      max(0, min(255, int(color[2]))))
        pygame.draw.circle(surface, body_color, (sx, sy), self.size)
        pygame.draw.circle(surface, PURPLE, (sx, sy), self.size, 3)

        # 大眼睛 (占据整个身体)
        eye_r = self.size * 3 // 4
        # 眼白
        pygame.draw.circle(surface, (220, 200, 255), (sx, sy), eye_r)
        # 虹膜
        iris_r = eye_r * 2 // 3
        self.iris_angle += 0.03
        ix = sx + int(math.cos(self.iris_angle) * eye_r // 6)
        iy = sy + int(math.sin(self.iris_angle) * eye_r // 6)
        pygame.draw.circle(surface, PURPLE, (ix, iy), iris_r)
        # 瞳孔
        pygame.draw.circle(surface, BLACK, (ix, iy), iris_r // 2)
        # 高光
        pygame.draw.circle(surface, WHITE, (ix - iris_r // 3, iy - iris_r // 3), iris_r // 5)

    def _get_bullet_color(self):
        return PURPLE


# ============================================================
#  Boss工厂 - 根据等级创建不同Boss
# ============================================================
BOSS_TYPES = [SkullKing, VenomBeast, FlameGeneral, VoidEye]

def create_boss(x, y, boss_level=1):
    """根据boss_level创建对应类型的Boss，循环使用不同类型"""
    type_idx = (boss_level - 1) % len(BOSS_TYPES)
    boss_type = BOSS_TYPES[type_idx]
    boss = boss_type(x, y, boss_level)
    boss.boss_type = type_idx  # 用于图鉴系统识别Boss类型
    return boss

def get_boss_preview_name(boss_level):
    """获取即将出现的Boss名称（用于警告显示）"""
    boss_type = BOSS_TYPES[(boss_level - 1) % len(BOSS_TYPES)]
    return f"{i18n.t(boss_type.BOSS_TITLE)} {i18n.t(boss_type.BOSS_NAME)}"


# ============================================================
#  独立测试模式
# ============================================================
if __name__ == '__main__':
    import sys
    import os
    import array

    pygame.init()
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

    WIDTH, HEIGHT = 1200, 800
    DARK_BG = (15, 15, 25)
    GRID_COLOR = (30, 30, 45)

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Boss 测试场")
    clock = pygame.time.Clock()

    # 字体
    font_path = 'C:/Windows/Fonts/msyh.ttc'
    font_lg = pygame.font.Font(font_path, 36)
    font_sm = pygame.font.Font(font_path, 22)
    font_xs = pygame.font.Font(font_path, 16)

    # ---- 简易音效系统 ----
    sfx_cache = {}
    def make_beep(freq=440, duration=0.1, volume=0.3):
        sr = 22050
        n = int(sr * duration)
        buf = array.array('h', [0] * n)
        for i in range(n):
            t = i / sr
            v = math.sin(2 * math.pi * freq * t) * volume * 32767
            env = min(1.0, (n - i) / (n * 0.3))
            buf[i] = max(-32767, min(32767, int(v * env)))
        snd = pygame.mixer.Sound(buffer=buf)
        return snd

    sfx_cache['hit'] = make_beep(600, 0.05, 0.2)
    sfx_cache['shoot'] = make_beep(800, 0.04, 0.15)
    sfx_cache['boss_roar'] = make_beep(120, 0.3, 0.4)
    sfx_cache['explosion'] = make_beep(200, 0.15, 0.3)

    def play_sfx(name):
        snd = sfx_cache.get(name)
        if snd:
            snd.play()

    # ---- 简易屏幕震动 ----
    class ScreenShake:
        def __init__(self):
            self.intensity = 0
            self.timer = 0
            self.offset = [0, 0]
        def trigger(self, intensity, duration):
            self.intensity = max(self.intensity, intensity)
            self.timer = max(self.timer, duration)
        def update(self, dt):
            if self.timer > 0:
                self.timer -= dt
                self.offset[0] = random.uniform(-self.intensity, self.intensity)
                self.offset[1] = random.uniform(-self.intensity, self.intensity)
                self.intensity *= 0.92
            else:
                self.offset = [0, 0]
                self.intensity = 0
    shake = ScreenShake()

    # ---- 简易粒子系统 ----
    class Particle:
        def __init__(self, x, y, vx, vy, color, life=1.0, size=4):
            self.x, self.y = x, y
            self.vx, self.vy = vx, vy
            self.color = color
            self.life = life
            self.max_life = life
            self.size = size
        def update(self, dt):
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.vy += 200 * dt
            self.life -= dt
        def draw(self, surface, sh):
            if self.life <= 0:
                return
            a = max(0, min(255, int(255 * self.life / self.max_life)))
            r = max(1, int(self.size * self.life / self.max_life))
            sx = int(self.x + sh[0])
            sy = int(self.y + sh[1])
            ps = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            c = (*self.color[:3], a)
            pygame.draw.circle(ps, c, (r + 1, r + 1), r)
            surface.blit(ps, (sx - r - 1, sy - r - 1))

    particles = []
    def create_particles(x, y, count, effect_type='default'):
        colors = {
            'default': [WHITE, CYAN, YELLOW],
            'explosion': [ORANGE, YELLOW, RED],
            'boss_death': [PINK, PURPLE, RED, ORANGE, YELLOW],
        }
        palette = colors.get(effect_type, colors['default'])
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(50, 250)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            c = random.choice(palette)
            life = random.uniform(0.4, 1.2)
            size = random.uniform(2, 6)
            particles.append(Particle(x, y, vx, vy, c, life, size))

    # ---- 测试用玩家 ----
    class TestPlayer:
        def __init__(self):
            self.x = WIDTH // 2
            self.y = HEIGHT // 2
            self.health = 999
            self.max_health = 999
            self.weapons = {
                'gun': {'level': 3, 'max_level': 5, 'ultimate': False},
                'sword': {'level': 3, 'max_level': 5, 'ultimate': False},
            }
            self.invincible_timer = 0
        def take_damage(self, amount):
            if self.invincible_timer > 0:
                return
            self.health -= amount
            self.invincible_timer = 0.1
        def update(self, dt):
            if self.invincible_timer > 0:
                self.invincible_timer -= dt
        def draw(self, surface, sh):
            sx = int(self.x + sh[0])
            sy = int(self.y + sh[1])
            pygame.draw.circle(surface, CYAN, (sx, sy), 22)
            pygame.draw.circle(surface, WHITE, (sx, sy), 22, 3)
            pygame.draw.circle(surface, WHITE, (sx, sy), 8)

    test_player = TestPlayer()

    # ---- 模拟光剑 ----
    test_swords = []
    def get_swords():
        return test_swords

    # ---- 子弹 ----
    test_bullets = []
    class TestBullet:
        def __init__(self, x, y, angle, speed=500, damage=30):
            self.x, self.y = x, y
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            self.life = 2.5
            self.damage = damage
            self.hit = False
        def update(self, dt, bosses):
            if self.hit:
                return
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.life -= dt
            for boss in bosses:
                if self.hit or not boss.alive:
                    continue
                d = math.hypot(boss.x - self.x, boss.y - self.y)
                if d < boss.size + 8:
                    boss.health -= self.damage
                    boss.flash_timer = 0.1
                    create_particles(self.x, self.y, 10, 'explosion')
                    shake.trigger(4, 0.1)
                    play_sfx('hit')
                    self.hit = True
                    self.life = 0
                    if d > 0:
                        boss.x += (boss.x - self.x) / d * 30
                        boss.y += (boss.y - self.y) / d * 30
        def draw(self, surface, sh):
            if self.hit:
                return
            sx = int(self.x + sh[0])
            sy = int(self.y + sh[1])
            pygame.draw.circle(surface, YELLOW, (sx, sy), 4)
            ex = sx - int(self.vx * 0.03)
            ey = sy - int(self.vy * 0.03)
            pygame.draw.line(surface, ORANGE, (sx, sy), (ex, ey), 3)

    # ---- 初始化 Boss 模块 ----
    init(test_player, get_swords, shake, create_particles, play_sfx, font_sm, font_xs, WIDTH, HEIGHT)

    # ---- 状态 ----
    current_boss_level = 1
    bosses_list = [create_boss(WIDTH // 2, 150, current_boss_level)]
    game_time = 0.0
    bg_offset = [0.0, 0.0]
    auto_shoot_timer = 0
    paused = False

    # ---- 主循环 ----
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.033)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # 数字键切换Boss
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    current_boss_level = event.key - pygame.K_0
                    bosses_list = [create_boss(WIDTH // 2, 150, current_boss_level)]
                    test_player.health = test_player.max_health
                    test_bullets.clear()
                    particles.clear()

                # N键 下一个Boss等级
                if event.key == pygame.K_n:
                    current_boss_level += 1
                    bosses_list = [create_boss(WIDTH // 2, 150, current_boss_level)]
                    test_player.health = test_player.max_health
                    test_bullets.clear()
                    particles.clear()

                # R键 重置当前Boss
                if event.key == pygame.K_r:
                    bosses_list = [create_boss(WIDTH // 2, 150, current_boss_level)]
                    test_player.health = test_player.max_health
                    test_bullets.clear()
                    particles.clear()

                # P键 暂停
                if event.key == pygame.K_p:
                    paused = not paused

                # H键 恢复满血
                if event.key == pygame.K_h:
                    test_player.health = test_player.max_health

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                angle = math.atan2(mouse_pos[1] - test_player.y, mouse_pos[0] - test_player.x)
                spread = math.pi / 6
                for i in range(3):
                    offset = (i - 1) * spread / 2
                    test_bullets.append(TestBullet(test_player.x, test_player.y, angle + offset, 500, 50))
                play_sfx('shoot')
                create_particles(test_player.x, test_player.y, 5, 'explosion')

        if paused:
            # 暂停画面
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            pt = _render_outlined(font_lg, "已暂停 (P键继续)", WHITE)
            screen.blit(pt, (WIDTH // 2 - pt.get_width() // 2, HEIGHT // 2 - 30))
            pygame.display.flip()
            continue

        game_time += dt

        # 玩家移动
        keys = pygame.key.get_pressed()
        move_speed = 300
        mx_move, my_move = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    my_move = move_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:   my_move = -move_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:   mx_move = move_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  mx_move = -move_speed
        if mx_move and my_move:
            mx_move *= 0.707; my_move *= 0.707
        bg_offset[0] += mx_move * dt
        bg_offset[1] += my_move * dt
        for boss in bosses_list:
            boss.x += mx_move * dt
            boss.y += my_move * dt
            for bb in boss.boss_bullets:
                bb[0] += mx_move * dt
                bb[1] += my_move * dt
        for b in test_bullets:
            b.x += mx_move * dt
            b.y += my_move * dt

        # 光剑
        test_swords.clear()
        sword_count = test_player.weapons.get('sword', {}).get('level', 0)
        for i in range(sword_count):
            angle = game_time * 3 + i * math.pi * 2 / sword_count
            test_swords.append((
                test_player.x + math.cos(angle) * 35,
                test_player.y + math.sin(angle) * 35,
                angle
            ))

        # 自动射击
        auto_shoot_timer -= dt
        if auto_shoot_timer <= 0 and bosses_list and bosses_list[0].alive:
            boss = bosses_list[0]
            angle = math.atan2(boss.y - test_player.y, boss.x - test_player.x)
            test_bullets.append(TestBullet(test_player.x, test_player.y, angle, 500, 30))
            auto_shoot_timer = 0.3

        # 更新
        test_player.update(dt)
        shake.update(dt)
        for boss in bosses_list:
            boss.update(dt, game_time)
        for b in test_bullets:
            b.update(dt, bosses_list)
        test_bullets = [b for b in test_bullets if b.life > 0]
        for p in particles:
            p.update(dt)
        particles = [p for p in particles if p.life > 0]

        # Boss死亡 → 自动下一个
        for boss in bosses_list:
            if not boss.alive:
                create_particles(boss.x, boss.y, 80, 'boss_death')
                shake.trigger(20, 0.5)
        bosses_list = [b for b in bosses_list if b.alive]
        if not bosses_list:
            current_boss_level += 1
            bosses_list = [create_boss(WIDTH // 2, 150, current_boss_level)]
            test_player.health = test_player.max_health

        # ---- 绘制 ----
        sh = shake.offset
        screen.fill(DARK_BG)

        # 网格
        grid = 60
        ox = int(bg_offset[0] % grid + sh[0])
        oy = int(bg_offset[1] % grid + sh[1])
        for x in range(ox, WIDTH + grid, grid):
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
        for y in range(oy, HEIGHT + grid, grid):
            pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y), 1)

        # 光剑
        for sx, sy, sa in test_swords:
            dx, dy = int(sx + sh[0]), int(sy + sh[1])
            pygame.draw.circle(screen, CYAN, (dx, dy), 18, 5)
            pygame.draw.circle(screen, (68, 255, 255), (dx, dy), 12)

        # 子弹
        for b in test_bullets:
            b.draw(screen, sh)

        # 玩家
        test_player.draw(screen, sh)

        # Boss
        for boss in bosses_list:
            boss.draw(screen, sh)

        # 粒子
        for p in particles:
            p.draw(screen, sh)

        # ---- HUD ----
        # 操作说明
        panel = pygame.Surface((300, 220), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 180), (0, 0, 300, 220), border_radius=10)
        screen.blit(panel, (WIDTH - 310, HEIGHT - 230))

        helps = [
            i18n.t("--- Boss 测试场 ---"),
            i18n.t("WASD / 方向键 : 移动"),
            i18n.t("鼠标点击 : 散弹射击"),
            i18n.t("1-4 : 切换Boss类型"),
            i18n.t("N : 下一级Boss"),
            i18n.t("R : 重置当前Boss"),
            i18n.t("H : 恢复满血"),
            i18n.t("P : 暂停"),
            i18n.t("ESC : 退出"),
        ]
        for i, h in enumerate(helps):
            color = YELLOW if i == 0 else (200, 200, 200)
            ht = _render_outlined(font_xs, h, color)
            screen.blit(ht, (WIDTH - 300, HEIGHT - 222 + i * 24))

        # Boss信息
        if bosses_list:
            boss = bosses_list[0]
            info_panel = pygame.Surface((280, 100), pygame.SRCALPHA)
            pygame.draw.rect(info_panel, (0, 0, 0, 180), (0, 0, 280, 100), border_radius=10)
            screen.blit(info_panel, (10, HEIGHT - 110))

            boss_type_name = type(boss).__name__
            infos = [
                f"类型: {boss.display_title} {boss.display_name} ({boss_type_name})",
                f"等级: Lv.{boss.boss_level}  阶段: {boss.phase}",
                f"血量: {int(boss.health)}/{boss.max_health}",
                f"玩家血量: {int(test_player.health)}/{test_player.max_health}",
            ]
            for i, info in enumerate(infos):
                it = _render_outlined(font_xs, info, WHITE)
                screen.blit(it, (20, HEIGHT - 105 + i * 24))

        pygame.display.flip()

    pygame.quit()
    sys.exit()
