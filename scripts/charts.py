"""Charts for the slim-trixie PR, in light and dark variants."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RES = Path("/home/aditeyabaral/Desktop/pesu/auth/benchmark/results/alpine_slim_trixie")
OUT = Path("/tmp/claude-1000/-home-aditeyabaral-Desktop-pesu-auth/13562676-b02e-44ef-94c4-dc5d133e92e7/scratchpad/charts")
OUT.mkdir(exist_ok=True)

NAMES = ["alpine", "slim", "trixie"]
LABELS = {"alpine": "alpine", "slim": "slim-bookworm", "trixie": "slim-trixie"}
THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e1e0d9",
        "series": {"alpine": "#2a78d6", "slim": "#eb6834", "trixie": "#1baf7a"},
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "grid": "#2c2c2a",
        "series": {"alpine": "#3987e5", "slim": "#d95926", "trixie": "#199e70"},
    },
}

df = pd.read_csv(RES / "requests.csv")
df = df[df.block != "warmup"].copy()
df["block"] = df["block"].astype(int)
df["client_ms"] = df.client_s * 1000
meta = json.loads((RES / "meta.json").read_text())
cold = pd.DataFrame(json.loads((RES / "cold_start.json").read_text()))


def style(ax, t):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["grid"])
    ax.tick_params(colors=t["ink2"], length=0, labelsize=9)
    ax.grid(axis="x", color=t["grid"], linewidth=1)
    ax.set_axisbelow(True)
    ax.title.set_color(t["ink"])
    ax.xaxis.label.set_color(t["ink2"])
    ax.yaxis.label.set_color(t["ink2"])


def figure(t, ncols=1, nrows=1, size=(10, 3.4), **kw):
    fig, axes = plt.subplots(nrows, ncols, figsize=size, facecolor=t["surface"], **kw)
    return fig, np.atleast_1d(axes)


def save(fig, name, theme):
    fig.savefig(OUT / f"{name}-{theme}.png", dpi=200, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def strip_panel(ax, t, col, title, unit, fmt):
    """One row per image: every request as a dot, median as a bar, median labelled."""
    rng = np.random.default_rng(1)
    for row, name in enumerate(reversed(NAMES)):
        vals = df[df.image == name][col].to_numpy()
        y = row + rng.uniform(-0.18, 0.18, len(vals))
        ax.scatter(vals, y, s=14, color=t["series"][name], alpha=0.55, linewidths=0)
        med, p95 = np.median(vals), np.percentile(vals, 95)
        ax.plot([med, med], [row - 0.3, row + 0.3], color=t["ink"], linewidth=2, solid_capstyle="round")
        ax.annotate(f"median {fmt(med)}  ·  p95 {fmt(p95)}", (med, row + 0.32), color=t["ink2"], fontsize=8.5,
                    ha="center", va="bottom")
    ax.set_yticks(range(len(NAMES)), [LABELS[n] for n in reversed(NAMES)], color=t["ink"], fontsize=10)
    ax.set_ylim(-0.6, len(NAMES) - 0.25)
    ax.set_xlabel(unit)
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=10, color=t["ink"])


def distributions(theme):
    t = THEMES[theme]
    fig, (a, b) = figure(t, ncols=2, size=(12, 3.6))
    for ax in (a, b):
        style(ax, t)
    strip_panel(a, t, "client_ms", "End-to-end /authenticate latency (100 requests each)", "milliseconds",
                lambda v: f"{v:,.0f} ms")
    strip_panel(b, t, "cpu_ms", "Container CPU time per request", "milliseconds of CPU", lambda v: f"{v:.1f} ms")
    b.set_xlim(left=0)
    fig.tight_layout(w_pad=3)
    save(fig, "distributions", theme)


def blocks(theme):
    t = THEMES[theme]
    fig, (a, b) = figure(t, nrows=2, size=(11, 5.4), sharex=True)
    bm = df.groupby(["block", "image"])[["client_ms", "cpu_ms"]].mean().reset_index()
    for ax, col, title, unit in (
        (a, "client_ms", "Mean end-to-end latency per block of 25 requests", "ms"),
        (b, "cpu_ms", "Mean CPU per request, per block of 25 requests", "ms of CPU"),
    ):
        style(ax, t)
        ax.grid(axis="y", color=t["grid"], linewidth=1)
        ax.grid(axis="x", visible=False)
        for name in NAMES:
            part = bm[bm.image == name]
            ax.scatter(part.block, part[col], s=64, color=t["series"][name], edgecolors=t["surface"],
                       linewidths=2, zorder=3, label=LABELS[name])
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=8, color=t["ink"])
        ax.set_ylabel(unit)
    b.set_ylim(bottom=0)
    b.set_xticks(range(12), [f"{i + 1}" for i in range(12)])
    b.set_xlabel("block, in run order (A B C  C B A  B C A  A C B)")
    leg = a.legend(loc="upper right", ncols=3, frameon=False, fontsize=9)
    for text in leg.get_texts():
        text.set_color(t["ink"])
    fig.tight_layout(h_pad=1.5)
    save(fig, "blocks", theme)


def bar_panel(ax, t, values, title, fmt):
    """Horizontal bars, 4px-style rounded data end, value labelled at the end."""
    style(ax, t)
    top = max(values.values())
    for row, name in enumerate(reversed(NAMES)):
        v = values[name]
        ax.barh(row, v, height=0.44, color=t["series"][name], linewidth=0)
        ax.annotate(fmt(v), (v, row), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9,
                    color=t["ink"])
    ax.set_xlim(0, top * 1.28)
    ax.set_ylim(-0.6, len(NAMES) - 0.4)
    ax.set_yticks(range(len(NAMES)), [LABELS[n] for n in reversed(NAMES)], color=t["ink"], fontsize=10)
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=8, color=t["ink"])
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)


def footprint(theme):
    t = THEMES[theme]
    fig, axes = figure(t, ncols=3, size=(13, 2.6))
    st, fin = meta["static"], meta["final"]
    bar_panel(axes[0], t, {n: st[n]["gzip_bytes"] / 1e6 for n in NAMES}, "Image, gzipped (pull size)",
              lambda v: f"{v:.1f} MB")
    bar_panel(axes[1], t, {n: fin[n]["size_rootfs"] / 1e6 for n in NAMES}, "Running container filesystem",
              lambda v: f"{v:.1f} MB")
    bar_panel(axes[2], t, cold.groupby("image").ready_s.median().to_dict(), "Cold start, median of 6",
              lambda v: f"{v:.2f} s")
    for ax in axes[1:]:
        ax.set_yticklabels([])
    fig.tight_layout(w_pad=2)
    save(fig, "footprint", theme)


for theme in THEMES:
    distributions(theme)
    blocks(theme)
    footprint(theme)
print(sorted(p.name for p in OUT.iterdir()))
