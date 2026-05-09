# 🛡️ AI Cyber Defense Arena

> **A Deep Reinforcement Learning-Based Cybersecurity Defense Agent**

A 2D real-time cybersecurity simulation where an AI-powered firewall agent learns to intercept and block incoming cyber-attackers using **Proximal Policy Optimization (PPO)** reinforcement learning — built entirely in Python with live visuals, particle effects, and automatic GIF recording.

---

## Demo

> Run `python arena.py ai` — the GIF saves automatically to `recordings/cyber_defense_demo.gif`

| Element           | Description                      |
| ----------------- | -------------------------------- |
| 🟢 Green Circle   | Protected Server                 |
| 🔵 Blue Rectangle | AI Firewall Agent                |
| 🔴🟠🟣 Hexagons   | VIRUS / DDOS / MALWARE Attackers |
| ✨ Particles      | Explosion on successful block    |
| ● REC             | Live GIF recording indicator     |

---

## Project Overview

The **AI Cyber Defense Arena** is my university simple assignment that demonstrates how reinforcement learning can be applied to cybersecurity. A defense agent (firewall) learns — purely through trial and error — to move up and down to block three types of incoming attackers before they damage the server.

**Key highlights:**

- Agent starts with ~15% block rate (random) and reaches ~85% after training
- Full visual arena with glowing effects, attack trails, and particle explosions
- Entire gameplay session recorded as a looping GIF automatically
- Clean modular codebase — easy to read, extend, and explain

---

## How It Works

```
ENVIRONMENT ──── state ────► AGENT (PPO Neural Network)
     ▲                              │
     │                           action
     │                              │
ENVIRONMENT ◄─── action ────────────┘
     │
     └──── reward ──────────► Agent improves policy
```

### State Space (what the AI sees)

A 13-element normalized float array:

- Agent Y position
- Server HP
- Number of active attackers
- X, Y coordinates of up to 5 nearest attackers

### Action Space (what the AI can do)

| Action | Behavior   |
| ------ | ---------- |
| 0      | Move UP    |
| 1      | Move DOWN  |
| 2      | Stay STILL |

### Reward Function

| Event             | Reward |
| ----------------- | ------ |
| Block an attacker | +10    |
| Miss an attacker  | -10    |
| Survive each step | +1     |
| Server destroyed  | -50    |

---

## Project Structure

```
ai_cyber_defense/
 ├── arena.py          # Pygame visual arena + AI mode + auto GIF recording
 ├── environment.py    # Custom Gymnasium RL environment
 ├── train.py          # PPO training, evaluation, and model saving
 ├── assets/           # Images, icons (extendable)
 ├── models/
 │    ├── cyber_defense_ppo.zip        # Final trained model
 │    └── best_model/best_model.zip    # Best checkpoint during training
 └── recordings/
      └── cyber_defense_demo.gif       # Auto-saved gameplay GIF
```

---

## Tech Stack

| Library           | Version | Purpose                                 |
| ----------------- | ------- | --------------------------------------- |
| Python            | 3.8+    | Core language                           |
| Pygame            | 2.x     | 2D visual arena, animation, GIF capture |
| Gymnasium         | 0.29+   | RL environment standard interface       |
| Stable-Baselines3 | 2.x     | PPO algorithm implementation            |
| NumPy             | 1.24+   | Observation arrays and frame processing |
| imageio           | 2.x     | GIF encoding from captured frames       |
| OpenCV            | 4.x     | Optional video recording                |

---

## Installation & Setup

### 1. Clone the repository

### 2. Create a virtual environment (recommended)

```bash
python -m venv cyber_env

# Windows
cyber_env\Scripts\activate

# Mac / Linux
source cyber_env/bin/activate
```

### 3. Install dependencies

```bash
pip install pygame gymnasium stable-baselines3 numpy opencv-python imageio
```

---

## Running the Project

### Step 1 — Train the AI agent

```bash
python train.py
```

This will:

- Run an environment sanity check (500 random steps)
- Train PPO for 150,000 timesteps across 4 parallel environments
- Print live progress (reward, blocks, misses every 5,000 steps)
- Save the model to `models/cyber_defense_ppo.zip`
- Auto-evaluate the trained model over 10 episodes

