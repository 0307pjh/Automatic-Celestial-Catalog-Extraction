#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brown dwarf catalog statistical overview - simplified parsing version
Only handles +/- and range formats
Corresponds to Figure 3 of the paper
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ========== Simplified parsing function ==========
def parse_value(value):
    """
    Parse only two formats:
    1. "1000 +/- 100" -> 1000
    2. "120-130" -> 125 (midpoint)
    Others return NaN
    """
    if pd.isna(value) or value == '':
        return np.nan
    
    s = str(value).strip()
    
    # Try direct conversion
    try:
        return float(s)
    except ValueError:
        pass
    
    # Handle +/- format
    if '+' in s:
        parts = s.split('+')
        try:
            return float(parts[0].strip())
        except ValueError:
            pass
    
    # Handle range format
    for sep in ['-', '–', '—']:
        if sep in s:
            parts = s.split(sep)
            if len(parts) == 2:
                try:
                    v1 = float(parts[0].strip())
                    v2 = float(parts[1].strip())
                    return (v1 + v2) / 2
                except ValueError:
                    pass
    
    return np.nan

# ========== Global configuration (ApJ standard) ==========
plt.rcParams.update({
    'font.size': 8,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'Palatino'],
    'axes.labelsize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

# ========== Read data ==========
df = pd.read_csv('brown_dwarf.csv', low_memory=False)
print(f"Original data: {len(df):,} rows")

# Keep only brown dwarfs
df = df[df['IsBrownDwarf'] == 1.0].copy()
print(f"Brown dwarfs: {len(df):,} rows")

# ========== Parse values using simplified parser ==========
print("\nParsing data (supports +/- and range formats)...")

# Apply parsing
df['Teff'] = df['EffectiveTemperature_K'].apply(parse_value)
df['Mass'] = df['Mass_MJ'].apply(parse_value)
df['Radius'] = df['Radius_RJ'].apply(parse_value)

# Parse statistics
def count_valid(series):
    return series.notna().sum()

n_teff_raw = pd.to_numeric(df['EffectiveTemperature_K'], errors='coerce').notna().sum()
n_teff_new = count_valid(df['Teff'])
n_mass_raw = pd.to_numeric(df['Mass_MJ'], errors='coerce').notna().sum()
n_mass_new = count_valid(df['Mass'])
n_radius_raw = pd.to_numeric(df['Radius_RJ'], errors='coerce').notna().sum()
n_radius_new = count_valid(df['Radius'])

print(f"\nParse comparison:")
print(f"   Temperature: {n_teff_raw:,} -> {n_teff_new:,} (+{n_teff_new - n_teff_raw})")
print(f"   Mass: {n_mass_raw:,} -> {n_mass_new:,} (+{n_mass_new - n_mass_raw})")
print(f"   Radius: {n_radius_raw:,} -> {n_radius_new:,} (+{n_radius_new - n_radius_raw})")

# ========== Prepare data for each subplot ==========
data_teff = df[df['Teff'].notna() & (df['Teff'] > 0)].copy()
data_mass = df[df['Mass'].notna() & (df['Mass'] > 0)].copy()
data_tm = df[df['Teff'].notna() & df['Mass'].notna() & 
             (df['Teff'] > 0) & (df['Mass'] > 0)].copy()
data_mr = df[df['Mass'].notna() & df['Radius'].notna() & 
             (df['Mass'] > 0) & (df['Radius'] > 0)].copy()

print(f"\nFinal sample sizes:")
print(f"   (a) Temperature distribution: {len(data_teff):,}")
print(f"   (b) Mass distribution: {len(data_mass):,}")
print(f"   (c) Temperature-Mass: {len(data_tm):,}")
print(f"   (d) Mass-Radius: {len(data_mr):,}")

# ========== Check if data is sufficient ==========
if len(data_teff) < 10:
    print("\nInsufficient temperature data, exiting")
    exit()

# ========== Create four subplots ==========
fig, axes = plt.subplots(2, 2, figsize=(8, 7))

# ---- Subplot 1: Temperature distribution ----
ax = axes[0, 0]
ax.hist(data_teff['Teff'], bins=30, color='#2870B3', 
        edgecolor='white', alpha=0.85)
# L/T boundary (1300K) in red, T/Y boundary (700K) in orange
ax.axvline(1300, color='#D62728', linestyle='--', linewidth=1.5, label='T/L (1300 K)')
ax.axvline(700, color='#FF7F0E', linestyle='--', linewidth=1.5, label='Y/T (700 K)')
ax.set_xlabel('Effective Temperature (K)', fontsize=9)
ax.set_ylabel('Number', fontsize=9)
ax.set_title(f'(a) Temperature Distribution (N={len(data_teff)})', fontsize=10)

# Adjust legend order
handles, labels = ax.get_legend_handles_labels()
order = [1, 0]
ax.legend([handles[i] for i in order], [labels[i] for i in order], 
          fontsize=7, frameon=True)
ax.tick_params(labelsize=7)

# ---- Subplot 2: Mass distribution ----
ax = axes[0, 1]
ax.hist(data_mass['Mass'], bins=30, color='#3465a4', 
        edgecolor='white', alpha=0.85)
ax.axvline(13, color='#D62728', linestyle='--', linewidth=1.5, label='13 M$_J$ (D-burning)')
ax.axvline(60, color='#2CA02C', linestyle='--', linewidth=1.5, label='60 M$_J$ (H-burning)')
ax.set_xlabel('Mass (M$_{\\rm Jup}$)', fontsize=9)
ax.set_ylabel('Number', fontsize=9)
ax.set_title(f'(b) Mass Distribution (N={len(data_mass)})', fontsize=10)
ax.legend(fontsize=7, frameon=True)
ax.tick_params(labelsize=7)

# ---- Subplot 3: Temperature-Mass relation ----
ax = axes[1, 0]
if len(data_tm) > 5:
    scatter = ax.scatter(data_tm['Mass'], data_tm['Teff'],
                         c=data_tm['Teff'], cmap='hot_r',
                         s=20, alpha=0.7, edgecolors='none')
    ax.set_xlabel('Mass (M$_{\\rm Jup}$)', fontsize=9)
    ax.set_ylabel('Effective Temperature (K)', fontsize=9)
    ax.set_title(f'(c) Temperature vs Mass (N={len(data_tm)})', fontsize=10)
    ax.invert_yaxis()
    ax.tick_params(labelsize=7)
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.06, pad=0.03)
    cbar.set_label('Teff (K)', fontsize=7)
