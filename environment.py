import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random

# Constants 
SCREEN_WIDTH    = 900
SCREEN_HEIGHT   = 600
AGENT_X         = 550
AGENT_HALF_H    = 35       # half height of agent rectangle
SERVER_X        = 780
MAX_ATTACKERS   = 5        # max attackers tracked in state
AGENT_SPEED     = 5
ATTACKER_SPEED_MIN = 2
ATTACKER_SPEED_MAX = 4
SPAWN_EVERY     = 60       # frames between spawns
MAX_STEPS       = 2000     # max steps per episode

# ATTACKER (internal simulation — no Pygame needed here)

class SimAttacker:
    """
    Lightweight attacker used inside the RL environment.
    No Pygame drawing — pure logic only.
    """
    TYPES = [
        {"name": "VIRUS",   "speed_mult": 1.0, "damage": 10},
        {"name": "DDOS",    "speed_mult": 1.4, "damage": 7},
        {"name": "MALWARE", "speed_mult": 0.8, "damage": 15},
    ]

    def __init__(self):
        atype       = random.choice(self.TYPES)
        self.x      = -30.0
        self.y      = float(random.randint(80, SCREEN_HEIGHT - 80))
        self.speed  = random.uniform(ATTACKER_SPEED_MIN,
                                     ATTACKER_SPEED_MAX) * atype["speed_mult"]
        self.damage = atype["damage"]
        self.active = True

    def update(self):
        self.x += self.speed

# CYBER DEFENSE ENVIRONMENT

