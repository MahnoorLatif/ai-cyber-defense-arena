import pygame
import sys
import os
import random
import math
import numpy as np
import imageio

# Constants 
SCREEN_WIDTH   = 900
SCREEN_HEIGHT  = 600
FPS            = 60
TITLE          = "AI Cyber Defense Arena"
AGENT_X        = 550
AGENT_HALF_H   = 35
AGENT_SPEED    = 5
SERVER_X       = 780
SERVER_Y       = SCREEN_HEIGHT // 2
SPAWN_INTERVAL = 90
MAX_ATTACKERS  = 5

#Colors 
C_BG      = (5,   10,  20)
C_GRID    = (0,   30,  50)
C_BORDER  = (0,   180, 120)
C_SERVER  = (0,   255, 180)
C_AGENT   = (0,   150, 255)
C_ATK_V   = (255, 60,  60)
C_ATK_D   = (255, 140, 0)
C_ATK_M   = (200, 0,   255)
C_TEXT    = (200, 255, 240)
C_DIM     = (60,  100, 80)
C_BLOCKED = (255, 220, 0)
C_HIT     = (255, 80,  80)
C_SCAN    = (0,   255, 255)
C_HP_G    = (0,   220, 100)
C_HP_R    = (220, 50,  50)
C_HP_BG   = (20,  20,  20)


# HELPERS

def draw_glow(surf, color, pos, radius, layers=4, alpha_base=45):
    s = pygame.Surface((radius*2+60, radius*2+60), pygame.SRCALPHA)
    for i in range(layers, 0, -1):
        a = int(alpha_base * (i / layers))
        pygame.draw.circle(s, (*color[:3], a),
                           (radius+30, radius+30), radius + i*7)
    surf.blit(s, (pos[0]-radius-30, pos[1]-radius-30))

def draw_rect_glow(surf, color, rect, layers=3):
    for i in range(layers, 0, -1):
        a   = int(40 * (i / layers))
        exp = i * 5
        s   = pygame.Surface((rect.width+exp*2, rect.height+exp*2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], a),
                         (0, 0, rect.width+exp*2, rect.height+exp*2),
                         border_radius=10)
        surf.blit(s, (rect.x-exp, rect.y-exp))

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

# PARTICLES

class Particle:
    def __init__(self, x, y, color, speed=4, life=35):
        self.x    = float(x)
        self.y    = float(y)
        self.color= color
        angle     = random.uniform(0, math.tau)
        spd       = random.uniform(1, speed)
        self.vx   = math.cos(angle) * spd
        self.vy   = math.sin(angle) * spd
        self.life = random.randint(life//2, life)
        self.max_l= self.life

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.vx  *= 0.92
        self.vy  *= 0.92
        self.life-= 1

    def draw(self, surf):
        if self.life <= 0:
            return
        t    = self.life / self.max_l
        size = max(1, int(t * 5))
        s    = pygame.Surface((size*2+2, size*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], int(t*230)),
                           (size+1, size+1), size)
        surf.blit(s, (int(self.x)-size-1, int(self.y)-size-1))


