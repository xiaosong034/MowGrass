"""
角色模块 - 割草游戏可选角色系统
每个角色拥有独特的外观、属性和被动技能
"""

import pygame
import math
import random
import i18n

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

# ============================================================
#  常量
# ============================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 68, 68)
PINK = (255, 100, 200)
CYAN = (78, 205, 196)
YELLOW = (255, 255, 0)
ORANGE = (255, 170, 0)
PURPLE = (170, 68, 255)
GREEN = (68, 255, 68)

# ============================================================
#  角色基类
# ============================================================
class CharacterBase:
    """所有角色的基类"""
    CHAR_NAME = "角色"
    CHAR_TITLE = ""
    CHAR_COLOR = CYAN
    CHAR_DESC = ""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        # 基础属性
        self.max_health = self._base_health()
        self.health = self.max_health
        self.move_speed = self._base_speed()
        self.pickup_range = self._base_pickup()
        self.armor = self._base_armor()
        self.dodge_rate = self._base_dodge()
        self.regen = self._base_regen()
        self.crit_rate = self._base_crit()
        self.crit_damage = 1.5
        self.damage_bonus = 0.0
        self.cooldown_reduction = 0.0
        # 战斗状态
        self.invincible_timer = 0
        self.weapons = {
            'gun': {'level': 1, 'max_level': 5, 'ultimate': False},
            'sword': {'level': 1, 'max_level': 5, 'ultimate': False},
        }
        # 动画
        self.anim_timer = 0
        self.facing_angle = 0  # 朝向
        self.dash_trail = []   # 冲刺残影 [x, y, alpha]
        self._passive_timer = 0
        self._passive_active = False

    # ---- 显示属性 (用于UI显示翻译后的文本) ----
    @property
    def display_name(self):
        """返回翻译后的角色名称"""
        return i18n.t(self.CHAR_NAME)

    @property
    def display_title(self):
        """返回翻译后的角色称号"""
        return i18n.t(self.CHAR_TITLE)

    @property
    def display_desc(self):
        """返回翻译后的角色描述"""
        return i18n.t(self.CHAR_DESC)

    # ---- 基础属性 (子类覆盖) ----
    def _base_health(self): return 100
    def _base_speed(self): return 300
    def _base_pickup(self): return 80
    def _base_armor(self): return 0
    def _base_dodge(self): return 0.0
    def _base_regen(self): return 0.0
    def _base_crit(self): return 0.05

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return False
        # 闪避判定
        if random.random() < self.dodge_rate:
            return False  # 闪避成功
        actual = max(1, amount - self.armor)
        self.health -= actual
        self.invincible_timer = 0.15
        self._on_hit(actual)
        return True

    def _on_hit(self, damage):
        """受击时触发的被动 (子类覆盖)"""
        pass

    def _on_kill(self):
        """击杀时触发的被动 (子类覆盖)"""
        pass

    def update(self, dt):
        self.anim_timer += dt
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
        if self.regen > 0:
            self.health = min(self.max_health, self.health + self.regen * dt)
        self._passive_timer += dt
        # 冲刺残影衰减
        for t in self.dash_trail:
            t[2] -= dt * 400
        self.dash_trail = [t for t in self.dash_trail if t[2] > 0]
        self._update_passive(dt)

    def _update_passive(self, dt):
        """更新被动技能 (子类覆盖)"""
        pass

    def draw(self, surface, shake):
        sx = int(self.x + shake[0])
        sy = int(self.y + shake[1])
        # 残影
        for tx, ty, ta in self.dash_trail:
            tsx = int(tx + shake[0])
            tsy = int(ty + shake[1])
            a = max(0, min(255, int(ta)))
            ts = pygame.Surface((44, 44), pygame.SRCALPHA)
            self._draw_body_on(ts, 22, 22, a)
            surface.blit(ts, (tsx - 22, tsy - 22))
        # 绘制本体
        self._draw_character(surface, sx, sy)

    def _draw_body_on(self, surface, sx, sy, alpha):
        """在Surface上绘制角色简化版 (用于残影)"""
        c = (*self.CHAR_COLOR, alpha)
        pygame.draw.circle(surface, c, (sx, sy), 18)

    def _draw_character(self, surface, sx, sy):
        """绘制角色完整外观 (子类覆盖)"""
        pygame.draw.circle(surface, self.CHAR_COLOR, (sx, sy), 20)
        pygame.draw.circle(surface, WHITE, (sx, sy), 20, 3)

    def get_stats_dict(self):
        """返回属性字典 (用于UI显示)"""
        return {
            i18n.t('生命'): f'{int(self.health)}/{self.max_health}',
            i18n.t('速度'): f'{self.move_speed:.0f}',
            i18n.t('拾取'): f'{self.pickup_range:.0f}',
            i18n.t('护甲'): f'{self.armor}',
            i18n.t('闪避'): f'{self.dodge_rate*100:.0f}%',
            i18n.t('回血'): f'{self.regen:.1f}/s',
            i18n.t('暴击'): f'{self.crit_rate*100:.0f}%',
        }