Training takes **3–5 minutes** on a standard CPU.

### Step 2 — Watch the AI play (auto-saves GIF)

```bash
python arena.py ai
```

The GIF records automatically and saves to `recordings/cyber_defense_demo.gif` when the game ends.

### Step 3 — Play manually

```bash
python arena.py
```

Use `↑ ↓` arrow keys to move the firewall. Press `R` to restart, `ESC` to quit.

### Other commands

```bash
python train.py eval       # Re-evaluate saved model over 10 episodes
python train.py continue   # Continue training from saved checkpoint
```

---

## Training Results

| Metric              | Untrained (Random) | After 150,000 Steps   |
| ------------------- | ------------------ | --------------------- |
| Block Rate          | ~15%               | ~85%                  |
| Avg Episode Reward  | -45                | +142                  |
| Server HP Remaining | Drops quickly      | ~74%                  |
| Strategy            | None               | Tracks nearest threat |

---

## Controls

| Key       | Action                            |
| --------- | --------------------------------- |
| `↑` Arrow | Move firewall up                  |
| `↓` Arrow | Move firewall down                |
| `G`       | Start GIF recording (manual mode) |
| `R`       | Restart after game over           |
| `ESC`     | Quit                              |

---

## Attacker Types

| Type    | Speed  | Damage | Color     |
| ------- | ------ | ------ | --------- |
| VIRUS   | Medium | 10 HP  | 🔴 Red    |
| DDOS    | Fast   | 7 HP   | 🟠 Orange |
| MALWARE | Slow   | 15 HP  | 🟣 Purple |

---

## Customization

**`arena.py` / `environment.py`**

```python
SPAWN_INTERVAL = 90      # Frames between attacker spawns (lower = harder)
MAX_ATTACKERS  = 5       # Max attackers tracked in observation
WIN_SCORE      = 300     # Score needed to win
AGENT_SPEED    = 5       # Firewall movement speed
```

**`train.py`**

```python
total_timesteps = 150_000   # Increase for better performance
n_envs          = 4         # Parallel environments
learning_rate   = 3e-4      # PPO learning rate
```

---

1. Run `python train.py` — it trains and saves automatically

---

## Common Issues & Fixes

| Error                                    | Fix                                  |
| ---------------------------------------- | ------------------------------------ |
| `ModuleNotFoundError: pygame`            | `pip install pygame`                 |
| `ModuleNotFoundError: stable_baselines3` | `pip install stable-baselines3`      |
| `No trained model found` in arena.py     | Run `python train.py` first          |
| GIF file is very large                   | Set `GIF_FPS = 12` in arena.py       |
| Training very slow                       | Normal on CPU — takes 3–5 min        |
| `observation space mismatch`             | Delete `models/` folder and retrain  |
| Window too large for screen              | Set `SCREEN_WIDTH = 700` in arena.py |

---

## Algorithm Reference

- **PPO Paper:** Schulman et al. (2017) — _Proximal Policy Optimization Algorithms_ — [arxiv.org/abs/1707.06347](https://arxiv.org/abs/1707.06347)
- **Stable-Baselines3 Docs:** [stable-baselines3.readthedocs.io](https://stable-baselines3.readthedocs.io)
- **Gymnasium Docs:** [gymnasium.farama.org](https://gymnasium.farama.org)

---

## Future Work

- [ ] Multi-agent defense (two cooperative firewalls)
- [ ] Adversarial attackers trained with RL
- [ ] LSTM policy for remembering attack patterns
- [ ] Real network dataset integration (NSL-KDD / CICIDS)
- [ ] Difficulty curriculum (progressive attacker scaling)
- [ ] Web-based demo using WebAssembly

---

## License

This project is for educational purposes. Feel free to fork, modify, and build on it.

---

## Author

**MAHNOOR LATIF**
University Of Punjab (PUCIT), LAHORE | COMPUTER SCIENCE | 2026

> Built as a university assignment demonstrating Deep Reinforcement Learning applied to Cybersecurity simulation.

---