class CyberDefenseEnv(gym.Env):
    """
    Custom Gymnasium environment for the Cyber Defense Arena.

    OBSERVATION SPACE (what the agent sees):
    ─────────────────────────────────────────
    A flat numpy array of shape (3 + MAX_ATTACKERS*2,) = 13 values:
      [0]   agent_y          (normalized 0–1)
      [1]   server_hp        (normalized 0–1)
      [2]   num_attackers    (normalized 0–1)
      [3]   attacker_0_x     (normalized 0–1)
      [4]   attacker_0_y     (normalized 0–1)
      ... repeated for up to MAX_ATTACKERS attackers
      Missing attackers are filled with [-1, -1] (off-screen)

    ACTION SPACE (what the agent can do):
    ─────────────────────────────────────
      0 = move UP
      1 = move DOWN
      2 = stay STILL

    REWARD SYSTEM:
    ──────────────
      +10   blocked attacker
      -10   missed attacker (reached server)
      +1    every step server is still alive (survival bonus)
      -50   server HP reaches 0 (episode ends)
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}

    def __init__(self, render_mode=None):
        super().__init__()

        self.render_mode = render_mode

        # Action Space: 3 discrete actions
        self.action_space = spaces.Discrete(3)
        # 0 = UP, 1 = DOWN, 2 = STAY

        # Observation Space: 13 normalized floats 
        obs_size = 3 + MAX_ATTACKERS * 2
        self.observation_space = spaces.Box(
            low  = -1.0,
            high =  1.0,
            shape=(obs_size,),
            dtype=np.float32
        )

        # Internal state 
        self.agent_y    = float(SCREEN_HEIGHT // 2)
        self.server_hp  = 100.0
        self.attackers  = []
        self.frame      = 0
        self.steps      = 0
        self.score      = 0
        self.blocks     = 0
        self.misses     = 0

        # Pygame rendering (only used if render_mode="human")
        self.screen     = None
        self.clock      = None
        self.pygame_initialized = False

    # RESET — called at start of every episode
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.agent_y   = float(SCREEN_HEIGHT // 2)
        self.server_hp = 100.0
        self.attackers = []
        self.frame     = 0
        self.steps     = 0
        self.score     = 0
        self.blocks    = 0
        self.misses    = 0

        obs = self._get_obs()
        info = {}
        return obs, info

    
    # STEP — called every frame; agent takes one action
    
    def step(self, action):
        self.frame += 1
        self.steps += 1
        reward = 0.0

        #  1. Apply action
        if action == 0:   # Move UP
            self.agent_y = max(AGENT_HALF_H + 60,
                               self.agent_y - AGENT_SPEED)
        elif action == 1: # Move DOWN
            self.agent_y = min(SCREEN_HEIGHT - AGENT_HALF_H - 20,
                               self.agent_y + AGENT_SPEED)
        # action == 2: STAY — do nothing

        # 2. Spawn new attacker 
        if self.frame % SPAWN_EVERY == 0:
            self.attackers.append(SimAttacker())

        # 3. Update attackers 
        still_active = []
        for att in self.attackers:
            att.update()

            # Check collision with agent
            agent_top    = self.agent_y - AGENT_HALF_H
            agent_bottom = self.agent_y + AGENT_HALF_H
            agent_left   = AGENT_X - 15
            agent_right  = AGENT_X + 15

            hit_x = agent_left <= att.x <= agent_right
            hit_y = agent_top  <= att.y <= agent_bottom

            if hit_x and hit_y:
                # ✅ BLOCKED
                reward      += 10
                self.score  += 10
                self.blocks += 1
                # attacker removed (don't add to still_active)

            elif att.x >= SERVER_X - 40:
                # ❌ MISSED — reached server
                reward           -= 10
                self.score       -= 5
                self.misses      += 1
                self.server_hp    = max(0, self.server_hp - att.damage)
                # attacker removed

            else:
                still_active.append(att)

        self.attackers = still_active

        # 4. Survival reward 
        if self.server_hp > 0:
            reward += 1.0   # small bonus for staying alive each step

        # 5. Check termination 
        terminated = self.server_hp <= 0
        truncated  = self.steps >= MAX_STEPS

        if terminated:
            reward -= 50    # big penalty for losing server

        # 6. Get observation 
        obs  = self._get_obs()
        info = {
            "score":  self.score,
            "blocks": self.blocks,
            "misses": self.misses,
            "hp":     self.server_hp
        }

        # 7. Render if human mode 
        if self.render_mode == "human":
            self._render_frame()

        return obs, reward, terminated, truncated, info


    # GET OBSERVATION — builds the state vector the agent sees
    
    def _get_obs(self):
        obs = np.full(3 + MAX_ATTACKERS * 2, -1.0, dtype=np.float32)

        # Normalize agent Y (0 = top, 1 = bottom)
        obs[0] = self.agent_y / SCREEN_HEIGHT

        # Normalize server HP (0 = dead, 1 = full)
        obs[1] = self.server_hp / 100.0

        # Number of active attackers (normalized)
        obs[2] = len(self.attackers) / MAX_ATTACKERS

        # Sort attackers by distance to agent (closest first)
        sorted_atts = sorted(self.attackers,
                             key=lambda a: abs(a.x - AGENT_X))

        for i, att in enumerate(sorted_atts[:MAX_ATTACKERS]):
            obs[3 + i*2]     = att.x / SCREEN_WIDTH   # normalized X
            obs[3 + i*2 + 1] = att.y / SCREEN_HEIGHT  # normalized Y

        return obs

    
    # RENDER — Pygame visual (called only in render_mode="human")
   
    def render(self):
        if self.render_mode == "human":
            self._render_frame()

    def _render_frame(self):
        import pygame

        # Initialize pygame once
        if not self.pygame_initialized:
            pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("AI Cyber Defense — RL Training")
            self.clock  = pygame.time.Clock()
            self.font_s = pygame.font.SysFont("consolas", 14)
            self.font_l = pygame.font.SysFont("consolas", 22, bold=True)
            self.pygame_initialized = True

        # Handle quit event during training render
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return

        screen = self.screen

        # Background
        screen.fill((5, 10, 20))

        # Grid
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(screen, (0, 30, 50), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(screen, (0, 30, 50), (0, y), (SCREEN_WIDTH, y))

        # Border
        pygame.draw.rect(screen, (0, 180, 120),
                         (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 3)

        # Divider
        for y in range(0, SCREEN_HEIGHT, 15):
            pygame.draw.line(screen, (0, 80, 80),
                             (AGENT_X, y), (AGENT_X, y+8), 1)

        # Server
        pygame.draw.circle(screen, (0, 255, 180), (SERVER_X, SCREEN_HEIGHT//2), 32)
        pygame.draw.circle(screen, (255,255,255), (SERVER_X, SCREEN_HEIGHT//2), 32, 2)

        # Agent
        ax = AGENT_X
        ay = int(self.agent_y)
        pygame.draw.rect(screen, (0, 150, 255),
                         (ax-15, ay-AGENT_HALF_H, 30, AGENT_HALF_H*2),
                         border_radius=6)
        pygame.draw.rect(screen, (255,255,255),
                         (ax-15, ay-AGENT_HALF_H, 30, AGENT_HALF_H*2), 2,
                         border_radius=6)

        # Attackers
        import math
        for att in self.attackers:
            cx, cy = int(att.x), int(att.y)
            s = 13
            points = [(cx + s*math.cos(math.radians(i*60)),
                       cy + s*math.sin(math.radians(i*60))) for i in range(6)]
            pygame.draw.polygon(screen, (255, 60, 60), points)

            # Attack line to server
            pygame.draw.line(screen, (80, 20, 20),
                             (cx, cy), (SERVER_X, SCREEN_HEIGHT//2), 1)

        # HUD
        title = self.font_l.render("AI CYBER DEFENSE — TRAINING", True, (200,255,240))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 12))

        stats = [
            f"STEP   : {self.steps}",
            f"SCORE  : {self.score}",
            f"BLOCKS : {self.blocks}",
            f"MISSES : {self.misses}",
            f"HP     : {int(self.server_hp)}%",
        ]
        for i, s in enumerate(stats):
            color = (0,150,255) if i < 3 else (220,50,50)
            surf = self.font_s.render(s, True, color)
            screen.blit(surf, (20, 100 + i*24))

        # Server HP bar
        bar_w = 100
        ratio = self.server_hp / 100
        fill  = (0,220,100) if ratio > 0.4 else (220,50,50)
        pygame.draw.rect(screen, (30,30,30),
                         (SCREEN_WIDTH-130, 100, bar_w, 14))
        pygame.draw.rect(screen, fill,
                         (SCREEN_WIDTH-130, 100, int(bar_w*ratio), 14))
        pygame.draw.rect(screen, (200,255,240),
                         (SCREEN_WIDTH-130, 100, bar_w, 14), 1)
        label = self.font_s.render("SERVER HP", True, (200,255,240))
        screen.blit(label, (SCREEN_WIDTH-130, 82))

        pygame.display.flip()
        self.clock.tick(60)
            
    # CLOSE 
  
    def close(self):
        if self.pygame_initialized:
            import pygame
            pygame.quit()
            self.pygame_initialized = False