# ============================================================
#  角色1: 守墓人·阿什 [初始角色 - 均衡型]
# ============================================================
class GravekeeperAsh(CharacterBase):
    CHAR_NAME = "阿什"
    CHAR_TITLE = "守墓人"
    CHAR_COLOR = CYAN
    CHAR_DESC = "均衡型角色 · 被动: 击杀敌人5%概率回复少量生命"

    def _base_health(self): return 100
    def _base_speed(self): return 300
    def _base_pickup(self): return 80
    def _base_armor(self): return 2
    def _base_crit(self): return 0.05

    def _on_kill(self):
        if random.random() < 0.05:
            self.health = min(self.max_health, self.health + 5)

    def _draw_character(self, surface, sx, sy):
        # 斗篷 (深青色)
        cloak_pts = [
            (sx, sy - 16),
            (sx - 18, sy + 12),
            (sx + 18, sy + 12),
        ]
        pygame.draw.polygon(surface, (30, 120, 110), cloak_pts)
        # 身体
        pygame.draw.circle(surface, self.CHAR_COLOR, (sx, sy), 16)
        pygame.draw.circle(surface, WHITE, (sx, sy), 16, 2)
        # 头部
        head_y = sy - 12
        pygame.draw.circle(surface, (200, 220, 220), (sx, head_y), 9)
        # 眼睛
        pygame.draw.circle(surface, WHITE, (sx - 3, head_y - 1), 3)
        pygame.draw.circle(surface, WHITE, (sx + 3, head_y - 1), 3)
        pygame.draw.circle(surface, BLACK, (sx - 3, head_y - 1), 1)
        pygame.draw.circle(surface, BLACK, (sx + 3, head_y - 1), 1)
        # 铲子 (背后)
        shovel_x = sx + 14
        pygame.draw.line(surface, (139, 90, 43), (shovel_x, sy - 18), (shovel_x, sy + 8), 3)
        pygame.draw.rect(surface, (100, 100, 100), (shovel_x - 4, sy - 22, 8, 6))

    def _draw_body_on(self, surface, sx, sy, alpha):
        c = (78, 205, 196, alpha)
        pygame.draw.circle(surface, c, (sx, sy), 16)


