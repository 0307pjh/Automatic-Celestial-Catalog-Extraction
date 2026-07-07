#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brown dwarf mass-semi-major axis distribution (occurrence rate plot)
APJ submission format - only shows samples with complete uncertainties
Modifications:
1. Strictly use Mass instead of M sin i
2. X-axis range changed to 2 au - 20 au
3. Exclude samples with Type = Binary
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde, pearsonr, spearmanr
from matplotlib.ticker import FuncFormatter
import re
import warnings
warnings.filterwarnings('ignore')

# ========== Global configuration ==========
plt.rcParams.update({
    'font.size': 8.5,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'Palatino'],
    'axes.labelsize': 9.0,
    'xtick.labelsize': 7.0,
    'ytick.labelsize': 7.0,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

# ========== Extract numeric values ==========
def extract_mid_value(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    try:
        return float(val_str)
    except:
        pass
    if '-' in val_str or '–' in val_str:
        numbers = re.findall(r'[\d.]+', val_str)
        if len(numbers) >= 2:
            try:
                return (float(numbers[0]) + float(numbers[-1])) / 2.0
            except:
                pass
    match = re.match(r'^[~∼<>]\s*([\d.]+)$', val_str)
    if match:
        try:
            return float(match.group(1))
        except:
            pass
    return np.nan

# ========== Read data ==========
print("="*70)
print("Loading data")
print("="*70)

df = pd.read_csv('brown_dwarf.csv', low_memory=False)
print(f"Original data: {len(df):,} rows")

# Keep only brown dwarfs
df = df[df['IsBrownDwarf'] == 1.0].copy()
print(f"Brown dwarfs: {len(df):,} rows")

# ========== Exclude Binary type ==========
print("\n" + "="*70)
print("Type filtering (excluding Binary)")
print("="*70)

type_col = 'Type'
if type_col in df.columns:
    df['Type'] = df[type_col].astype(str).str.strip()
    before = len(df)
    df = df[df['Type'] != 'Binary']
    print(f"  Before excluding Binary: {before:,}")
    print(f"  After excluding Binary: {len(df):,}")
else:
    print(f"Warning: Column '{type_col}' not found, skipping type filter.")

# ========== Extract values ==========
print("\nExtracting numeric values...")

df['Mass'] = df['Mass_MJ'].apply(extract_mid_value)
df['Mass_Err_Plus'] = df['Mass_MJ_Error_Plus'].apply(extract_mid_value)
df['Mass_Err_Minus'] = df['Mass_MJ_Error_Minus'].apply(extract_mid_value)
df['SMA_raw'] = df['SemiMajorAxis_AU'].apply(extract_mid_value)
df['SMA_Err_Plus'] = df['SemiMajorAxis_AU_Error_Plus'].apply(extract_mid_value)
df['SMA_Err_Minus'] = df['SemiMajorAxis_AU_Error_Minus'].apply(extract_mid_value)

# ========== Unit conversion ==========
print("\nConverting units...")

R_SUN_TO_AU = 0.00465047

def convert_sma(value, unit):
    if pd.isna(value) or pd.isna(unit):
        return np.nan
    unit_str = str(unit).strip()
    if unit_str in ['AU', 'au']:
        return value
    elif unit_str == 'R_sun':
        return value * R_SUN_TO_AU
    elif unit_str == 'arcsec':
        return np.nan
    else:
        return np.nan

df['SMA'] = df.apply(lambda row: convert_sma(row['SMA_raw'], row['SemiMajorAxis_AU_unit']), axis=1)

print(f"  Mass: {df['Mass'].notna().sum():,} valid values")
print(f"  Semi-major axis (AU): {df['SMA'].notna().sum():,} valid values")

# ========== Data cleaning ==========
print("\n" + "="*70)
print("Data cleaning")
print("="*70)

df_clean = df.dropna(subset=['Mass', 'SMA'])
df_clean = df_clean[(df_clean['Mass'] > 0) & (df_clean['SMA'] > 0)]
df_clean = df_clean[np.isfinite(df_clean['Mass'])]
df_clean = df_clean[np.isfinite(df_clean['SMA'])]

print(f"After cleaning: {len(df_clean):,} samples")

if len(df_clean) < 10:
    print("Insufficient data, exiting")
    exit()

# ========== Set plot range ==========
X_MIN, X_MAX = 2, 20
Y_MIN, Y_MAX = 2, 110
MASS_THRESHOLD = 30

data_for_plot = df_clean[
    (df_clean['SMA'] >= X_MIN) & 
    (df_clean['SMA'] <= X_MAX) & 
    (df_clean['Mass'] >= Y_MIN) & 
    (df_clean['Mass'] <= Y_MAX)
].copy()

print(f"Within plot range (2-20 AU): {len(data_for_plot):,} samples")

if len(data_for_plot) < 10:
    print("Insufficient data within plot range, exiting")
    exit()

# ========== Keep only samples with complete uncertainties ==========
print("\n" + "="*70)
print("Filtering samples with complete uncertainties")
print("="*70)

mask_complete = (
    data_for_plot['Mass_Err_Plus'].notna() &
    data_for_plot['Mass_Err_Minus'].notna() &
    data_for_plot['SMA_Err_Plus'].notna() &
    data_for_plot['SMA_Err_Minus'].notna()
)

data_plot = data_for_plot[mask_complete].copy()
print(f"  Original samples: {len(data_for_plot):,}")
print(f"  With complete uncertainties: {len(data_plot):,}")
print(f"  Removed: {len(data_for_plot) - len(data_plot):,} (missing errors)")

if len(data_plot) < 10:
    print("Insufficient samples with complete uncertainties, exiting")
    exit()

# Split high mass and low mass
high_mass = data_plot[data_plot['Mass'] >= MASS_THRESHOLD]
low_mass = data_plot[data_plot['Mass'] < MASS_THRESHOLD]

# ========== Binning statistics ==========
N_BINS = 12
bins = np.logspace(np.log10(X_MIN), np.log10(X_MAX), N_BINS)
counts_c, _ = np.histogram(high_mass['SMA'], bins=bins)
counts_d, _ = np.histogram(low_mass['SMA'], bins=bins)
bin_centers = (bins[:-1] + bins[1:]) / 2

# ========== Detailed statistics output ==========
print("\n" + "="*70)
print("Detailed statistics (samples with complete uncertainties)")
print("="*70)

# 1. Mass statistics
print("\n[Mass distribution]")
print(f"  Sample count: {len(data_plot)}")
print(f"  Minimum: {data_plot['Mass'].min():.2f} M_J")
print(f"  Maximum: {data_plot['Mass'].max():.2f} M_J")
print(f"  Mean: {data_plot['Mass'].mean():.2f} M_J")
print(f"  Median: {data_plot['Mass'].median():.2f} M_J")
print(f"  Std: {data_plot['Mass'].std():.2f} M_J")

# 2. Semi-major axis statistics
print("\n[Semi-major axis distribution]")
print(f"  Sample count: {len(data_plot)}")
print(f"  Minimum: {data_plot['SMA'].min():.3f} AU")
print(f"  Maximum: {data_plot['SMA'].max():.3f} AU")
print(f"  Mean: {data_plot['SMA'].mean():.3f} AU")
print(f"  Median: {data_plot['SMA'].median():.3f} AU")
print(f"  Std: {data_plot['SMA'].std():.3f} AU")

# 3. Correlation analysis
print("\n[Correlation analysis]")
corr_pearson, p_pearson = pearsonr(data_plot['SMA'], data_plot['Mass'])
corr_spearman, p_spearman = spearmanr(data_plot['SMA'], data_plot['Mass'])
print(f"  Pearson correlation: {corr_pearson:.4f} (p = {p_pearson:.4e})")
print(f"  Spearman correlation: {corr_spearman:.4f} (p = {p_spearman:.4e})")

# 4. Mass bin statistics
print("\n[Mass bin statistics]")
mass_bins = [2, 5, 10, 20, 30, 40, 60, 80, 110]
mass_labels = ['2-5', '5-10', '10-20', '20-30', '30-40', '40-60', '60-80', '80-110']
data_plot['mass_bin'] = pd.cut(data_plot['Mass'], bins=mass_bins, labels=mass_labels, right=False)

for label in mass_labels:
    subset = data_plot[data_plot['mass_bin'] == label]
    if len(subset) > 0:
        print(f"  {label:>8} M_J: {len(subset):>4} ({len(subset)/len(data_plot)*100:>5.1f}%)")

# 5. Semi-major axis bin statistics
print("\n[Semi-major axis bin statistics]")
sma_bins = [2, 5, 10, 20]
sma_labels = ['2-5', '5-10', '10-20']
data_plot['sma_bin'] = pd.cut(data_plot['SMA'], bins=sma_bins, labels=sma_labels, right=False)

for label in sma_labels:
    subset = data_plot[data_plot['sma_bin'] == label]
    if len(subset) > 0:
        print(f"  {label:>10} AU: {len(subset):>4} ({len(subset)/len(data_plot)*100:>5.1f}%)")

# 6. High vs low mass comparison
print("\n[High vs low mass comparison]")
print(f"  High mass (>=30 M_J): {len(high_mass):>4} ({len(high_mass)/len(data_plot)*100:>5.1f}%)")
print(f"  Low mass (<30 M_J):  {len(low_mass):>4} ({len(low_mass)/len(data_plot)*100:>5.1f}%)")

# 7. Error statistics
print("\n[Error statistics]")
mass_err_plus = data_plot['Mass_Err_Plus'].dropna()
mass_err_minus = data_plot['Mass_Err_Minus'].dropna()
sma_err_plus = data_plot['SMA_Err_Plus'].dropna()
sma_err_minus = data_plot['SMA_Err_Minus'].dropna()

print(f"  Mass error upper: median {mass_err_plus.median():.3f} M_J")
print(f"  Mass error lower: median {mass_err_minus.median():.3f} M_J")
print(f"  SMA error upper: median {sma_err_plus.median():.3f} AU")
print(f"  SMA error lower: median {sma_err_minus.median():.3f} AU")

# ========== KDE calculation function ==========
def calculate_kde(x, y):
    if len(x) < 5:
        return None, None, None
    valid_mask = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
    x, y = x[valid_mask], y[valid_mask]
    if len(x) < 2:
        return None, None, None
    try:
        xx, yy = np.mgrid[np.log10(X_MIN):np.log10(X_MAX):100j,
                          np.log10(Y_MIN):np.log10(Y_MAX):100j]
        positions = np.vstack([xx.ravel(), yy.ravel()])
        values = np.vstack([np.log10(x), np.log10(y)])
        kernel = gaussian_kde(values)
        f = np.reshape(kernel(positions).T, xx.shape)
        return xx, yy, f
    except:
        return None, None, None

# ========== Tick formatter function ==========
def format_func(value, tick_number):
    if value in [5, 10, 25, 50, 100]:
        return f'{int(value)}'
    return ''

# ========== Figure layout ==========
print("\nRendering figure...")
fig = plt.figure(figsize=(12, 10))

gs = fig.add_gridspec(3, 2, 
                       height_ratios=[1, 3.5, 1], 
                       width_ratios=[1, 4],       
                       hspace=0, wspace=0)

# --- (c) Top panel (high mass occurrence rate) ---
ax_c = fig.add_subplot(gs[0, 1])
ax_c.errorbar(bin_centers, counts_c, yerr=np.sqrt(counts_c), fmt='s-', color='#d62728',
              ecolor='#d62728', capsize=3, markersize=4, label=r'$30 \leq m < 120 M_J$')
ax_c.set_xscale('log')
ax_c.set_xlim(X_MIN, X_MAX)
ax_c.set_ylabel('occurrence rate')
ax_c.legend(frameon=False, fontsize=10, loc='lower center')
ax_c.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
ax_c.text(0.02, 0.95, '(c)', transform=ax_c.transAxes, fontsize=14, 
          fontweight='bold', va='top', ha='left')

# --- (a) Main panel (scatter + heatmap) ---
ax_a = fig.add_subplot(gs[1, 1])
x = data_plot['SMA'].values
y = data_plot['Mass'].values

# Mass errors
y_err_upper = data_plot['Mass_Err_Plus'].values
y_err_lower = data_plot['Mass_Err_Minus'].values
y_err = [y_err_lower, y_err_upper]

# SMA errors
x_err_upper = data_plot['SMA_Err_Plus'].values
x_err_lower = data_plot['SMA_Err_Minus'].values
x_err = [x_err_lower, x_err_upper]

# Heatmap
xx, yy, f = calculate_kde(x, y)
if f is not None:
    ax_a.contourf(10 ** xx, 10 ** yy, f, levels=15, cmap='viridis', alpha=0.9, zorder=0)

# Scatter with error bars
ax_a.errorbar(x, y, xerr=x_err, yerr=y_err, fmt='o', color='white', 
              ecolor='white', elinewidth=1.3, capsize=1.5, capthick=1.2,
              markersize=3,
              zorder=1, alpha=0.7)

ax_a.set_xscale('log')
ax_a.set_yscale('log')
ax_a.set_xlim(X_MIN, X_MAX)
ax_a.set_ylim(Y_MIN, Y_MAX)

# Hide ticks and labels
ax_a.set_xticks([])
ax_a.set_yticks([])
ax_a.tick_params(
    axis='both',
    which='both',
    bottom=False,
    top=False,
    left=False,
    right=False,
    labelbottom=False,
    labeltop=False,
    labelleft=False,
    labelright=False
)

# Mass threshold line
ax_a.axhline(MASS_THRESHOLD, color='#d62728', linestyle='--', linewidth=2.5)
ax_a.text(0.02, 0.95, '(a)', transform=ax_a.transAxes, fontsize=14, 
          fontweight='bold', va='top', ha='left')

# --- (b) Left panel (mass distribution KDE) ---
ax_b = fig.add_subplot(gs[1, 0])
y_log = np.log10(y[y > 0])

if len(y_log) > 2:
    try:
        kde_y = gaussian_kde(y_log)
        y_grid = np.linspace(np.log10(Y_MIN), np.log10(Y_MAX), 100)
        density = kde_y(y_grid)
        
        # Bootstrap confidence interval
        n_bootstrap = 100
        n_samples = len(y_log)
        densities_bootstrap = []
        
        for _ in range(n_bootstrap):
            idx = np.random.choice(n_samples, n_samples, replace=True)
            sample = y_log[idx]
            try:
                kde_sample = gaussian_kde(sample)
                density_sample = kde_sample(y_grid)
                densities_bootstrap.append(density_sample)
            except:
                pass
        
        densities_bootstrap = np.array(densities_bootstrap)
        lower_bound = np.percentile(densities_bootstrap, 16, axis=0)
        upper_bound = np.percentile(densities_bootstrap, 84, axis=0)
        density_std = np.std(densities_bootstrap, axis=0)
        
        ax_b.plot(density * 100, 10 ** y_grid, color='#1f77b4', linewidth=2, label='KDE')
        ax_b.fill_betweenx(10 ** y_grid, lower_bound * 100, upper_bound * 100,
                          color='#1f77b4', alpha=0.3, label='1 sigma uncertainty')
        
        step = 10
        ax_b.errorbar(density[::step] * 100, 10 ** y_grid[::step],
                     xerr=density_std[::step] * 100,
                     fmt='none', ecolor='#1f77b4', capsize=3, 
                     elinewidth=1, alpha=0.7, label='+/- 1 sigma')
        
        ax_b.set_xlim(0, np.max(upper_bound) * 150)
        
    except Exception as e:
        print(f"KDE calculation warning: {e}")
        try:
            kde_y = gaussian_kde(y_log)
            y_grid = np.linspace(np.log10(Y_MIN), np.log10(Y_MAX), 100)
            density = kde_y(y_grid)
            ax_b.plot(density * 100, 10 ** y_grid, color='#1f77b4', linewidth=2)
            ax_b.fill_betweenx(10 ** y_grid, 0, density * 100, color='#1f77b4', alpha=0.15)
            ax_b.set_xlim(0, np.max(density) * 150)
        except:
            pass

ax_b.set_ylim(Y_MIN, Y_MAX)
ax_b.set_yscale('log')
ax_b.set_xlabel('occurrence rate', fontsize=12)
ax_b.tick_params(axis='y', which='both', left=True, labelleft=True)

ax_b.yaxis.set_ticks([5, 10, 25, 50, 100])
ax_b.yaxis.set_major_formatter(plt.FuncFormatter(format_func))

def format_x_axis_b(value, tick_number):
    if value == 0 or abs(value) < 0.01:
        return ''
    return f'{value:.1f}'

ax_b.xaxis.set_major_formatter(FuncFormatter(format_x_axis_b))
ax_b.legend(frameon=False, fontsize=9, loc='upper right')
ax_b.text(0.02, 0.95, '(b)', transform=ax_b.transAxes, fontsize=14, 
          fontweight='bold', va='top', ha='left')

# --- (d) Bottom panel (low mass occurrence rate) ---
ax_d = fig.add_subplot(gs[2, 1])
ax_d.errorbar(bin_centers, counts_d, yerr=np.sqrt(counts_d), fmt='s-', color='#d62728',
              ecolor='#d62728', capsize=3, markersize=4, label=r'$5 < m < 30 M_J$')
ax_d.set_xscale('log')
ax_d.set_xlim(X_MIN, X_MAX)
ax_d.set_xlabel(r'Semi-major axis $a$ [au]', fontsize=14)
ax_d.set_ylabel('occurrence rate')
ax_d.legend(frameon=False, fontsize=10, loc='lower center')
ax_d.text(0.02, 0.95, '(d)', transform=ax_d.transAxes, fontsize=14, 
          fontweight='bold', va='top', ha='left')

def format_x_axis_d(value, tick_number):
    if value >= 10:
        return ''
    if value.is_integer() and value > 0:
        return f'{int(value)}'
    return ''

ax_d.xaxis.set_major_formatter(FuncFormatter(format_x_axis_d))

def format_y_axis_d(value, tick_number):
    if value > 10:
        return ''
    if value.is_integer():
        return f'{int(value)}'
    return ''

ax_d.yaxis.set_major_formatter(FuncFormatter(format_y_axis_d))

for ax in [ax_a, ax_c, ax_d]:
    ax.xaxis.set_major_formatter(plt.ScalarFormatter())

# ========== Save ==========
plt.tight_layout()
plt.savefig('mass_semimajor.pdf', dpi=300, facecolor='white')
print("\nSaved: mass_semimajor.pdf")

print("\n" + "="*70)
print("Done!")
print("="*70)