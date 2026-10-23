#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Comparison
-------------------
Reproduces Figure 3 of the paper: comparison of the number of brown dwarfs
contained in our catalog and several representative public databases.

Our catalog contains 14,682 unique brown dwarfs after deduplication by
simbad_name, of which 5,286 are retrievable in SIMBAD and are shown as the
"Our Work" bar. Counts for the comparison databases follow the paper:
UltracoolSheet (latest release, updated 2025 July), SIMBAD (ADQL query with
otype 'BD*' and 'BD?', accessed 2026 September: 3,762 confirmed + 12,058
candidates), SIMPLE Archive (official website statistics), and CASPAR
(published catalog, 2023 October).

Outputs:
    Figures/database_comparison.pdf
    Figures/database_comparison.png
"""

import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.patches import Patch

# ==========================
# Data
# ==========================
databases = [
    'Our Work',
    'SIMPLE Archive',
    'UltracoolSheet',
    'CASPAR',
    'SIMBAD Confirmed',
    'SIMBAD Candidate',
]
counts = [5286, 3632, 3956, 133, 3762, 12058]

# ==========================
# Sort (descending)
# ==========================
sorted_idx = np.argsort(counts)[::-1]
databases = [databases[i] for i in sorted_idx]
counts = [counts[i] for i in sorted_idx]

# ==========================
# APJ Style
# ==========================
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times"],
    "font.size": 13,
    "axes.labelsize": 13,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.fontsize": 13,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.constrained_layout.use": True,
})

# ==========================
# Figure
# ==========================
fig, ax = plt.subplots(figsize=(10, 7))

Y_TOP = 20000

color_map = {
    'Our Work':         '#1565C0',
    'SIMPLE Archive':   '#F4A6A6',
    'UltracoolSheet':   '#A8D5A2',
    'CASPAR':           '#FBC98A',
    'SIMBAD Confirmed': '#C9A8D4',
    'SIMBAD Candidate': '#9ED9E0',
}
fallback_color = '#D9D9D9'
colors = [color_map.get(db, fallback_color) for db in databases]

bars = ax.bar(
    databases,
    counts,
    width=0.50,
    color=colors,
    edgecolor="black",
    linewidth=1.0,
)

# ==========================
# Value labels
# ==========================
for i, (bar, value) in enumerate(zip(bars, counts)):
    fontweight = "bold" if databases[i] == 'Our Work' else "normal"
    label_y = value * 1.15

    if label_y > Y_TOP:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value * 0.92,
            f"{value:,}",
            ha="center", va="top",
            fontsize=13,
            color="white" if databases[i] == 'Our Work' else "black",
            fontweight=fontweight,
        )
    else:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            label_y,
            f"{value:,}",
            ha="center", va="bottom",
            fontsize=13,
            color="black",
            fontweight=fontweight,
        )

# ==========================
# Axis labels
# ==========================
ax.set_ylabel("Number of Brown Dwarfs", fontsize=13)
ax.set_xlabel("Database", fontsize=13)

# ==========================
# Grid
# ==========================
ax.grid(axis="y", linestyle=":", linewidth=0.8, color="0.7")
ax.set_axisbelow(True)

# ==========================
# Axis range (log scale)
# ==========================
ax.set_yscale("log")
ax.set_ylim(100, Y_TOP)

# ==========================
# Tick style
# ==========================
ax.tick_params(
    which="both", direction="in",
    top=True, right=True,
    labelsize=13, width=1.0, length=6,
)
ax.set_yticks([100, 200, 500, 1000, 2000, 5000, 10000, 20000])
ax.set_yticklabels(['100', '200', '500', '1,000', '2,000', '5,000', '10,000', '20,000'])

ax.set_xticks(range(len(databases)))
ax.set_xticklabels([])

# ==========================
# Legend
# ==========================
legend_handles = [
    Patch(facecolor=color_map.get(db, fallback_color),
          edgecolor='black', label=db)
    for db in databases
]
ax.legend(
    handles=legend_handles,
    loc='upper right',
    ncol=2,
    frameon=True,
    framealpha=0.95,
    edgecolor='black',
    fontsize=13,
    borderpad=0.5,
    labelspacing=0.4,
    columnspacing=0.8,
)

# ==========================
# Statistical summary
# ==========================
total = sum(counts)
mean = np.mean(counts)
median = np.median(counts)
summary_text = f'Total: {total:,}  |  Mean: {mean:,.0f}  |  Median: {median:,.0f}'

ax.text(
    0.5, -0.15, summary_text,
    transform=ax.transAxes,
    ha='center', fontsize=13, style='italic',
)

# ==========================
# Save
# ==========================
plt.tight_layout()
plt.savefig("Figures/database_comparison.pdf", format='pdf', dpi=300,
            bbox_inches="tight", pad_inches=0.05)
plt.savefig("Figures/database_comparison.png", format='png', dpi=300,
            bbox_inches="tight", pad_inches=0.05)
plt.close()

print("=" * 60)
print("FIGURE SAVED SUCCESSFULLY")
print("=" * 60)
print("PDF:  Figures/database_comparison.pdf")
print("PNG:  Figures/database_comparison.png")
print("\nFile sizes:")
for f in ["Figures/database_comparison.pdf", "Figures/database_comparison.png"]:
    if os.path.exists(f):
        size = os.path.getsize(f) / 1024
        print(f"  {f}: {size:.1f} KB")