class TextPopup:
    def __init__(self, x, y, text, color):
        self.x    = float(x)
        self.y    = float(y)
        self.text = text
        self.color= color
        self.life = 50
        self.max_l= 50
        self.font = pygame.font.SysFont("consolas", 16, bold=True)

    def update(self):
        self.y   -= 0.8
        self.life-= 1

    def draw(self, surf):
        if self.life <= 0:
            return
        s = self.font.render(self.text, True, self.color)
        s.set_alpha(int((self.life/self.max_l)*255))
        surf.blit(s, (int(self.x)-s.get_width()//2, int(self.y)))

# SERVER

class Server:
    def __init__(self):
        self.x        = SERVER_X
        self.y        = SERVER_Y
        self.radius   = 32
        self.max_hp   = 100
        self.hp       = 100.0
        self.hit_flash= 0
        self.pulse    = 0

    def take_damage(self, amount=10):
        self.hp        = max(0, self.hp - amount)
        self.hit_flash = 25

    def is_alive(self):
        return self.hp > 0

    def draw(self, surf, font):
        self.pulse = (self.pulse + 2) % 360
        pulse_r    = self.radius + int(math.sin(math.radians(self.pulse)) * 5)
        color      = C_HIT if self.hit_flash > 0 else C_SERVER
        if self.hit_flash > 0:
            self.hit_flash -= 1

        draw_glow(surf, color, (self.x, self.y), pulse_r, layers=5)
        pygame.draw.circle(surf, color, (self.x, self.y), self.radius)
        pygame.draw.circle(surf, (255,255,255), (self.x, self.y), self.radius, 2)

        for i in range(-12, 15, 9):
            pygame.draw.line(surf, C_BG,
                             (self.x-14, self.y+i), (self.x+14, self.y+i), 2)

        bw, bh = 74, 10
        bx     = self.x - bw//2
        by     = self.y + self.radius + 6
        ratio  = self.hp / self.max_hp
        fill   = lerp_color(C_HP_R, C_HP_G, ratio)
        pygame.draw.rect(surf, C_HP_BG, (bx, by, bw, bh))
        pygame.draw.rect(surf, fill,    (bx, by, int(bw*ratio), bh))
        pygame.draw.rect(surf, C_TEXT,  (bx, by, bw, bh), 1)

        lbl = font.render("SERVER", True, color)
        surf.blit(lbl, (self.x - lbl.get_width()//2, by + bh + 4))

# AGENT

class Agent:
    def __init__(self):
        self.x          = AGENT_X
        self.y          = float(SCREEN_HEIGHT // 2)
        self.w          = 30
        self.h          = AGENT_HALF_H * 2
        self.speed      = AGENT_SPEED
        self.score      = 0
        self.blocks     = 0
        self.misses     = 0
        self.scan_ring  = 0
        self.shield_glow= 0
        self.action_text= ""
        self.action_life= 0

    def move_up(self):
        self.y = max(self.h//2 + 60, self.y - self.speed)

    def move_down(self):
        self.y = min(SCREEN_HEIGHT - self.h//2 - 20, self.y + self.speed)

    def get_rect(self):
        return pygame.Rect(self.x - self.w//2,
                           int(self.y) - self.h//2,
                           self.w, self.h)

    def on_block(self):
        self.score      += 10
        self.blocks     += 1
        self.scan_ring   = 8
        self.shield_glow = 30
        self.action_text = "+10  BLOCKED"
        self.action_life = 55

    def on_miss(self):
        self.misses     += 1
        self.score      -= 5
        self.action_text = "-5  MISSED"
        self.action_life = 55

    def draw(self, surf, font):
        rect = self.get_rect()
        cx   = self.x
        cy   = int(self.y)

        if self.scan_ring > 0:
            r = (8 - self.scan_ring) * 22
            pygame.draw.circle(surf, C_SCAN, (cx, cy), max(1,int(r)), 2)
            self.scan_ring -= 0.3

        if self.shield_glow > 0:
            draw_rect_glow(surf, C_SCAN, rect, layers=4)
            self.shield_glow -= 1

        draw_rect_glow(surf, C_AGENT, rect, layers=3)
        pygame.draw.rect(surf, C_AGENT, rect, border_radius=8)
        pygame.draw.rect(surf, (255,255,255), rect, 2, border_radius=8)

        for i in range(4):
            ly = rect.top + 8 + i*14
            pygame.draw.line(surf, (0,60,120),
                             (rect.left+4, ly), (rect.right-4, ly), 1)

        pts = [(cx, cy-16),(cx-9, cy-4),(cx-9, cy+6),
               (cx, cy+14),(cx+9, cy+6),(cx+9, cy-4)]
        pygame.draw.polygon(surf, (255,255,255), pts, 2)

        lbl = font.render("FIREWALL", True, C_AGENT)
        surf.blit(lbl, (cx - lbl.get_width()//2, rect.bottom + 6))

        if self.action_life > 0:
            t     = self.action_life / 55
            color = C_BLOCKED if "BLOCKED" in self.action_text else C_HIT
            af    = pygame.font.SysFont("consolas", 15, bold=True)
            s     = af.render(self.action_text, True, color)
            s.set_alpha(int(t*255))
            surf.blit(s, (cx - s.get_width()//2, rect.top - 30))
            self.action_life -= 1

# ATTACKER

class Attacker:
    TYPES = [
        {"name":"VIRUS",   "color":C_ATK_V, "sm":1.0, "dmg":10, "sz":13},
        {"name":"DDOS",    "color":C_ATK_D, "sm":1.5, "dmg":7,  "sz":10},
        {"name":"MALWARE", "color":C_ATK_M, "sm":0.8, "dmg":15, "sz":16},
    ]

    def __init__(self):
        t          = random.choice(self.TYPES)
        self.name  = t["name"]
        self.color = t["color"]
        self.dmg   = t["dmg"]
        self.sz    = t["sz"]
        self.x     = float(random.randint(-80, -20))
        self.y     = float(random.randint(80, SCREEN_HEIGHT-80))
        self.speed = random.uniform(2, 4) * t["sm"]
        self.active= True
        self.angle = random.uniform(0, 360)
        self.trail : list = []

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)
        self.x    += self.speed
        self.angle = (self.angle + 4) % 360

    def get_rect(self):
        return pygame.Rect(self.x-self.sz, self.y-self.sz,
                           self.sz*2, self.sz*2)

    def draw(self, surf):
        if not self.active:
            return
        cx, cy, s = int(self.x), int(self.y), self.sz

        for i, (tx, ty) in enumerate(self.trail):
            t  = i / max(1, len(self.trail))
            ts = pygame.Surface((s*2, s*2), pygame.SRCALPHA)
            pygame.draw.circle(ts, (*self.color[:3], int(t*80)),
                               (s, s), max(1, int(s*t)))
            surf.blit(ts, (int(tx)-s, int(ty)-s))

        draw_glow(surf, self.color, (cx, cy), s, layers=2, alpha_base=35)

        pts = []
        for i in range(6):
            a = math.radians(self.angle + i*60)
            pts.append((cx + s*math.cos(a), cy + s*math.sin(a)))
        pygame.draw.polygon(surf, self.color, pts)
        pygame.draw.polygon(surf, (255,255,255), pts, 1)

        pygame.draw.line(surf, (255,255,255), (cx-s//2,cy), (cx+s//2,cy), 1)
        pygame.draw.line(surf, (255,255,255), (cx,cy-s//2), (cx,cy+s//2), 1)

        fn  = pygame.font.SysFont("consolas", 10)
        lbl = fn.render(self.name, True, self.color)
        surf.blit(lbl, (cx - lbl.get_width()//2, cy + s + 3))

# BACKGROUND & HUD

def draw_background(surf, scan_y):
    surf.fill(C_BG)
    for x in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(surf, C_GRID, (x, 0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(surf, C_GRID, (0, y), (SCREEN_WIDTH, y))
    sl = pygame.Surface((SCREEN_WIDTH, 3), pygame.SRCALPHA)
    sl.fill((0, 255, 200, 35))
    surf.blit(sl, (0, scan_y))
    pygame.draw.rect(surf, C_BORDER, (0,0,SCREEN_WIDTH,SCREEN_HEIGHT), 3)
    for y in range(0, SCREEN_HEIGHT, 15):
        pygame.draw.line(surf, (0,80,80), (AGENT_X, y), (AGENT_X, y+8), 1)


def draw_attack_vectors(surf, attackers):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for att in attackers:
        if att.active:
            # Fixed visible alpha — always draw the line clearly
            alpha = 60
            # Draw dashed line from attacker toward server
            x1, y1 = int(att.x), int(att.y)
            x2, y2 = SERVER_X, SERVER_Y
            # Draw full line
            pygame.draw.line(overlay, (*att.color[:3], alpha),
                             (x1, y1), (x2, y2), 1)
            # Draw brighter dot at attacker end for emphasis
            pygame.draw.circle(overlay, (*att.color[:3], 80),
                                (x1, y1), 3)
    surf.blit(overlay, (0,0))


def draw_hud(surf, agent, server, font_l, font_s, ai_mode,
             gif_recording, gif_frames_count, gif_max):
    title = font_l.render("AI CYBER DEFENSE ARENA", True, C_TEXT)
    surf.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 10))

    badge = font_s.render("[ AI MODE ]" if ai_mode else "[ MANUAL ]",
                           True, (0,255,150) if ai_mode else (255,200,0))
    surf.blit(badge, (SCREEN_WIDTH//2 - badge.get_width()//2, 40))

    # GIF recording indicator
    if gif_recording and gif_max == -1 and gif_frames_count > 0:
        # Blinking red dot effect
        import time
        blink = int(time.time() * 2) % 2 == 0
        col   = (220, 50, 50) if blink else (120, 20, 20)
        rec   = font_s.render(
            f"● REC  {gif_frames_count} frames  (~{gif_frames_count//20}s)",
            True, col)
        surf.blit(rec, (SCREEN_WIDTH//2 - rec.get_width()//2, 68))
    elif gif_max != -1 and gif_frames_count >= gif_max:
        done = font_s.render("● GIF SAVED ✓", True, C_HP_G)
        surf.blit(done, (SCREEN_WIDTH//2 - done.get_width()//2, 68))

    # Stats
    total = max(1, agent.blocks + agent.misses)
    acc   = agent.blocks / total * 100
    for i,(txt,col) in enumerate([
        (f"SCORE  : {agent.score}",  C_AGENT),
        (f"BLOCKS : {agent.blocks}", C_HP_G),
        (f"MISSES : {agent.misses}", C_HIT),
        (f"ACC    : {acc:.0f}%",     C_TEXT),
    ]):
        surf.blit(font_s.render(txt, True, col), (18, 95 + i*26))

    hp_col = lerp_color(C_HP_R, C_HP_G, server.hp/100)
    hp_s   = font_s.render(f"SERVER HP: {int(server.hp)}%", True, hp_col)
    surf.blit(hp_s, (SCREEN_WIDTH - hp_s.get_width() - 18, 95))

    hint = font_s.render(
        "[ AI AGENT ACTIVE ]  [ ESC ] Quit" if ai_mode
        else "[ ↑ ↓ ] Move   [ ESC ] Quit", True, C_DIM)
    surf.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT-26))

def draw_end_screen(surf, font_l, font_s, agent, won=False):
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((0,0,0,190))
    surf.blit(ov, (0,0))
    msg   = "MISSION COMPLETE" if won else "SERVER BREACHED"
    color = C_HP_G if won else C_HIT
    t     = font_l.render(msg, True, color)
    surf.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, SCREEN_HEIGHT//2-80))
    total = max(1, agent.blocks + agent.misses)
    for i, line in enumerate([
        f"Score: {agent.score}",
        f"Blocks: {agent.blocks}   Misses: {agent.misses}",
        f"Accuracy: {agent.blocks/total*100:.1f}%",
        "", "[ R ] Restart    [ ESC ] Quit"
    ]):
        s = font_s.render(line, True, C_TEXT)
        surf.blit(s, (SCREEN_WIDTH//2 - s.get_width()//2,
                      SCREEN_HEIGHT//2 - 20 + i*30))

# AI OBSERVATION
def build_obs(agent, server, attackers):
    obs = np.full(3 + MAX_ATTACKERS*2, -1.0, dtype=np.float32)
    obs[0] = agent.y / SCREEN_HEIGHT
    obs[1] = server.hp / 100.0
    obs[2] = len(attackers) / MAX_ATTACKERS
    for i, att in enumerate(
            sorted(attackers, key=lambda a: abs(a.x-AGENT_X))[:MAX_ATTACKERS]):
        obs[3 + i*2]     = att.x / SCREEN_WIDTH
        obs[3 + i*2 + 1] = att.y / SCREEN_HEIGHT
    return obs

# MAIN GAME LOOP

def run_game(ai_mode=False):
    pygame.init()
    screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock   = pygame.time.Clock()
    font_l  = pygame.font.SysFont("consolas", 24, bold=True)
    font_s  = pygame.font.SysFont("consolas", 15)

    # Load AI model 
    ai_model = None
    if ai_mode:
        from stable_baselines3 import PPO
        for p in ["models/cyber_defense_ppo.zip",
                  "models/best_model/best_model.zip"]:
            if os.path.exists(p):
                ai_model = PPO.load(p)
                print(f"✅ Loaded: {p}")
                break
        if ai_model is None:
            print("⚠️  No model found — manual mode.")
            ai_mode = False

    #GIF setup
    os.makedirs("recordings", exist_ok=True)
    gif_frames    = []
    RECORD_GIF    = ai_mode          # only auto-record in AI mode
    GIF_FPS       = 20
    #GIF_SECONDS   = 10               # record 10 seconds
    GIF_EVERY     = max(1, FPS // GIF_FPS)
    #GIF_MAX       = GIF_SECONDS * GIF_FPS
    gif_saved     = False

    # Game objects
    server    = Server()
    agent     = Agent()
    attackers : list[Attacker] = []
    particles : list[Particle] = []
    popups    : list[TextPopup]= []
    frame     = 0
    scan_y    = 0
    game_over = False
    won       = False
    WIN_SCORE = 300

    running = True
    while running:
        frame  += 1
        scan_y  = (scan_y + 1) % SCREEN_HEIGHT

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r and game_over:
                    pygame.quit()
                    return run_game(ai_mode)
                # Manual GIF trigger with G key
                if event.key == pygame.K_g and not ai_mode:
                    RECORD_GIF = True
                    gif_frames = []
                    gif_saved  = False
                    print("  🔴 Manual GIF recording started (10 sec)...")

        # Movement 
        if not game_over:
            if ai_mode and ai_model:
                obs    = build_obs(agent, server, attackers)
                action, _ = ai_model.predict(obs, deterministic=True)
                if   action == 0: agent.move_up()
                elif action == 1: agent.move_down()
            else:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]:   agent.move_up()
                if keys[pygame.K_DOWN]: agent.move_down()

        # Spawn attackers 
        if not game_over and frame % SPAWN_INTERVAL == 0:
            for _ in range(random.randint(1, 2)):
                attackers.append(Attacker())

        # Update attackers 
        if not game_over:
            alive = []
            for att in attackers:
                att.update()
                if agent.get_rect().colliderect(att.get_rect()):
                    att.active = False
                    agent.on_block()
                    for _ in range(22):
                        particles.append(Particle(att.x, att.y, att.color))
                    particles.append(Particle(att.x, att.y, (255,255,255)))
                    popups.append(TextPopup(att.x, att.y-20, "+10", C_BLOCKED))
                elif att.x >= SERVER_X - 42:
                    att.active = False
                    server.take_damage(att.dmg)
                    agent.on_miss()
                    for _ in range(14):
                        particles.append(Particle(SERVER_X, SERVER_Y, C_HIT))
                    popups.append(TextPopup(SERVER_X, SERVER_Y-40,
                                            f"-{att.dmg} HP", C_HIT))
                else:
                    alive.append(att)
            attackers = alive

        # Update particles & popups 
        for p in particles: p.update()
        particles = [p for p in particles if p.life > 0]
        for p in popups:    p.update()
        popups    = [p for p in popups    if p.life > 0]

        # Win / Lose 
        
        if not game_over:
            if not server.is_alive():
                game_over, won = True, False
            elif agent.score >= WIN_SCORE:
                game_over, won = True, True

        #Save GIF the moment game ends 
        if game_over and RECORD_GIF and not gif_saved and gif_frames:
            # Capture 3 extra seconds of end screen
            pass  # handled below after end screen draws

        #Draw everything 
        draw_background(screen, scan_y)
        draw_attack_vectors(screen, attackers)
        for p in particles:  p.draw(screen)
        server.draw(screen, font_s)
        agent.draw(screen,  font_s)
        for att in attackers: att.draw(screen)
        for pop in popups:    pop.draw(screen)

        draw_hud(screen, agent, server, font_l, font_s,
                 ai_mode, RECORD_GIF, len(gif_frames), -1)

        if game_over:
            draw_end_screen(screen, font_l, font_s, agent, won)

        pygame.display.flip()
        clock.tick(FPS)

        # GIF capture every Nth frame 
        if RECORD_GIF and not gif_saved:
            if frame % GIF_EVERY == 0:
                raw = pygame.surfarray.array3d(screen)
                gif_frames.append(np.transpose(raw, (1, 0, 2)))

        #Save GIF after end screen shown for 3 seconds
        if game_over and RECORD_GIF and not gif_saved and gif_frames:
            # Keep rendering end screen for 3 more seconds (180 frames)
            end_frames_needed = 3 * GIF_FPS   # 60 extra GIF frames
            # Count how many end-screen frames we've added
            if not hasattr(run_game, '_end_frame_count'):
                run_game._end_frame_count = 0
            run_game._end_frame_count += 1

            if run_game._end_frame_count >= end_frames_needed * GIF_EVERY:
                run_game._end_frame_count = 0   # reset for next run
                path = "recordings/cyber_defense_demo.gif"
                print(f"\n  💾 Saving full session GIF")
                print(f"  📊 Total frames : {len(gif_frames)}")
                print(f"  ⏱️  Duration     : ~{len(gif_frames)//GIF_FPS}s")
                print(f"  💾 Saving to    : {path}")
                print(f"  ⏳ Please wait...")
                imageio.mimsave(path, gif_frames, fps=GIF_FPS, loop=0)
                print(f"  ✅ GIF saved → {path}")
                gif_saved = True

    pygame.quit()
    sys.exit()

# ENTRY POINT

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "manual"
    run_game(ai_mode=(mode == "ai"))