# ============================================================
#  角色2: 暗影刺客·莉拉 [高速低血]
# ============================================================
class ShadowAssassinLila(CharacterBase):
    CHAR_NAME = "莉拉"
    CHAR_TITLE = "暗影刺客"
    CHAR_COLOR = PURPLE
    CHAR_DESC = "高速型角色 · 被动: 闪避成功后0.5秒内移速+80%"

    def _base_health(self): return 70
    def _base_speed(self): return 380
    def _base_pickup(self): return 70
    def _base_dodge(self): return 0.10
    def _base_crit(self): return 0.10

    def __init__(self, x, y):
        super().__init__(x, y)
        self._shadow_boost_timer = 0
        self._original_speed = self.move_speed

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return False
        if random.random() < self.dodge_rate:
            # 闪避成功 → 触发加速
            self._shadow_boost_timer = 0.5
            self.move_speed = self._original_speed * 1.8
            return False
        actual = max(1, amount - self.armor)
        self.health -= actual
        self.invincible_timer = 0.1
        return True

    def _update_passive(self, dt):
        if self._shadow_boost_timer > 0:
            self._shadow_boost_timer -= dt
            if self._shadow_boost_timer <= 0:
                self.move_speed = self._original_speed
                self._shadow_boost_timer = 0

    def _draw_character(self, surface, sx, sy):
        # 暗影残影效果
        if self._shadow_boost_timer > 0:
            for i in range(3):
                a = max(0, min(120, int(80 - i * 25)))
                offset = (i + 1) * 6
                ss = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(ss, (170, 68, 255, a), (20, 20), 14)
                surface.blit(ss, (sx - 20 - offset, sy - 20))
        # 身体 (紫色 + 尖锐轮廓)
        body_pts = [
            (sx, sy - 18),   # 头顶
            (sx - 14, sy),   # 左
            (sx - 8, sy + 14),  # 左下
            (sx + 8, sy + 14),  # 右下
            (sx + 14, sy),   # 右
        ]
        pygame.draw.polygon(surface, (100, 30, 160), body_pts)
        pygame.draw.polygon(surface, PURPLE, body_pts, 2)
        # 头部
        pygame.draw.circle(surface, (180, 160, 200), (sx, sy - 10), 8)
        # 面具
        mask_pts = [(sx - 6, sy - 13), (sx + 6, sy - 13), (sx + 4, sy - 7), (sx - 4, sy - 7)]
        pygame.draw.polygon(surface, (60, 0, 100), mask_pts)
        # 红色眼睛
        pygame.draw.circle(surface, RED, (sx - 3, sy - 11), 2)
        pygame.draw.circle(surface, RED, (sx + 3, sy - 11), 2)
        # 匕首
        blade_x = sx + 16
        pygame.draw.line(surface, (200, 200, 220), (blade_x, sy - 8), (blade_x, sy + 5), 2)
        pygame.draw.circle(surface, (200, 200, 220), (blade_x, sy - 10), 2)


# ============================================================
#  角色3: 铁壁骑士·加隆 [高血高甲低速]
# ============================================================
class IronKnightGaron(CharacterBase):
    CHAR_NAME = "加隆"
    CHAR_TITLE = "铁壁骑士"
    CHAR_COLOR = (100, 150, 200)
    CHAR_DESC = "防御型角色 · 被动: 血量低于30%时护甲翻倍"

    def _base_health(self): return 150
    def _base_speed(self): return 220
    def _base_pickup(self): return 60
    def _base_armor(self): return 5
    def _base_regen(self): return 0.5

    def __init__(self, x, y):
        super().__init__(x, y)
        self._base_armor_val = self.armor
        self._fortified = False

    def _update_passive(self, dt):
        if self.health / self.max_health < 0.3:
            if not self._fortified:
                self._fortified = True
                self.armor = self._base_armor_val * 2
        else:
            if self._fortified:
                self._fortified = False
                self.armor = self._base_armor_val

    def _draw_character(self, surface, sx, sy):
        # 盾牌 (左侧)
        shield_x = sx - 16
        shield_pts = [
            (shield_x, sy - 14),
            (shield_x - 8, sy - 8),
            (shield_x - 8, sy + 6),
            (shield_x, sy + 14),
            (shield_x + 8, sy + 6),
            (shield_x + 8, sy - 8),
        ]
        pygame.draw.polygon(surface, (60, 80, 120), shield_pts)
        pygame.draw.polygon(surface, (100, 150, 200), shield_pts, 2)
        # 盾十字
        pygame.draw.line(surface, (200, 200, 220), (shield_x, sy - 8), (shield_x, sy + 8), 2)
        pygame.draw.line(surface, (200, 200, 220), (shield_x - 5, sy), (shield_x + 5, sy), 2)
        # 铠甲身体
        pygame.draw.circle(surface, (80, 110, 160), (sx, sy), 16)
        pygame.draw.circle(surface, (120, 160, 200), (sx, sy), 16, 3)
        # 头盔
        head_y = sy - 12
        pygame.draw.circle(surface, (100, 120, 150), (sx, head_y), 10)
        # 头盔面罩
        pygame.draw.rect(surface, (60, 80, 100), (sx - 6, head_y - 3, 12, 8))
        # 眼缝
        pygame.draw.line(surface, (200, 220, 255), (sx - 4, head_y), (sx + 4, head_y), 2)
        # 强化指示
        if self._fortified:
            fs = pygame.Surface((48, 48), pygame.SRCALPHA)
            pa = max(0, min(120, int(80 + 40 * math.sin(self.anim_timer * 5))))
            pygame.draw.circle(fs, (100, 150, 255, pa), (24, 24), 24, 3)
            surface.blit(fs, (sx - 24, sy - 24))


