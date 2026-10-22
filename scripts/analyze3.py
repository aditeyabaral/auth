"""Summarise the interleaved Alpine vs slim-bookworm vs slim-trixie run."""

import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("/home/aditeyabaral/Desktop/pesu/auth/benchmark/results/alpine_slim_trixie")
NAMES = ["alpine", "slim", "trixie"]
rng = np.random.default_rng(0)
pd.set_option("display.width", 200)

df = pd.read_csv(OUT / "requests.csv")
meta = json.loads((OUT / "meta.json").read_text())
cold = pd.DataFrame(json.loads((OUT / "cold_start.json").read_text()))

warm = df[df.block == "warmup"]
df = df[df.block != "warmup"].copy()
df["block"] = df["block"].astype(int)
df["triad"] = df["block"] // 3
df["app_ms"] = (df.server_s - df.login_s - df.profile_s) * 1000
for c in ("client_s", "server_s", "login_s", "profile_s"):
    df[c.replace("_s", "_ms")] = df[c] * 1000

print("requests", df.groupby("image").size().to_dict(), "success", df.groupby("image").status.sum().to_dict())
print("warmup (first request per container, ms):")
print((warm.set_index("image")[["client_s", "login_s", "profile_s"]] * 1000).round(0).to_string())

p95 = lambda x: np.percentile(x, 95)  # noqa: E731
STATS = (("mean", np.mean), ("median", np.median), ("p95", p95))
COLS = [
    ("client_ms", "end-to-end (client)"),
    ("server_ms", "server /authenticate"),
    ("login_ms", "PESU login (auth)"),
    ("profile_ms", "PESU profile fetch"),
    ("app_ms", "in-app overhead"),
    ("cpu_ms", "CPU per request"),
    ("cpu_user_ms", "  CPU user"),
    ("cpu_sys_ms", "  CPU system"),
]


def boot(a: np.ndarray, b: np.ndarray, stat, n: int = 10000) -> tuple[float, float, float]:
    """stat(b) - stat(a), with a 95% bootstrap interval."""
    d = np.array([stat(rng.choice(b, len(b))) - stat(rng.choice(a, len(a))) for _ in range(n)])
    return stat(b) - stat(a), *np.percentile(d, [2.5, 97.5])


print("\nPER IMAGE (ms)")
rows = []
for col, label in COLS:
    for sname, f in STATS:
        rows.append({"metric": label, "stat": sname, **{n: round(f(df[df.image == n][col]), 1) for n in NAMES}})
print(pd.DataFrame(rows).to_string(index=False))

print("\nPAIRWISE DIFFERENCES (ms), second minus first, [95% bootstrap CI]")
for a_name, b_name in combinations(NAMES, 2):
    print(f"-- {b_name} - {a_name}")
    for col, label in COLS:
        a = df[df.image == a_name][col].to_numpy()
        b = df[df.image == b_name][col].to_numpy()
        parts = []
        for sname, f in STATS:
            d, lo, hi = boot(a, b, f)
            parts.append(f"{sname} {d:+7.1f} [{lo:+.1f}, {hi:+.1f}]")
        print(f"  {label:22s} " + " | ".join(parts))

print("\nPER-BLOCK MEANS (ms)")
print(
    df.groupby(["block", "image"])[["client_ms", "login_ms", "profile_ms", "app_ms", "cpu_ms"]]
    .mean()
    .round(1)
    .to_string()
)
print("\nWITHIN-TRIAD DIFFERENCES of block means (each triad has one block per image)")
tri = df.groupby(["triad", "image"])[["client_ms", "login_ms", "cpu_ms"]].mean().unstack("image")
for col in ("client_ms", "login_ms", "cpu_ms"):
    t = tri[col]
    for a_name, b_name in combinations(NAMES, 2):
        d = (t[b_name] - t[a_name]).round(1).tolist()
        print(f"  {col:10s} {b_name}-{a_name}: {d}  mean {np.mean(d):+.1f}")

blocks = pd.DataFrame(meta["blocks"])
blocks = blocks[blocks.block != "warmup"]
cpu_pct = blocks.groupby("image").apply(lambda g: 100 * g.cpu_s.sum() / g.wall_s.sum(), include_groups=False)
print("\nCPU % of one core while serving:", cpu_pct.round(3).to_dict())

print("\nMEMORY")
for name in NAMES:
    f = meta["final"][name]
    print(
        f"{name:7s}",
        f"idle RSS {f['idle_mem']['rss_kb'] / 1024:.1f} MiB, idle anon {f['idle_mem']['cg_anon'] / 2**20:.1f} MiB,",
        f"final RSS {f['mem']['rss_kb'] / 1024:.1f} MiB, peak RSS {f['mem']['hwm_kb'] / 1024:.1f} MiB,",
        f"cgroup peak {f['mem']['cg_peak'] / 2**20:.1f} MiB, docker stats {f['docker_stats']['MemUsage']}",
    )

print("\nSIZES")
for name in NAMES:
    s, f = meta["static"][name], meta["final"][name]
    print(
        f"{name:7s}",
        f"image {s['image_size_bytes'] / 1e6:.1f} MB, gzip {s['gzip_bytes'] / 1e6:.1f} MB, layers {s['layers']},",
        f"container writable {f['size_rw']} B, rootfs {f['size_rootfs'] / 1e6:.1f} MB, {s['openssl']}",
    )

print("\nCOLD START (docker run -> /health 200)")
print(
    cold.assign(rss_mib=cold.rss_kb / 1024)
    .groupby("image")
    .agg(n=("ready_s", "size"), ready_mean=("ready_s", "mean"), ready_median=("ready_s", "median"),
         ready_min=("ready_s", "min"), ready_max=("ready_s", "max"), rss_mib=("rss_mib", "mean"))
    .round(3)
    .to_string()
)
