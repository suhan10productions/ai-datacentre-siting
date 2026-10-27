"""Figures for the siting analysis: a world map of facilities by water stress,
and a two-panel comparison of measured siting against reference baselines."""
import importlib.util
import json
import sys

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

R = json.load(open("results/results_final.json"))
spec = importlib.util.spec_from_file_location("sa", "siting_analysis.py")
sa = importlib.util.module_from_spec(spec)
sys.argv = ["sa"]
spec.loader.exec_module(sa)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "pdf.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
})
NAVY = "#1b3f73"
# single-hue sequential ramp, light -> dark (monotonic lightness, prints as greys)
RAMP = {0: "#dde5f0", 1: "#b3c4dc", 2: "#7f9cc4", 3: "#4a6fa3", 4: "#1b3f73"}
LABELS = {0: "Low (<10%)", 1: "Low-medium (10-20%)", 2: "Medium-high (20-40%)",
          3: "High (40-80%)", 4: "Extremely high (>80%)"}
OUT = "figs/"


def fig_map():
    world = gpd.read_file("data/ne_110m_countries.geojson")
    world = world[world["ADMIN"] != "Antarctica"]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    world.plot(ax=ax, color="#f2f2f2", edgecolor="#c8c8c8", linewidth=0.3)
    pdb = sa.pdb[sa.pdb.bws_cat >= 0]
    for cat in range(5):
        d = pdb[pdb.bws_cat == cat]
        ax.scatter(d.longitude, d.latitude, s=3.5, c=RAMP[cat], edgecolors="none",
                   alpha=0.95, zorder=3, rasterized=True)
    ep = sa.ep
    for cat in range(5):
        d = ep[ep.bws_cat == cat]
        ax.scatter(d.lon, d.lat, s=12 + d.planned_it_mw / 25, marker="D", c=RAMP[cat],
                   edgecolors="black", linewidths=0.6, zorder=4)
    ax.set_xlim(-170, 180)
    ax.set_ylim(-58, 78)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel(""); ax.set_ylabel("")
    for s in ax.spines.values():
        s.set_visible(False)
    handles = [Line2D([0], [0], marker="o", ls="", markersize=6, markerfacecolor=RAMP[c],
                      markeredgecolor="#666666", markeredgewidth=0.4, label=LABELS[c]) for c in range(5)]
    leg1 = ax.legend(handles=handles, title="Baseline water stress (Aqueduct 4.0)",
                     loc="upper left", frameon=False, fontsize=7, title_fontsize=7.5,
                     bbox_to_anchor=(0.02, 0.0), ncol=2, alignment="left")
    ax.add_artist(leg1)
    shape = [Line2D([0], [0], marker="o", ls="", markersize=4, markerfacecolor="#9a9a9a",
                    markeredgecolor="none", label="Interconnection facility (PeeringDB)"),
             Line2D([0], [0], marker="D", ls="", markersize=7, markerfacecolor="#9a9a9a",
                    markeredgecolor="black", markeredgewidth=0.6,
                    label="Large AI data centre (Epoch AI;\nsize = planned IT power)")]
    ax.legend(handles=shape, loc="upper left", frameon=False, fontsize=7,
              bbox_to_anchor=(0.62, -0.035))
    fig.savefig(OUT + "fig6_siting_map.pdf", bbox_inches="tight", pad_inches=0.02, dpi=300)
    plt.close(fig)


def dot(ax, y, s, color, label=None, fmt="{:.0f}%", scale=100, pos="above"):
    v, lo, hi = s["value"] * scale, s["ci"][0] * scale, s["ci"][1] * scale
    ax.plot([lo, hi], [y, y], color=color, lw=1.3, solid_capstyle="butt", zorder=2)
    ax.scatter([v], [y], s=34, color=color, edgecolors="white", linewidths=0.8, zorder=3)
    if pos == "above":
        ax.text(v, y + 0.2, fmt.format(v), ha="center", va="bottom", fontsize=7.5)
    else:
        ax.text(hi + 1.5, y, fmt.format(v), ha="left", va="center", fontsize=7.5)


def fig_tests():
    w, c = R["water"], R["carbon_us"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.7), gridspec_kw=dict(wspace=0.95))

    rows = [("World city population\n(reference)", w["cities_pop"], "#8c8c8c"),
            ("All facilities\n(PeeringDB, n = 5,254)", w["pdb"], "#5a5a5a"),
            ("Large AI sites,\nby count (n = 94)", w["epoch_count"], NAVY),
            ("Large AI sites,\nby planned capacity", w["epoch_planned"], NAVY)]
    for i, (lab, s, col) in enumerate(rows[::-1]):
        dot(a1, i, s, col, pos="right")
    ref = w["cities_pop"]["value"] * 100
    a1.plot([ref, ref], [-0.5, len(rows) - 0.5], ls="--", color="#8c8c8c", lw=0.8, zorder=1)
    a1.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]])
    a1.tick_params(axis="y", length=0)
    a1.set_xlim(0, 65)
    a1.set_xlabel("Share in high or extremely high\nwater stress (%)")
    a1.xaxis.grid(True, color="#e6e6e6", lw=0.5); a1.set_axisbelow(True)
    a1.set_title("(a) Water stress", loc="left", fontsize=8.5, fontweight="bold")

    rows2 = [("Existing facility fleet\n(PeeringDB, US)", c["pdb_mean"], "#5a5a5a"),
             ("Large AI sites,\nby count (US, n = 77)", c["epoch_count_mean"], NAVY),
             ("Large AI sites,\nby current capacity", c["epoch_current_wmean"], NAVY),
             ("Large AI sites,\nby planned capacity", c["epoch_planned_wmean"], NAVY)]
    for i, (lab, s, col) in enumerate(rows2[::-1]):
        dot(a2, i, s, col, fmt="{:.0f} g", scale=1)
    us = R["data"]["us_avg_ci"]
    a2.plot([us, us], [-0.5, len(rows2) - 0.5], ls="--", color="#333333", lw=0.8, zorder=1)
    a2.text(us, len(rows2) - 0.35, f"US average\n{us:.0f} g", ha="center", va="bottom", fontsize=7)
    a2.set_yticks(range(len(rows2)), [r[0] for r in rows2[::-1]])
    a2.tick_params(axis="y", length=0)
    a2.set_xlim(320, 520)
    a2.set_ylim(-0.6, len(rows2) + 0.25)
    a2.set_xlabel("Grid carbon intensity where sited,\n2024 (g CO$_2$e/kWh)")
    a2.xaxis.grid(True, color="#e6e6e6", lw=0.5); a2.set_axisbelow(True)
    a2.set_title("(b) Grid carbon, United States", loc="left", fontsize=8.5, fontweight="bold")
    fig.savefig(OUT + "fig7_siting_tests.pdf", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    fig_map()
    fig_tests()
    print("done")