else:
    ax.text(0.5, 0.5, f'Insufficient data\n(N={len(data_tm)})', 
            ha='center', va='center', transform=ax.transAxes)

# ---- Subplot 4: Mass-Radius relation ----
ax = axes[1, 1]
if len(data_mr) > 5:
    scatter2 = ax.scatter(data_mr['Mass'], data_mr['Radius'],
                          c=data_mr['Teff'] if 'Teff' in data_mr.columns else 'blue',
                          cmap='plasma', s=20, alpha=0.7, edgecolors='none')
    ax.set_xlabel('Mass (M$_{\\rm Jup}$)', fontsize=9)
    ax.set_ylabel('Radius (R$_{\\rm Jup}$)', fontsize=9)
    ax.set_title(f'(d) Mass-Radius Relation (N={len(data_mr)})', fontsize=10)
    ax.tick_params(labelsize=7)
    if 'Teff' in data_mr.columns:
        cbar2 = plt.colorbar(scatter2, ax=ax, fraction=0.06, pad=0.03)
        cbar2.set_label('Teff (K)', fontsize=7)
else:
    ax.text(0.5, 0.5, f'Insufficient data\n(N={len(data_mr)})', 
            ha='center', va='center', transform=ax.transAxes)

# ---- Layout ----
plt.tight_layout()

# ========== Save ==========
output_file = 'catalog_summary.pdf'
plt.savefig(output_file, format='pdf', dpi=300, bbox_inches='tight')
print(f"\nSaved: {output_file}")

# ========== Summary statistics ==========
print("\n" + "="*70)
print("Final Statistics Summary")
print("="*70)
if len(data_teff) > 0:
    print(f"  Temperature median: {data_teff['Teff'].median():.0f} K")
    print(f"  Temperature range: {data_teff['Teff'].min():.0f} - {data_teff['Teff'].max():.0f} K")
if len(data_mass) > 0:
    print(f"  Mass median: {data_mass['Mass'].median():.2f} M_J")
    print(f"  Mass range: {data_mass['Mass'].min():.2f} - {data_mass['Mass'].max():.2f} M_J")
if len(data_tm) > 5:
    print(f"  Temp-Mass correlation: {data_tm['Teff'].corr(data_tm['Mass']):.3f}")
if len(data_mr) > 5:
    print(f"  Mass-Radius correlation: {data_mr['Mass'].corr(data_mr['Radius']):.3f}")
print("="*70)

# ================================================================
# ========== Temperature bin statistics ==========
# ================================================================
print("\n" + "="*70)
print("Temperature Bin Statistics")
print("="*70)

bins = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
labels = ['0-500 K', '500-1000 K', '1000-1500 K', '1500-2000 K', 
          '2000-2500 K', '2500-3000 K', '3000-3500 K']

data_teff['temp_bin'] = pd.cut(data_teff['Teff'], bins=bins, labels=labels, right=False)
bin_counts = data_teff['temp_bin'].value_counts().sort_index()
bin_percentages = (bin_counts / len(data_teff) * 100).round(2)

print(f"\n{'Temp Range':<18} {'Count':>10} {'Percentage':>12}")
print("-" * 42)
for label in labels:
    count = bin_counts.get(label, 0)
    pct = bin_percentages.get(label, 0)
    print(f"{label:<18} {count:>10,} {pct:>11.2f}%")
print("-" * 42)
print(f"{'Total':<18} {len(data_teff):>10,} {'100.00%':>12}")

# ================================================================
# ========== Spectral type bin statistics ==========
# ================================================================
print("\n" + "="*70)
print("Spectral Type Bin Statistics")
print("="*70)

bins_spec = [0, 700, 1300, 10000]
labels_spec = ['Y-type (0-700 K)', 'T-type (700-1300 K)', 'L-type (>1300 K)']

data_teff['spec_bin'] = pd.cut(data_teff['Teff'], bins=bins_spec, labels=labels_spec, right=False)
spec_counts = data_teff['spec_bin'].value_counts().sort_index()
spec_pcts = (spec_counts / len(data_teff) * 100).round(2)

print(f"\n{'Spectral Type':<18} {'Count':>10} {'Percentage':>12}")
print("-" * 42)
for label in labels_spec:
    count = spec_counts.get(label, 0)
    pct = spec_pcts.get(label, 0)
    print(f"{label:<18} {count:>10,} {pct:>11.2f}%")
print("-" * 42)
print(f"{'Total':<18} {len(data_teff):>10,} {'100.00%':>12}")

print("\n" + "="*70)
print("Done!")