# ============================================================
#  角色4: 炼金术士·菲奥 [高伤低闪避]
# ============================================================
class AlchemistFio(CharacterBase):
    CHAR_NAME = "菲奥"
    CHAR_TITLE = "炼金术士"
    CHAR_COLOR = ORANGE
    CHAR_DESC = "伤害型角色 · 被动: 武器进化所需等级-2，暴击伤害+30%"

    def _base_health(self): return 85
    def _base_speed(self): return 280
    def _base_crit(self): return 0.08

    def __init__(self, x, y):
        super().__init__(x, y)
        self.crit_damage = 1.8  # +30%暴击伤害
        self.damage_bonus = 0.10  # 基础伤害加成
        self._potion_timer = 0
        self._potion_bubbles = []

    def _update_passive(self, dt):
        self._potion_timer += dt
        if random.random() < dt * 2:
            self._potion_bubbles.append([
                random.uniform(-8, 8), 0, random.uniform(-15, 15),
                random.uniform(-40, -20), random.uniform(0.3, 0.8)])
        for b in self._potion_bubbles:
            b[0] += b[2] * dt; b[1] += b[3] * dt; b[4] -= dt
        self._potion_bubbles = [b for b in self._potion_bubbles if b[4] > 0]

    def _draw_character(self, surface, sx, sy):
        # 药水气泡
        for dx, dy, _, _, bl in self._potion_bubbles:
            if bl > 0:
                pa = max(0, min(200, int(200 * bl)))
                pr = max(1, int(3 * bl))
                bsf = pygame.Surface((pr * 2 + 2, pr * 2 + 2), pygame.SRCALPHA)
                col = random.choice([(255, 200, 50, pa), (255, 100, 0, pa), (100, 255, 100, pa)])
                pygame.draw.circle(bsf, col, (pr + 1, pr + 1), pr)
                surface.blit(bsf, (sx + int(dx) - pr, sy + int(dy) - 20 - pr))
        # 长袍
        robe_pts = [(sx, sy - 14), (sx - 16, sy + 14), (sx + 16, sy + 14)]
        pygame.draw.polygon(surface, (120, 70, 20), robe_pts)
        # 身体
        pygame.draw.circle(surface, (180, 120, 50), (sx, sy), 13)
        pygame.draw.circle(surface, ORANGE, (sx, sy), 13, 2)
        # 头部
        head_y = sy - 10
        pygame.draw.circle(surface, (220, 200, 180), (sx, head_y), 8)
        # 帽子 (尖顶)
        hat_pts = [(sx - 9, head_y - 2), (sx + 9, head_y - 2), (sx + 2, head_y - 22)]
        pygame.draw.polygon(surface, (100, 50, 10), hat_pts)
        pygame.draw.polygon(surface, ORANGE, hat_pts, 2)
        # 眼睛
        pygame.draw.circle(surface, YELLOW, (sx - 3, head_y - 1), 2)
        pygame.draw.circle(surface, YELLOW, (sx + 3, head_y - 1), 2)
        pygame.draw.circle(surface, BLACK, (sx - 3, head_y - 1), 1)
        pygame.draw.circle(surface, BLACK, (sx + 3, head_y - 1), 1)
        # 药瓶 (右手)
        bottle_x = sx + 14
        pygame.draw.rect(surface, (100, 200, 100), (bottle_x - 3, sy - 4, 6, 10))
        pygame.draw.rect(surface, (80, 160, 80), (bottle_x - 3, sy - 4, 6, 10), 1)
        pygame.draw.rect(surface, (139, 90, 43), (bottle_x - 2, sy - 7, 4, 4))


