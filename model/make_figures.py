"""Regenerates the paper's five figures from model.py. Greyscale-safe, vector PDF."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import model as m

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "pdf.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
})
NAVY = "#1b3f73"
BLACK, DARK, MID, LIGHT, PALE = "#111111", "#5a5a5a", "#9a9a9a", "#c4c4c4", "#e2e2e2"
EDGE = dict(edgecolor="black", linewidth=0.6)
OUT = "figs/"


def save(fig, name):
    fig.savefig(OUT + name + ".pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig("figs/" + name + ".png", dpi=110,
                bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


# ---------------------------------------------------------------- Fig 1
def fig1():
    rates = [("Internal / small\nfacilities", m.U_SMALL, LIGHT, "black"),
             ("Colocation\nfacilities", m.U_COLO, MID, "black"),
             ("Hyperscale\nfacilities", m.U_HYPER, BLACK, "white")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.55))
    for i, (lab, v, col, tc) in enumerate(rates):
        a1.barh(i, v, height=0.5, color=col, **EDGE)
        a1.text(v - 1, i, f"{v:.1f}%", ha="right", va="center", color=tc, fontweight="bold")
    a1.set_yticks(range(3), [r[0] for r in rates]); a1.tick_params(axis="y", length=0)
    a1.set_xlim(0, 60); a1.set_xlabel("Projected 2031 utilisation (%)")
    a1.set_title("(a) Utilisation by facility type", fontsize=8.5, loc="left")
    u = m.U["central"] * 100
    lf = m.load_factor(m.U["central"], m.IDLE["central"]) * 100
    bars = [("Capacity-weighted\nutilisation", u, PALE), ("Electrical load factor\n(incl. idle power)", lf, DARK)]
    for i, (lab, v, col) in enumerate(bars):
        a2.barh(i, v, height=0.5, color=col, **EDGE)
        a2.text(v + 1, i, f"{v:.1f}%", ha="left", va="center", fontweight="bold")
    a2.set_yticks(range(2), [b[0] for b in bars]); a2.tick_params(axis="y", length=0)
    a2.set_xlim(0, 80); a2.set_xlabel("Fleet, 2031 (%)")
    a2.set_title("(b) Fleet utilisation and load", fontsize=8.5, loc="left")
    for a in (a1, a2):
        a.xaxis.grid(True, color="#e6e6e6", lw=0.5); a.set_axisbelow(True)
    save(fig, "fig1_utilisation")


# ---------------------------------------------------------------- Fig 2
def fig2():
    base = m.central()["co2"]
    spec = [("Base-year calibration", f"ρ = {m.RHO['low']:.2f} to 1", "rho", m.RHO, "white"),
            ("PUE", f"{m.PUE['low']}-{m.PUE['high']}", "pue", m.PUE, BLACK),
            ("Grid carbon intensity", f"{m.GRID['low']}-{m.GRID['high']} g/kWh", "grid", m.GRID, DARK),
            ("Capacity", f"{m.CAP['low']}-{m.CAP['high']} GW", "cap", m.CAP, MID),
            ("Idle power", f"{m.IDLE['low']*100:.0f}-{m.IDLE['high']*100:.0f}% of max", "idle", m.IDLE, LIGHT),
            ("Utilisation", f"{m.U['low']*100:.1f}-{m.U['high']*100:.1f}%", "u", m.U, PALE)]
    rows = []
    for name, rng_lab, key, d, col in spec:
        lo = m.central(**{key: d["low"]})["co2"]
        hi = m.central(**{key: d["high"]})["co2"]
        lo, hi = min(lo, hi), max(lo, hi)
        rows.append((name, rng_lab, lo, hi, (hi - lo) / base * 100, col))
    rows.sort(key=lambda r: r[4])
    fig, ax = plt.subplots(figsize=(6.1, 3.0))
    for i, (name, rl, lo, hi, sw, col) in enumerate(rows):
        hatch = "////" if name.startswith("Base-year") else None
        ax.barh(i, hi - lo, left=lo, height=0.55, color=col, hatch=hatch, **EDGE)
        ax.text(lo - 3, i, f"{lo:.0f} Mt", ha="right", va="center", fontsize=7.5)
        ax.text(hi + 3, i, f"{hi:.0f} Mt", ha="left", va="center", fontsize=7.5)
        ax.text(612, i, f"{sw:.0f}%", ha="right", va="center",
                fontweight="bold" if name == "PUE" else "normal")
    # separate the calibration row from the parameters that describe the 2031 fleet
    ax.axhline(len(rows) - 1.5, color="#888888", lw=0.6, ls=":")
    ax.set_yticks(range(len(rows)), [f"{r[0]}\n{r[1]}" for r in rows])
    ax.tick_params(axis="y", length=0)
    ax.plot([base, base], [-0.5, len(rows) - 0.5], color=NAVY, lw=1.4)
    ax.text(base, len(rows) - 0.35, f"Central estimate: {base:.0f} Mt",
            ha="center", va="bottom", color=NAVY, fontweight="bold")
    ax.set_xlim(215, 615)
    ax.set_ylim(-0.6, len(rows) - 0.3)
    ax.set_xlabel("Annual emissions, 2031 (Mt CO$_2$)")
    ax.xaxis.grid(True, color="#e6e6e6", lw=0.5)
    ax.set_axisbelow(True)
    save(fig, "fig2_sensitivity")


# ---------------------------------------------------------------- Fig 3
def fig3():
    labels = ["New-build,\nPUE 1.04", "Blended fleet,\nPUE 1.30", "Fleet average,\nPUE 1.57"]
    keys = ["low", "central", "high"]
    st = [m.central(pue=m.PUE[k], grid=445)["co2"] for k in keys]
    dc = [m.central(pue=m.PUE[k], grid=345)["co2"] for k in keys]
    fig, ax = plt.subplots(figsize=(5.3, 3.1))
    w = 0.35
    xs = range(3)
    b1 = ax.bar([x - w / 2 for x in xs], st, w, color=BLACK, **EDGE,
                label="Static grid (445 g/kWh)")
    b2 = ax.bar([x + w / 2 for x in xs], dc, w, color=PALE, **EDGE,
                label="Decarbonising grid (345 g/kWh)")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 8,
                    f"{b.get_height():.0f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(list(xs), labels)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("Mt CO$_2$ per year")
    ax.set_ylim(0, 600)
    ax.yaxis.grid(True, color="#e6e6e6", lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2,
              frameon=False, handlelength=1.6)
    save(fig, "fig3_emissions")


# ---------------------------------------------------------------- Fig 4
def fig4():
    keys = ["low", "central", "high"]
    sc = [m.scenario(k) for k in keys]
    direct = [x["water"] for x in sc]
    comb = [x["combined"] for x in sc]
    labels = ["Low", "Central", "High"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9), gridspec_kw=dict(wspace=0.35))
    b = a1.bar(range(3), direct, 0.55, color=BLACK, **EDGE)
    for x, v in zip(range(3), direct):
        a1.text(x, v + 0.04, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)
    a1.set_ylim(0, 2.8); a1.set_ylabel("Trillion litres per year")
    a1.set_title("(a) Direct cooling water (model result)", fontsize=8.5, loc="left")
    a2.bar(range(3), comb, 0.55, color=PALE, **EDGE)
    for x, v in zip(range(3), comb):
        a2.text(x, v - 0.5, f"{v:.1f}", ha="center", va="top", fontsize=7.5)
    a2.plot([-0.5, 2.5], [m.UNU_WATER_TN] * 2, ls="--", color=NAVY, lw=0.9)
    a2.text(-0.42, m.UNU_WATER_TN + 2.2, "UNU-INWEH 2030 projection (9.3)", ha="left", va="bottom", fontsize=7.2, color=NAVY)
    a2.set_xlim(-0.5, 2.5); a2.set_ylim(0, 24)
    a2.set_title("(b) Total water, scaled comparison", fontsize=8.5, loc="left")
    for a in (a1, a2):
        a.set_xticks(range(3), labels); a.tick_params(axis="x", length=0)
        a.yaxis.grid(True, color="#e6e6e6", lw=0.5); a.set_axisbelow(True)
    save(fig, "fig4_water")


# ---------------------------------------------------------------- Fig 5
def fig5():
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    ax.set_xlim(-0.1, 14.0)
    ax.set_ylim(0, 4.3)
    ax.axis("off")

    def box(x, y, w, h, text, shade=False, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="#e6e6e6" if shade else "white", ec="black", lw=0.9))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontweight="bold" if bold else "normal", fontsize=7.8)

    def arrow(x0, y0, x1, y1, lw=1.0):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", lw=lw, color="black",
                                    mutation_scale=9))

    W, H, TOP = 2.9, 0.85, 3.0
    X1, X2, X3 = 0.0, 5.6, 10.6
    box(X1, TOP, W, H, "Installed capacity\n(GW)", shade=True, bold=True)
    box(X2, TOP, W, H, "IT energy\n(TWh)")
    box(X3, TOP, W, H, "Total facility energy\n(TWh)")
    box(X2, 0.3, W, H, "Water consumption\n(litres)", shade=True, bold=True)
    box(X3, 0.3, W, H, "Carbon emissions\n(tonnes CO$_2$)", shade=True, bold=True)

    mid = TOP + H / 2
    arrow(X1 + W, mid, X2, mid)
    ax.text((X1 + W + X2) / 2, mid + 0.1, "× ρ × load factor\n× 8,760 h",
            ha="center", va="bottom", fontsize=7.6)
    ax.text(X1 + W / 2 + 0.6, TOP - 0.2,
            "load factor = idle power share\n+ (1 − idle share) × utilisation\nρ = base-year calibration factor",
            ha="center", va="top", fontsize=7.0, color=NAVY, style="italic")
    arrow(X2 + W, mid, X3, mid)
    ax.text((X2 + W + X3) / 2, mid + 0.1, "× PUE", ha="center", va="bottom", fontsize=7.6)
    arrow(X2 + W / 2, TOP, X2 + W / 2, 0.3 + H)
    ax.text(X2 + W / 2 + 0.12, 2.1, "× WUE", ha="left", va="center", fontsize=7.6)
    arrow(X3 + W / 2, TOP, X3 + W / 2, 0.3 + H, lw=1.8)
    ax.text(X3 + W / 2 + 0.12, 2.1, "× grid carbon\nintensity", ha="left", va="center", fontsize=7.6)
    save(fig, "fig5_chain")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5):
        f()
    print("figures written")
