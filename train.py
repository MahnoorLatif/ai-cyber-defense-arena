import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor
from environment import CyberDefenseEnv

# ─── Paths ────────────────────────────────────────────────
MODEL_DIR   = "models"
MODEL_PATH  = os.path.join(MODEL_DIR, "cyber_defense_ppo")
BEST_PATH   = os.path.join(MODEL_DIR, "best_model")
LOG_DIR     = os.path.join(MODEL_DIR, "logs")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR,   exist_ok=True)
os.makedirs(BEST_PATH, exist_ok=True)

# CALLBACK — rich console progress

class RichCallback(BaseCallback):
    def __init__(self, print_every=5000):
        super().__init__()
        self.print_every     = print_every
        self.ep_rewards      = []
        self.ep_blocks       = []
        self.ep_misses       = []
        self.cur_reward      = 0
        self.best_avg        = -999

    def _on_step(self) -> bool:
        reward = self.locals.get("rewards", [0])[0]
        self.cur_reward += reward

        done = self.locals.get("dones", [False])[0]
        if done:
            info = self.locals.get("infos", [{}])[0]
            self.ep_rewards.append(self.cur_reward)
            self.ep_blocks.append(info.get("blocks", 0))
            self.ep_misses.append(info.get("misses", 0))
            self.cur_reward = 0

        if self.num_timesteps % self.print_every == 0 and self.ep_rewards:
            last   = self.ep_rewards[-10:]
            avg_r  = np.mean(last)
            avg_b  = np.mean(self.ep_blocks[-10:])  if self.ep_blocks  else 0
            avg_m  = np.mean(self.ep_misses[-10:])  if self.ep_misses  else 0
            tag    = " ← BEST" if avg_r > self.best_avg else ""
            if avg_r > self.best_avg:
                self.best_avg = avg_r

            bar_len  = 20
            progress = int((self.num_timesteps / 150_000) * bar_len)
            bar      = "█" * progress + "░" * (bar_len - progress)

            print(f"\n  [{bar}] {self.num_timesteps:>8,} / 150,000")
            print(f"  Avg Reward : {avg_r:>8.1f}{tag}")
            print(f"  Avg Blocks : {avg_b:>8.1f}")
            print(f"  Avg Misses : {avg_m:>8.1f}")
            print(f"  Episodes   : {len(self.ep_rewards)}")
        return True

# ENVIRONMENT TEST

def test_env():
    print("\n  ┌─────────────────────────────────────┐")
    print("  │   ENVIRONMENT SANITY CHECK          │")
    print("  └─────────────────────────────────────┘")

    env = CyberDefenseEnv(render_mode=None)
    obs, _ = env.reset()

    print(f"  Obs shape    : {obs.shape}")
    print(f"  Action space : {env.action_space}")
    print(f"  Obs range    : [{obs.min():.2f}, {obs.max():.2f}]")

    total_r = 0
    for _ in range(500):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_r += reward
        if terminated or truncated:
            obs, _ = env.reset()

    print(f"  500 random steps reward: {total_r:.1f}")
    print("  ✅ Environment OK\n")
    env.close()

# EVALUATE TRAINED MODEL

def evaluate_model(model, n_episodes=10):
    print("\n  ┌─────────────────────────────────────┐")
    print("  │   EVALUATING TRAINED MODEL          │")
    print("  └─────────────────────────────────────┘")

    env = CyberDefenseEnv(render_mode=None)
    rewards, blocks, misses, hps = [], [], [], []

    for ep in range(n_episodes):
        obs, _ = env.reset()
        ep_r   = 0
        done   = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_r += reward
            done  = terminated or truncated

        rewards.append(ep_r)
        blocks.append(info.get("blocks", 0))
        misses.append(info.get("misses", 0))
        hps.append(info.get("hp", 0))
        print(f"  Ep {ep+1:>2} | Reward: {ep_r:>8.1f} | "
              f"Blocks: {info.get('blocks',0):>3} | "
              f"Misses: {info.get('misses',0):>3} | "
              f"HP left: {info.get('hp',0):>5.1f}")

    env.close()
    print(f"\n  ── Summary over {n_episodes} episodes ──")
    print(f"  Avg Reward : {np.mean(rewards):.1f}")
    print(f"  Avg Blocks : {np.mean(blocks):.1f}")
    print(f"  Avg Misses : {np.mean(misses):.1f}")
    print(f"  Avg HP left: {np.mean(hps):.1f}")
    acc = np.mean(blocks) / max(1, np.mean(blocks) + np.mean(misses))
    print(f"  Block Rate : {acc*100:.1f}%")

# MAIN TRAIN

def train():
    print("\n  ╔═══════════════════════════════════════╗")
    print("  ║   AI CYBER DEFENSE — PPO TRAINING    ║")
    print("  ╚═══════════════════════════════════════╝")
    print("  Algorithm  : PPO")
    print("  Steps      : 150,000")
    print("  Parallel   : 4 environments")
    print(f"  Save path  : {MODEL_PATH}.zip\n")

    # 4 parallel envs for faster training
    env = make_vec_env(
        lambda: CyberDefenseEnv(render_mode=None),
        n_envs=4
    )

    # Eval env (single, monitored)
    eval_env = Monitor(CyberDefenseEnv(render_mode=None))

    model = PPO(
        policy          = "MlpPolicy",
        env             = env,
        learning_rate   = 3e-4,
        n_steps         = 1024,
        batch_size      = 128,
        n_epochs        = 10,
        gamma           = 0.99,
        gae_lambda      = 0.95,
        ent_coef        = 0.02,
        clip_range      = 0.2,
        verbose         = 0,
        tensorboard_log = LOG_DIR,
        device          = "auto"
    )

    # Save best model automatically
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path = BEST_PATH,
        log_path             = LOG_DIR,
        eval_freq            = 10_000,
        n_eval_episodes      = 5,
        deterministic        = True,
        verbose              = 0
    )

    rich_cb = RichCallback(print_every=5000)

    print("  Training in progress...\n")
    model.learn(
        total_timesteps = 150_000,
        callback        = [rich_cb, eval_cb],
        progress_bar    = True
    )

    model.save(MODEL_PATH)
    print(f"\n  ✅ Final model  → {MODEL_PATH}.zip")
    print(f"  ✅ Best model   → {BEST_PATH}/best_model.zip")

    env.close()
    eval_env.close()

    # Auto-evaluate after training
    evaluate_model(model)

# LOAD & CONTINUE TRAINING (bonus feature)

def continue_training(extra_steps=50_000):
    path = MODEL_PATH + ".zip"
    if not os.path.exists(path):
        print("  No model found. Run train() first.")
        return

    print(f"\n  Loading {path} and continuing training...")
    env = make_vec_env(
        lambda: CyberDefenseEnv(render_mode=None),
        n_envs=4
    )
    model = PPO.load(path, env=env)
    model.learn(
        total_timesteps = extra_steps,
        callback        = RichCallback(print_every=5000),
        progress_bar    = True,
        reset_num_timesteps = False
    )
    model.save(MODEL_PATH)
    print(f"  ✅ Continued model saved → {MODEL_PATH}.zip")
    env.close()


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"

    if cmd == "test":
        test_env()
    elif cmd == "eval":
        model = PPO.load(MODEL_PATH)
        evaluate_model(model, n_episodes=10)
    elif cmd == "continue":
        continue_training()
    else:
        test_env()
        train()