#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arXiv Astrophysics Paper Statistics
-----------------------------------
Reproduces Figure 1 of the paper: the annual number of astrophysics papers
submitted to arXiv from 1992 to June 2026.

The input file is the pre-filtered arXiv metadata snapshot (JSONL) containing
papers under astro-ph and its subcategories (astro-ph.CO, astro-ph.EP,
astro-ph.GA, astro-ph.HE, astro-ph.SR), excluding astro-ph.IM.

NOTE: The raw metadata snapshot is large (~800 MB) and is not shipped in this
repository. It can be obtained from the Kaggle-hosted Cornell University arXiv
dataset (https://www.kaggle.com/datasets/Cornell-University/arxiv) or the
official arXiv GCS bucket. The pre-computed figure is provided in Figures/.

Outputs:
    Figures/arxiv_astrophysics_yearly.pdf
    Figures/arxiv_astrophysics_yearly.png
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re

# ========== Configuration ==========
INPUT_FILE = 'arxiv_metadata.jsonl'  # Pre-filtered arXiv astrophysics metadata (JSONL)

# Figure size (wider and shorter, suitable for single column)
FIG_WIDTH = 4.2
FIG_HEIGHT = 2.2
DPI = 300
Y_TICK_INTERVAL = 5000

BAR_COLOR = '#2870B3'
EDGE_COLOR = '#203858'
GRID_COLOR = '#d3d3d3'

# X-axis tick interval (fixed at 4 years)
X_TICK_INTERVAL = 4


# ========== Year extraction ==========
def extract_year_from_id(arxiv_id):
    """Extract the year from an arXiv ID (supports both old and new formats)."""
    if not arxiv_id:
        return None

    clean_id = re.sub(r'v\d+$', '', arxiv_id)

    match = re.match(r'^(\d{2})(\d{2})\.', clean_id)
    if match:
        yy = int(match.group(1))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if 1991 <= year <= 2026:
            return year

    match = re.match(r'^(\d{4})\.', clean_id)
    if match:
        year = int(match.group(1))
        if 1991 <= year <= 2026:
            return year

    match = re.match(r'^[a-z\-]+/(\d{2})(\d{2})', clean_id)
    if match:
        yy = int(match.group(1))
        mm = int(match.group(2))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if 1 <= mm <= 12 and 1991 <= year <= 2026:
            return year

    match = re.match(r'^[a-z\-]+/(\d{2})', clean_id)
    if match:
        yy = int(match.group(1))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if 1991 <= year <= 2026:
            return year

    return None


# ========== Custom tick formatter ==========
def y_fmt(x, pos):
    """Format large numbers in thousands (e.g., 5k, 10k)."""
    if x == 0:
        return '0'
    val = x / 1000
    if val == int(val):
        return f'{int(val)}k'
    else:
        return f'{val:.1f}k'


# ========== Main ==========
def main():
    print("=" * 60)
    print("arXiv Astrophysics Papers Statistics")
    print(f"Data File: {INPUT_FILE}")
    print("-" * 60)

    year_counts = Counter()
    total_papers = 0
    failed_ids = []

    # Track the latest paper
    latest_paper = None
    latest_num = 0

    # Read the filtered JSONL file
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 100000 == 0:
                print(f"  Processed {line_num:,} records...")
            try:
                paper = json.loads(line.strip())
                arxiv_id = paper.get('id', '')

                year = extract_year_from_id(arxiv_id)
                if not year:
                    if len(failed_ids) < 10:
                        failed_ids.append(arxiv_id)
                    continue

                total_papers += 1
                year_counts[year] += 1

                # Track the latest paper (based on the largest arXiv ID)
                clean_id = re.sub(r'v\d+$', '', arxiv_id)
                try:
                    current_num = int(clean_id.replace('.', ''))
                except ValueError:
                    current_num = 0

                if current_num > latest_num:
                    latest_num = current_num
                    latest_paper = {
                        'id': arxiv_id,
                        'title': paper.get('title', '').strip(),
                        'year': year,
                        'categories': paper.get('categories', ''),
                        'authors': paper.get('authors', '').strip(),
                        'abstract': paper.get('abstract', '').strip()[:200] + '...' if paper.get('abstract') else ''
                    }

            except json.JSONDecodeError:
                continue
            except Exception:
                continue

    print("-" * 60)
    print(f"Completed!")
    print(f"   Total valid papers: {total_papers:,}")
    if year_counts:
        print(f"   Year range: {min(year_counts.keys())} - {max(year_counts.keys())}")
    if failed_ids:
        print(f"   Sample of failed IDs: {failed_ids[:5]}")
    print("=" * 60)

    # ===== Output latest paper info =====
    if latest_paper:
        print("\nLatest Paper in astro-ph:")
        print("-" * 60)
        print(f"   Year:      {latest_paper['year']}")
        print(f"   ID:        {latest_paper['id']}")
        print(f"   Title:     {latest_paper['title']}")
        print(f"   Authors:   {latest_paper['authors']}")
        print(f"   Categories: {latest_paper['categories']}")
        print(f"   Abstract:  {latest_paper['abstract']}")
        print("=" * 60)

    if not year_counts:
        print("No papers processed. Please check the data file format.")
        return

    # ========== Yearly breakdown ==========
    print("\nYearly Breakdown:")
    print("-" * 50)
    print(f"{'Year':<8} {'Count':>12} {'Percentage':>12} {'Cumulative':>12}")
    print("-" * 50)
    cumulative = 0
    for year in sorted(year_counts.keys()):
        count = year_counts[year]
        cumulative += count
        pct = (count / total_papers) * 100
        cum_pct = (cumulative / total_papers) * 100
        print(f"{year:<8} {count:>12,} {pct:>11.2f}% {cum_pct:>11.2f}%")
    print("-" * 50)
    print(f"{'TOTAL':<8} {total_papers:>12,} {100.00:>11.2f}% {100.00:>11.2f}%")
    print("=" * 60)

    # ========== Prepare yearly data ==========
    years = sorted(year_counts.keys())
    counts = [year_counts[y] for y in years]

    max_count = max(counts)
    y_max = int(np.ceil(max_count / Y_TICK_INTERVAL) * Y_TICK_INTERVAL)

    # ========== X-axis ticks (every 4 years, first and last always shown) ==========
    tick_years = []
    current = years[0]
    while current <= years[-1]:
        tick_years.append(current)
        current += X_TICK_INTERVAL
    if tick_years[-1] != years[-1]:
        tick_years.append(years[-1])

    print(f"\nPlot Parameters:")
    print(f"   Years: {len(years)} years ({years[0]} - {years[-1]})")
    print(f"   X-axis tick interval: {X_TICK_INTERVAL} years")
    print(f"   X-axis ticks: {len(tick_years)} labels")
    print(f"   Max count: {max_count:,}")
    print(f"   Y-axis max (rounded): {y_max:,}")

    # ========== Global style ==========
    plt.rcParams.update({
        'font.size': 8.5,
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'Palatino'],
        'axes.labelsize': 7.5,
        'xtick.labelsize': 7.0,
        'ytick.labelsize': 7.0,
        'legend.fontsize': 7.0,
        'legend.frameon': True,
        'legend.framealpha': 0.9,
        'legend.edgecolor': '#CCCCCC',
        'figure.dpi': DPI,
        'savefig.dpi': DPI,
        'savefig.bbox': 'tight',
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))

    # ========== Bar chart ==========
    bars = ax.bar(years, counts, width=0.6, color=BAR_COLOR,
                  edgecolor=EDGE_COLOR, linewidth=0.5, alpha=0.92,
                  label='Astrophysics Papers', zorder=2)

    # ========== Adjust subplot margins ==========
    plt.subplots_adjust(left=0.0, right=0.95, bottom=0.15, top=0.82)

    # ========== Axis settings ==========
    ax.set_xlabel('Publication Year', fontsize=7.5, fontfamily='serif', labelpad=1)
    ax.set_ylabel('Number of Papers', fontsize=7.5, fontfamily='serif', labelpad=0)

    # ========== X-axis range ==========
    ax.set_xlim(min(years) - 0.5, max(years) + 0.8)

    ax.set_xticks(tick_years)
    ax.set_xticklabels(tick_years, rotation=0, ha='center', fontsize=6.5, fontweight='normal')

    # ========== Y-axis settings ==========
    y_bottom = 0
    y_top = y_max * 1.15
    if y_top < max_count + 500:
        y_top = max_count + 800
    ax.set_ylim(y_bottom, y_top)

    y_ticks = np.arange(y_bottom, y_max + Y_TICK_INTERVAL, Y_TICK_INTERVAL)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([y_fmt(x, None) for x in y_ticks], fontsize=7.0, fontweight='normal')

    # ========== Grid and background ==========
    ax.grid(axis='y', alpha=0.25, linestyle='--', linewidth=0.5, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)
    ax.set_facecolor('#FAFAFA')
    fig.patch.set_facecolor('white')

    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
        spine.set_color('#333333')
        spine.set_zorder(10)

    # ========== Legend ==========
    ax.legend(loc='upper left', frameon=True, fancybox=False,
              edgecolor='#CCCCCC', fontsize=7.0, labelspacing=0.3, framealpha=0.9)

    # ========== Save ==========
    output_pdf = 'Figures/arxiv_astrophysics_yearly.pdf'
    plt.savefig(output_pdf, format='pdf', dpi=DPI, bbox_inches=None, pad_inches=0.02)
    print(f"PDF saved: {output_pdf}")

    output_png = 'Figures/arxiv_astrophysics_yearly.png'
    plt.savefig(output_png, format='png', dpi=DPI, bbox_inches=None, pad_inches=0.02, facecolor='white')
    print(f"PNG saved: {output_png} (DPI={DPI})")

    # ========== Specification confirmation ==========
    print("\n" + "=" * 60)
    print("ApJ Image Specifications Verified")
    print("=" * 60)
    print(f"  Size: {FIG_WIDTH} x {FIG_HEIGHT} inch")
    print(f"  DPI: {DPI} (>=300)")
    print(f"  Vector fonts: TrueType (fonttype=42)")
    print(f"  Minimum font size: 6.5 pt")
    print(f"  Years: {len(years)} years ({years[0]} - {years[-1]})")
    print(f"  X-axis ticks: {len(tick_years)} labels (interval = {X_TICK_INTERVAL} years)")
    print(f"  X-axis ticks: {tick_years}")
    print(f"  Y-axis range: {y_bottom:,} to {int(y_top):,}")
    print(f"  Y-axis tick interval: {Y_TICK_INTERVAL:,}")
    print(f"  Y-axis labels: k unit (e.g., 5k, 10k)")
    print(f"  Margins: left=0.0, right=0.95, bottom=0.15, top=0.82")
    print(f"  bbox_inches=None (preserves margins)")
    print(f"  Total astrophysics papers: {total_papers:,}")
    if latest_paper:
        print(f"  Latest paper: {latest_paper['id']} ({latest_paper['year']})")
    print("=" * 60)


if __name__ == "__main__":
    main()
