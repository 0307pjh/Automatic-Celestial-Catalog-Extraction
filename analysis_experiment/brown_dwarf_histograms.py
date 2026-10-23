#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brown Dwarf Parameter Histograms
---------------------------------
Reproduces Figure 4 of the paper: distribution histograms of three key
physical parameters (mass, effective temperature, and orbital semi-major
axis) for the deduplicated brown dwarf sample.

Pipeline: filter IsBrownDwarf == True, deduplicate by simbad_name, and remove
non-physical measurements (mass 13-80 M_Jup, Teff 200-3000 K, SMA 0.01-15 AU).

Input:
    brown_dwarf.csv    (the released literature-centric brown dwarf catalog)

Outputs:
    Figures/brown_dwarf_histograms_3panel.pdf
    Figures/brown_dwarf_histograms_3panel.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import warnings
warnings.filterwarnings('ignore')

# ========== APJ Style ==========
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times"],

    "font.size": 18,
    "axes.labelsize": 24,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "legend.fontsize": 18,
    "axes.titlesize": 20,

    "axes.linewidth": 1.2,
    "xtick.major.width": 1.2,
    "ytick.major.width": 1.2,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,

    "figure.dpi": 300,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def extract_mid_value(val):
    """Extract a numeric value (for ranges, take the midpoint)."""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()

    if re.match(r'^[\d.]+$', val_str):
        try:
            return float(val_str)
        except Exception:
            return np.nan

    match = re.match(r'^[~∼<>≤≥≲≳]\s*([\d.]+)$', val_str)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return np.nan

    if '–' in val_str or '-' in val_str:
        numbers = re.findall(r'[\d.]+', val_str)
        if len(numbers) >= 2:
            try:
                low = float(numbers[0])
                high = float(numbers[-1])
                return (low + high) / 2.0
            except Exception:
                pass

    return np.nan


def extract_value(val):
    """Extract a numeric value directly."""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    try:
        return float(val_str)
    except Exception:
        return np.nan


# ========== Read data ==========
print("=" * 70)
print("Brown Dwarf Sample Parameter Histograms")
print("=" * 70)

df = pd.read_csv('brown_dwarf.csv', low_memory=False)
print(f"Total records: {len(df):,}")

# ========== Step 1: filter IsBrownDwarf == True ==========
print("\n" + "=" * 70)
print("Filtering IsBrownDwarf == True")
print("=" * 70)

if 'IsBrownDwarf' in df.columns:
    before = len(df)
    df = df[df['IsBrownDwarf'].astype(str).str.upper().isin(['TRUE', '1', '1.0'])]
    print(f"  Before: {before:,} rows")
    print(f"  After: {len(df):,} rows (IsBrownDwarf == True)")
    print(f"  Removed: {before - len(df):,} rows (non-brown dwarfs)")
else:
    print("  Warning: no IsBrownDwarf column found; using all data")

if len(df) == 0:
    print("No brown dwarf data!")
    exit()

# ========== Extract key columns ==========
print("\nExtracting numeric values...")

if 'M' in df.columns:
    df['Mass_val'] = df['M'].apply(extract_mid_value)
    print(f"  Mass: {df['Mass_val'].notna().sum():,} valid values")

if 'T_eff' in df.columns:
    df['Teff_val'] = df['T_eff'].apply(extract_value)
    print(f"  T_eff: {df['Teff_val'].notna().sum():,} valid values")

if 'SemiMajorAxis' in df.columns:
    df['SMA_val'] = df['SemiMajorAxis'].apply(extract_mid_value)
    print(f"  SMA: {df['SMA_val'].notna().sum():,} valid values")

# ========== Step 2: deduplicate by simbad_name ==========
print("\n" + "=" * 70)
print("Deduplicating by simbad_name")
print("=" * 70)

if 'simbad_name' in df.columns:
    before = len(df)
    df = df.sort_values(
        by=['simbad_name', 'Mass_val', 'Teff_val', 'SMA_val'],
        ascending=[True, False, False, False],
        na_position='last'
    )
    df = df.drop_duplicates(subset=['simbad_name'], keep='first')
    print(f"  Before: {before:,} rows")
    print(f"  After: {len(df):,} rows")
    print(f"  Removed: {before - len(df):,} rows (duplicates)")
else:
    print("  Warning: no simbad_name column found; falling back to coordinates")
    if 'RA_deg' in df.columns and 'DEC_deg' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['RA_deg', 'DEC_deg'], keep='first')
        print(f"  Before: {before:,} rows")
        print(f"  After: {len(df):,} rows")
    else:
        print("  No deduplication column found; using all data")

if len(df) == 0:
    print("No data after deduplication!")
    exit()

# ========== Step 3: physical boundary cleaning ==========
print("\n" + "=" * 70)
print("Physical boundary cleaning")
print("=" * 70)