# ============================================================
#  角色5: 裂隙行者·虚无 [特殊属性波动型]
# ============================================================
class RiftWalkerVoid(CharacterBase):
    CHAR_NAME = "虚无"
    CHAR_TITLE = "裂隙行者"
    CHAR_COLOR = (200, 100, 255)
    CHAR_DESC = "特殊角色 · 被动: 每30秒闪现到安全位置，属性随机波动"

    def _base_health(self): return 90
    def _base_speed(self): return 300
    def _base_pickup(self): return 100
    def _base_dodge(self): return 0.08
    def _base_crit(self): return 0.07

    def __init__(self, x, y):
        super().__init__(x, y)
        self._blink_cooldown = 30.0
        self._blink_timer = 30.0
        self._rift_particles = []
        self._phase_shift = 0

    def _update_passive(self, dt):
        self._blink_timer -= dt
        self._phase_shift += dt
        # 属性波动
        wave = math.sin(self._phase_shift * 0.5)
        self.damage_bonus = 0.05 + 0.1 * max(0, wave)
        # 裂隙粒子
        if random.random() < dt * 3:
            angle = random.uniform(0, math.pi * 2)
            self._rift_particles.append([
                math.cos(angle) * 25, math.sin(angle) * 25,
                -math.cos(angle) * 15, -math.sin(angle) * 15,
                random.uniform(0.4, 0.8)])
        for p in self._rift_particles:
            p[0] += p[2] * dt; p[1] += p[3] * dt; p[4] -= dt
        self._rift_particles = [p for p in self._rift_particles if p[4] > 0]

    def _draw_character(self, surface, sx, sy):
        # 裂隙粒子
        for dx, dy, _, _, pl in self._rift_particles:
            if pl > 0:
                pa = max(0, min(200, int(200 * pl)))
                pr = max(1, int(3 * pl))
                psf = pygame.Surface((pr * 2 + 2, pr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(psf, (200, 100, 255, pa), (pr + 1, pr + 1), pr)
                surface.blit(psf, (sx + int(dx) - pr, sy + int(dy) - pr))
        # 身体 (半透明紫色漩涡)
        body_s = pygame.Surface((40, 40), pygame.SRCALPHA)
        # 外环
        pygame.draw.circle(body_s, (100, 30, 180, 150), (20, 20), 16)
        # 漩涡线
        for i in range(3):
            a = self._phase_shift * 2 + i * math.pi * 2 / 3
            x1 = 20 + int(math.cos(a) * 8)
            y1 = 20 + int(math.sin(a) * 8)
            x2 = 20 + int(math.cos(a + 1) * 14)
            y2 = 20 + int(math.sin(a + 1) * 14)
            pygame.draw.line(body_s, (200, 130, 255, 200), (x1, y1), (x2, y2), 2)
        surface.blit(body_s, (sx - 20, sy - 20))
        # 核心
        core_a = max(0, min(255, int(180 + 60 * math.sin(self._phase_shift * 3))))
        cs = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(cs, (255, 200, 255, core_a), (10, 10), 6)
        pygame.draw.circle(cs, (255, 255, 255, max(0, core_a - 50)), (10, 10), 3)
        surface.blit(cs, (sx - 10, sy - 10))
        # 眼
        eye_a = max(0, min(255, int(200 + 55 * math.sin(self._phase_shift * 4))))
        pygame.draw.circle(surface, (255, 200, 255), (sx, sy - 8), 4)
        pygame.draw.circle(surface, (80, 0, 120), (sx, sy - 8), 2)
        # 边框
        pygame.draw.circle(surface, (200, 100, 255), (sx, sy), 16, 2)
        # 闪烁计时器指示
        if self._blink_timer < 5:
            bt_a = max(0, min(255, int(200 * (1 - self._blink_timer / 5) * abs(math.sin(self.anim_timer * 5)))))
            bts = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(bts, (200, 100, 255, bt_a), (20, 20), 20, 2)
            surface.blit(bts, (sx - 20, sy - 20))


# ============================================================
#  角色6: 死神 [隐藏角色 - 极端攻击型]
# ============================================================
class ReaperDeath(CharacterBase):
    CHAR_NAME = "死神"
    CHAR_TITLE = "???"
    CHAR_COLOR = RED
    CHAR_DESC = "隐藏角色 · 被动: 击杀后1秒内攻击+100%，但生命极低"

    def _base_health(self): return 50
    def _base_speed(self): return 320
    def _base_pickup(self): return 100
    def _base_crit(self): return 0.15

    def __init__(self, x, y):
        super().__init__(x, y)
        self.damage_bonus = 0.2
        self._harvest_timer = 0
        self._scythe_angle = 0
        self._soul_particles = []

    def _on_kill(self):
        self._harvest_timer = 1.0
        self.damage_bonus = 1.2  # 击杀后+100%

    def _update_passive(self, dt):
        self._scythe_angle += dt * 2
        if self._harvest_timer > 0:
            self._harvest_timer -= dt
            if self._harvest_timer <= 0:
                self.damage_bonus = 0.2
        # 灵魂粒子
        if random.random() < dt * 2:
            self._soul_particles.append([
                random.uniform(-20, 20), random.uniform(-20, 20),
                random.uniform(-10, 10), random.uniform(-30, -10),
                random.uniform(0.5, 1.2)])
        for p in self._soul_particles:
            p[0] += p[2] * dt; p[1] += p[3] * dt; p[4] -= dt
        self._soul_particles = [p for p in self._soul_particles if p[4] > 0]

    def _draw_character(self, surface, sx, sy):
        # 灵魂粒子
        for dx, dy, _, _, pl in self._soul_particles:
            if pl > 0:
                pa = max(0, min(150, int(150 * pl)))
                psf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(psf, (255, 50, 50, pa), (4, 4), max(1, int(3 * pl)))
                surface.blit(psf, (sx + int(dx) - 4, sy + int(dy) - 4))
        # 黑色斗篷
        cloak_pts = [
            (sx, sy - 20),
            (sx - 20, sy + 8),
            (sx - 14, sy + 16),
            (sx + 14, sy + 16),
            (sx + 20, sy + 8),
        ]
        pygame.draw.polygon(surface, (20, 0, 0), cloak_pts)
        pygame.draw.polygon(surface, (80, 0, 0), cloak_pts, 2)
        # 兜帽
        hood_pts = [(sx - 12, sy - 8), (sx + 12, sy - 8), (sx, sy - 24)]
        pygame.draw.polygon(surface, (30, 0, 0), hood_pts)
        # 红色发光眼睛
        eye_a = max(0, min(255, int(200 + 55 * math.sin(self.anim_timer * 4))))
        for ex in [-4, 4]:
            es = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(es, (255, 0, 0, eye_a), (5, 5), 3)
            pygame.draw.circle(es, (255, 100, 100, max(0, eye_a - 80)), (5, 5), 5)
            surface.blit(es, (sx + ex - 5, sy - 15))
        # 镰刀
        sa = self._scythe_angle
        blade_r = 22
        bx = sx + int(math.cos(sa) * blade_r)
        by = sy + int(math.sin(sa) * blade_r)
        blade_end_x = bx + int(math.cos(sa + 0.8) * 15)
        blade_end_y = by + int(math.sin(sa + 0.8) * 15)
        pygame.draw.line(surface, (150, 150, 160), (sx, sy), (bx, by), 3)  # 柄
        pygame.draw.line(surface, (200, 200, 210), (bx, by), (blade_end_x, blade_end_y), 2)  # 刃
        # 收割buff指示
        if self._harvest_timer > 0:
            ha = max(0, min(200, int(200 * self._harvest_timer * abs(math.sin(self.anim_timer * 8)))))
            hs = pygame.Surface((50, 50), pygame.SRCALPHA)
            pygame.draw.circle(hs, (255, 0, 0, ha), (25, 25), 25, 3)
            surface.blit(hs, (sx - 25, sy - 25))


# ============================================================
#  角色总表
# ============================================================
CHARACTER_TYPES = [
    GravekeeperAsh,
    ShadowAssassinLila,
    IronKnightGaron,
    AlchemistFio,
    RiftWalkerVoid,
    ReaperDeath,
]

def create_character(index, x, y):
    """根据索引创建角色"""
    char_type = CHARACTER_TYPES[index % len(CHARACTER_TYPES)]
    return char_type(x, y)

def get_character_count():
    return len(CHARACTER_TYPES)

def get_character_info(index):
    """返回角色预览信息"""
    ct = CHARACTER_TYPES[index % len(CHARACTER_TYPES)]
    return {
        'name': i18n.t(ct.CHAR_NAME),
        'title': i18n.t(ct.CHAR_TITLE),
        'desc': i18n.t(ct.CHAR_DESC),
        'color': ct.CHAR_COLOR,
    }


# ============================================================
#  独立测试模式
# ============================================================
if __name__ == '__main__':
    import sys
    pygame.init()
    WIDTH, HEIGHT = 1000, 700
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("角色预览 - Characters Preview")
    clock = pygame.time.Clock()
    font_path = 'C:/Windows/Fonts/msyh.ttc'
    font = pygame.font.Font(font_path, 22)
    font_sm = pygame.font.Font(font_path, 16)

    # 创建所有角色
    chars = []
    for i in range(len(CHARACTER_TYPES)):
        cx = 120 + i * 150
        cy = HEIGHT // 2
        chars.append(create_character(i, cx, cy))

    selected = 0
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.033)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    selected = (selected - 1) % len(chars)
                elif event.key == pygame.K_RIGHT:
                    selected = (selected + 1) % len(chars)

        for c in chars:
            c.update(dt)

        screen.fill((20, 20, 30))
        # 标题
        title = _render_outlined(font, "角色选择预览 (←→ 切换)", WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

        # 绘制所有角色
        for i, c in enumerate(chars):
            cx = 100 + i * 150
            cy = HEIGHT // 2 - 30
            c.x = cx
            c.y = cy

            # 选中高亮
            if i == selected:
                hs = pygame.Surface((120, 120), pygame.SRCALPHA)
                pygame.draw.rect(hs, (255, 255, 255, 30), (0, 0, 120, 120), border_radius=10)
                pygame.draw.rect(hs, (*c.CHAR_COLOR, 150), (0, 0, 120, 120), 3, border_radius=10)
                screen.blit(hs, (cx - 60, cy - 60))

            c.draw(screen, (0, 0))

            # 名称
            info = get_character_info(i)
            nt = _render_outlined(font_sm, f"{info['title']}", info['color'])
            screen.blit(nt, (cx - nt.get_width() // 2, cy + 40))
            nn = _render_outlined(font_sm, f"{info['name']}", WHITE)
            screen.blit(nn, (cx - nn.get_width() // 2, cy + 58))

        # 选中角色详情
        ch = chars[selected]
        info = get_character_info(selected)
        detail_y = HEIGHT // 2 + 100
        # 描述
        desc = _render_outlined(font_sm, info['desc'], (200, 200, 200))
        screen.blit(desc, (WIDTH // 2 - desc.get_width() // 2, detail_y))
        # 属性
        stats = ch.get_stats_dict()
        sx_start = WIDTH // 2 - 200
        for j, (k, v) in enumerate(stats.items()):
            col = j % 4
            row = j // 4
            st = _render_outlined(font_sm, f"{k}: {v}", (180, 180, 180))
            screen.blit(st, (sx_start + col * 100, detail_y + 30 + row * 22))

        pygame.display.flip()

    pygame.quit()
    sys.exit()
