# bot/infographic.py
# White-theme charts (distinct colors per bar) + inline CSS + CSV/JSON exports + Sources drawer.

import os, json, csv
from datetime import datetime
from collections import Counter

import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

# ---------- CHART STYLE: white background, black text ----------
plt.rcParams.update({
    "figure.facecolor": "#ffffff",
    "axes.facecolor":   "#ffffff",
    "axes.edgecolor":   "#cccccc",
    "axes.labelcolor":  "#111111",
    "axes.titlecolor":  "#111111",
    "xtick.color":      "#111111",
    "ytick.color":      "#111111",
    "font.size":        10,
})

PALETTE_KEYWORDS = [
    "#2E93fA","#66DA26","#546E7A","#E91E63","#FF9800",
    "#00E396","#775DD0","#008FFB","#FEB019","#FF4560",
    "#00D9E9","#A300D6","#F86624","#D10CE8","#4CAF50",
    "#9C27B0","#03A9F4","#F9A3A4","#90EE7E","#FA4443"
]
PALETTE_BRANDS = [
    "#7B61FF","#FF6B6B","#00C49A","#FFB703","#219EBC",
    "#8338EC","#FB5607","#06D6A0","#118AB2","#EF476F",
    "#8ECAE6","#3A86FF","#FFBE0B","#2EC4B6","#FF7C43"
]

def pick_colors(n, palette):
    if n <= len(palette):
        return palette[:n]
    reps = (n + len(palette) - 1) // len(palette)
    return (palette * reps)[:n]

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left","bottom"):
        ax.spines[s].set_color("#e0e0e0")
        ax.spines[s].set_linewidth(1)
    ax.grid(axis="x", color="#eeeeee", linewidth=0.9, alpha=1.0, zorder=0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(6))
    ax.set_xlabel("Relative Importance", labelpad=8)

def save_barh_modern(labels, values, title, outpath, palette):
    ensure_dir(outpath)
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8.6, 6.2), dpi=170)

    style_axes(ax)
    ax.set_title(title, pad=10, fontsize=12, fontweight="bold")

    y = list(range(len(labels)))
    colors = pick_colors(len(labels), palette)
    bars = ax.barh(y, values, color=colors, edgecolor="#ffffff", linewidth=0.5, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)

    for bar, val in zip(bars, values):
        ax.text(val + (max(values) * 0.02 if values else 0.2),
                bar.get_y() + bar.get_height()/2,
                f"{val}", va="center", ha="left", color="#111111", fontsize=9)

    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

# ---------- Data helpers ----------
def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)
    json_path = os.path.join(assets_dir, "headlines.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(highlights, jf, indent=2, ensure_ascii=False)
    csv_path = os.path.join(assets_dir, "headlines.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=["title","link","source","published"])
        writer.writeheader()
        for h in highlights:
            writer.writerow({
                "title": h.get("title",""),
                "link": h.get("link",""),
                "source": h.get("source",""),
                "published": h.get("published",""),
            })
    return os.path.basename(csv_path), os.path.basename(json_path)

def sources_list_html(highlights, stats):
    counts = Counter([h.get("source","").strip() for h in highlights if h.get("source")])
    unique_sources = (stats or {}).get("sources") or sorted(s for s in counts if s)
    lis = []
    if counts:
        for src, n in sorted(counts.items(), key=lambda kv:(-kv[1], kv[0])):
            if src: lis.append(f"<li><span class='src-name'>{src}</span> <span class='src-count'>({n})</span></li>")
    else:
        for src in unique_sources:
            if src: lis.append(f"<li><span class='src-name'>{src}</span></li>")
    total = len(unique_sources) if unique_sources else len(counts)
    return f"""
    <details class="card" style="margin-top:18px">
      <summary style="cursor:pointer"><strong>Sources</strong> (today: {total})</summary>
      <ul class="list" style="margin-top:10px">
        {''.join(lis) if lis else '<li><em>No sources detected.</em></li>'}
      </ul>
    </details>
    """

# ---------- HTML with inline white CSS ----------
INLINE_CSS = """<style>
:root{
  --bg:#ffffff; --panel:#ffffff; --text