def clean_series(series, low, high, name):
    before = series.notna().sum()
    cleaned = series.where((series >= low) & (series <= high))
    after = cleaned.notna().sum()
    print(f"  {name}: {before:,} -> {after:,} (removed {before - after:,} non-physical values)")
    return cleaned


df['Mass_val'] = clean_series(df['Mass_val'], 13, 80, 'Mass  (13-80 M_Jup)')
df['Teff_val'] = clean_series(df['Teff_val'], 200, 3000, 'T_eff (200-3000 K)')
df['SMA_val'] = clean_series(df['SMA_val'], 0.01, 15, 'SMA   (0.01-15 AU)')

# ========== Updated statistics ==========
print("\n" + "=" * 70)
print("Final sample statistics (IsBrownDwarf + dedup + cleaning)")
print("=" * 70)

for col_name, label in [('Mass_val', 'Mass'), ('Teff_val', 'T_eff'), ('SMA_val', 'SMA')]:
    valid = df[col_name].notna().sum()
    print(f"  {label}: {valid:,} valid values")

# ========== Histogram configurations ==========
configs = [
    {
        'name': '(a) Mass',
        'column': 'Mass_val',
        'bins': 30,
        'range': (13, 80),
        'xlim': (13, 80),
        'color': '#4A86E8',
        'xlabel': r'Mass (M$_\mathrm{Jup}$)',
    },
    {
        'name': '(b) Effective Temperature',
        'column': 'Teff_val',
        'bins': 30,
        'range': (200, 3500),
        'xlim': (200, 3000),
        'color': '#E06666',
        'xlabel': r'T$_\mathrm{eff}$ (K)',
    },
    {
        'name': '(c) Semi-Major Axis',
        'column': 'SMA_val',
        'bins': 30,
        'range': (0, 20),
        'xlim': (0, 15),
        'color': '#F57900',
        'xlabel': 'Semi-Major Axis (AU)',
    },
]

# ========== Plot ==========
print("\n" + "=" * 70)
print("Generating histograms...")
print("=" * 70)

fig, axes = plt.subplots(1, 3, figsize=(18, 7))

for i, config in enumerate(configs):
    ax = axes[i]
    data = df[config['column']].dropna()

    if len(data) == 0:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                transform=ax.transAxes, fontsize=20)
        ax.set_title(config['name'], fontsize=20)
        continue

    n, bins, patches = ax.hist(
        data, bins=config['bins'], range=config['range'],
        color=config['color'], edgecolor='black',
        alpha=0.7, linewidth=1.5
    )

    n_count = len(data)
    mean = data.mean()
    median = data.median()

    ax.set_xlabel(config['xlabel'], fontsize=24)
    ax.set_ylabel('Count', fontsize=24)
    ax.set_title(
        f"{config['name']}\nN = {n_count:,}  |  Mean = {mean:.1f}  |  Median = {median:.1f}",
        fontsize=18, fontweight='normal'
    )
    ax.set_xlim(config['xlim'])

    if config['column'] == 'Mass_val':
        ax.set_xticks(np.arange(13, 81, 10))

    # Panel (c): y-axis keeps only 0; x-axis removes the 0 tick (avoid overlap with y-axis 0)
    if i == 2:
        ax.set_yticks([0])
        xticks = [t for t in ax.get_xticks() if abs(t) > 1e-9]
        ax.set_xticks(xticks)

    ax.grid(alpha=0.3, linestyle='--', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(which='both', direction='in', top=True, right=True,
                   labelsize=20, width=1.2, length=6)

plt.tight_layout()

plt.savefig('Figures/brown_dwarf_histograms_3panel.pdf', dpi=300, facecolor='white',
            bbox_inches='tight', pad_inches=0.05)
print("Saved: Figures/brown_dwarf_histograms_3panel.pdf")

plt.savefig('Figures/brown_dwarf_histograms_3panel.png', dpi=300, facecolor='white',
            bbox_inches='tight', pad_inches=0.05)
print("Saved: Figures/brown_dwarf_histograms_3panel.png")

plt.close()

# ========== Statistical summary ==========
print("\n" + "=" * 70)
print("Final statistics (IsBrownDwarf + dedup + cleaning)")
print("=" * 70)

for config in configs:
    data = df[config['column']].dropna()
    if len(data) > 0:
        print(f"\n{config['name']}:")
        print(f"  N      = {len(data):,}")
        print(f"  Min    = {data.min():.2f}")
        print(f"  Max    = {data.max():.2f}")
        print(f"  Mean   = {data.mean():.2f}")
        print(f"  Median = {data.median():.2f}")
        print(f"  Std    = {data.std():.2f}")

print("\n" + "=" * 70)
print("Done!")
