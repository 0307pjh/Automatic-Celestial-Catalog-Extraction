#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brown dwarf temperature-age evolution and temperature-mass isochrones
APJ submission format - no binary markers
Corresponds to Figure 4 of the paper
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings('ignore')

# ========== Global plot configuration (APJ style) ==========
plt.rcParams.update({
    'font.size': 8.5,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'Palatino'],
    'axes.labelsize': 9.0,
    'xtick.labelsize': 7.0,
    'ytick.labelsize': 7.0,
    'legend.fontsize': 6.8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
})

# ========== 1. Read and clean data ==========
print("="*70)
print("Data loading and cleaning")
print("="*70)

df = pd.read_csv('brown_dwarf.csv', low_memory=False)
print(f"Original rows: {len(df):,}")

# Value extraction function
def extract_mid_value(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    if re.match(r'^[\d.]+$', val_str):
        try:
            return float(val_str)
        except:
            return np.nan
    match = re.match(r'^[~∼<>≤≥≲≳]\s*([\d.]+)$', val_str)
    if match:
        try:
            return float(match.group(1))
        except:
            return np.nan
    if '–' in val_str or '-' in val_str:
        numbers = re.findall(r'[\d.]+', val_str)
        if len(numbers) >= 2:
            try:
                low = float(numbers[0])
                high = float(numbers[-1])
                return (low + high) / 2.0
            except:
                pass
    if '...' in val_str:
        numbers = re.findall(r'[\d.]+', val_str)
        if len(numbers) >= 2:
            try:
                low = float(numbers[0])
                high = float(numbers[-1])
                return (low + high) / 2.0
            except:
                pass
    return np.nan

# Extract key columns
print("\nExtracting mid values...")
for col in ['Mass_MJ', 'EffectiveTemperature_K', 'Age_Gyr']:
    df[f'{col}_mid'] = df[col].apply(extract_mid_value)
    valid = df[f'{col}_mid'].notna().sum()
    print(f"  {col}: {valid:,} valid ({valid/len(df)*100:.1f}%)")

# Unit conversion: 10^3 K -> K
df['EffectiveTemperature_K_mid'] = df.apply(
    lambda row: row['EffectiveTemperature_K_mid'] * 1000 
    if row.get('EffectiveTemperature_K_unit') == '10^3 K' 
    and pd.notna(row['EffectiveTemperature_K_mid'])
    else row['EffectiveTemperature_K_mid'], axis=1
)

# Unit conversion: Myr -> Gyr
df['Age_Gyr_mid'] = df.apply(
    lambda row: row['Age_Gyr_mid'] / 1000 
    if row.get('Age_Gyr_unit') in ['Myr', 'My', '10^6 yrs'] 
    and pd.notna(row['Age_Gyr_mid'])
    else row['Age_Gyr_mid'], axis=1
)

# ========== 2. Data cleaning ==========
print("\n" + "="*70)
print("Data cleaning")
print("="*70)

# Keep only brown dwarfs
df_bd = df[df['IsBrownDwarf'] == 1.0].copy()
print(f"Brown dwarfs: {len(df_bd):,} rows ({len(df_bd)/len(df)*100:.1f}%)")

# Drop rows with missing key columns
df_clean = df_bd.dropna(subset=['Mass_MJ_mid', 'EffectiveTemperature_K_mid', 'Age_Gyr_mid'])
print(f"After dropping nulls: {len(df_clean):,} rows")

# Remove physically unreasonable values
before = len(df_clean)
df_clean = df_clean[
    (df_clean['EffectiveTemperature_K_mid'] > 200) &
    (df_clean['EffectiveTemperature_K_mid'] < 3500) &
    (df_clean['Mass_MJ_mid'] > 0) &
    (df_clean['Mass_MJ_mid'] < 100) &
    (df_clean['Age_Gyr_mid'] > 0.001) &
    (df_clean['Age_Gyr_mid'] < 15)
]
print(f"After removing outliers: {len(df_clean):,} rows (removed {before - len(df_clean)})")

# ========== 3. Detailed statistics ==========
print("\n" + "="*70)
print("Detailed statistics")
print("="*70)

print("\n[Effective Temperature]")
print(f"  Count: {len(df_clean):,}")
print(f"  Min: {df_clean['EffectiveTemperature_K_mid'].min():.0f} K")
print(f"  Max: {df_clean['EffectiveTemperature_K_mid'].max():.0f} K")
print(f"  Mean: {df_clean['EffectiveTemperature_K_mid'].mean():.0f} K")
print(f"  Median: {df_clean['EffectiveTemperature_K_mid'].median():.0f} K")
print(f"  Std: {df_clean['EffectiveTemperature_K_mid'].std():.0f} K")
print(f"  IQR: {df_clean['EffectiveTemperature_K_mid'].quantile(0.75) - df_clean['EffectiveTemperature_K_mid'].quantile(0.25):.0f} K")

print("\n[Mass]")
print(f"  Count: {len(df_clean):,}")
print(f"  Min: {df_clean['Mass_MJ_mid'].min():.2f} M_J")
print(f"  Max: {df_clean['Mass_MJ_mid'].max():.2f} M_J")
print(f"  Mean: {df_clean['Mass_MJ_mid'].mean():.2f} M_J")
print(f"  Median: {df_clean['Mass_MJ_mid'].median():.2f} M_J")
print(f"  Std: {df_clean['Mass_MJ_mid'].std():.2f} M_J")
print(f"  IQR: {df_clean['Mass_MJ_mid'].quantile(0.75) - df_clean['Mass_MJ_mid'].quantile(0.25):.2f} M_J")

print("\n[Age]")
print(f"  Count: {len(df_clean):,}")
print(f"  Min: {df_clean['Age_Gyr_mid'].min():.3f} Gyr")
print(f"  Max: {df_clean['Age_Gyr_mid'].max():.3f} Gyr")
print(f"  Mean: {df_clean['Age_Gyr_mid'].mean():.3f} Gyr")
print(f"  Median: {df_clean['Age_Gyr_mid'].median():.3f} Gyr")
print(f"  Std: {df_clean['Age_Gyr_mid'].std():.3f} Gyr")
print(f"  IQR: {df_clean['Age_Gyr_mid'].quantile(0.75) - df_clean['Age_Gyr_mid'].quantile(0.25):.3f} Gyr")

# ========== 4. Group statistics ==========
print("\n" + "="*70)
print("Group statistics")
print("="*70)

print("\n[Mass bins]")
mass_bins = [0, 10, 20, 40, 60, 100]
mass_labels = ['<10 M_J', '10-20 M_J', '20-40 M_J', '40-60 M_J', '>60 M_J']
df_clean['mass_bin'] = pd.cut(df_clean['Mass_MJ_mid'], bins=mass_bins, labels=mass_labels)

for lab in mass_labels:
    sub = df_clean[df_clean['mass_bin'] == lab]
    if len(sub) > 0:
        print(f"  {lab:12s}: {len(sub):4d} ({len(sub)/len(df_clean)*100:.1f}%)")
        print(f"              Temp: {sub['EffectiveTemperature_K_mid'].mean():.0f} +/- {sub['EffectiveTemperature_K_mid'].std():.0f} K")
        print(f"              Age: {sub['Age_Gyr_mid'].mean():.3f} +/- {sub['Age_Gyr_mid'].std():.3f} Gyr")

print("\n[Age bins]")
age_bins = [0, 0.5, 1, 3, 5, 10, 20]
age_labels = ['<0.5 Gyr', '0.5-1 Gyr', '1-3 Gyr', '3-5 Gyr', '5-10 Gyr', '>10 Gyr']
df_clean['age_bin'] = pd.cut(df_clean['Age_Gyr_mid'], bins=age_bins, labels=age_labels)

for lab in age_labels:
    sub = df_clean[df_clean['age_bin'] == lab]
    if len(sub) > 0:
        print(f"  {lab:12s}: {len(sub):4d} ({len(sub)/len(df_clean)*100:.1f}%)")
        print(f"              Temp: {sub['EffectiveTemperature_K_mid'].mean():.0f} +/- {sub['EffectiveTemperature_K_mid'].std():.0f} K")
        print(f"              Mass: {sub['Mass_MJ_mid'].mean():.2f} +/- {sub['Mass_MJ_mid'].std():.2f} M_J")

# ========== 5. Create figure ==========
print("\n" + "="*70)
print("Generating figure")
print("="*70)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8))
plt.subplots_adjust(wspace=0.38, right=0.86)

# ================================================================
# Left: Temperature-age evolution (color-coded by mass)
# ================================================================
mass_colors = ['#99cced', '#73d216', '#f57900', '#e06666', '#674ea7']

for lab, color in zip(mass_labels, mass_colors):
    sub = df_clean[df_clean['mass_bin'] == lab]
    if len(sub) > 0:
        ax1.scatter(sub['Age_Gyr_mid'], sub['EffectiveTemperature_K_mid'],
                    color=color, s=20, alpha=0.7, label=lab)

# Theoretical cooling tracks
def cooling_track(age, mass):
    alpha, beta, t0 = 0.5, 0.3, 0.1
    T0 = 1500 * (mass / 30)**alpha
    return T0 * (age / t0)**(-beta)

age_range = np.logspace(-1, 1.5, 100)
mass_tracks = [10, 20, 40, 60]
track_colors = ['#222222', '#555555', '#888888', '#aaaaaa']
for idx, m in enumerate(mass_tracks):
    ax1.plot(age_range, cooling_track(age_range, m), '--',
             color=track_colors[idx], linewidth=1.2, alpha=0.6)

# Spectral boundaries
ax1.axhline(1300, color='gray', linestyle=':', alpha=0.7, linewidth=1.2)
ax1.text(age_range[-1]*0.75, 1330, 'T/L', fontsize=7, color='gray')
ax1.axhline(700, color='gray', linestyle=':', alpha=0.7, linewidth=1.2)
ax1.text(age_range[-1]*0.75, 720, 'Y/T', fontsize=7, color='gray')
ax1.axhspan(1250, 1350, alpha=0.08, color='gray')
ax1.axhspan(650, 750, alpha=0.08, color='gray')

ax1.set_xlabel('Age (Gyr)', fontsize=9.0)
ax1.set_ylabel('Effective Temperature (K)', fontsize=9.0)
ax1.set_title(f'(a) Temperature-Age Evolution (N={len(df_clean)})', fontsize=10)
ax1.set_xscale('log')
ax1.set_xlim(0.008, 15)
ax1.set_ylim(200, 3300)
ax1.invert_yaxis()
ax1.grid(alpha=0.25, linestyle='--', linewidth=0.5)

# ================================================================
# Right: Temperature-mass isochrones (color-coded by age)
# ================================================================
age_colors = ['#cc0000', '#f57900', '#d4b800', '#73d216', '#2962ff', '#311b92']

for lab, color in zip(age_labels, age_colors):
    sub = df_clean[df_clean['age_bin'] == lab]
    if len(sub) > 0:
        ax2.scatter(sub['Mass_MJ_mid'], sub['EffectiveTemperature_K_mid'],
                    color=color, s=20, alpha=0.7, label=lab)

# Theoretical isochrones
def isochrone(age, mass_range):
    beta, t0, alpha = 0.3, 0.1, 0.5
    T0 = 1500 / (age / t0)**beta
    return T0 * (mass_range / 30)**alpha

mass_range = np.linspace(0.5, 80, 100)
iso_ages = [0.1, 0.5, 1, 3, 5, 10]
for a, c in zip(iso_ages, age_colors[:6]):
    ax2.plot(mass_range, isochrone(a, mass_range), '--',
             color=c, linewidth=0.8, alpha=0.3)

# Spectral boundaries
ax2.axhline(1300, color='gray', linestyle=':', alpha=0.7, linewidth=1.2)
ax2.text(75, 1330, 'T/L', fontsize=7, color='gray')
ax2.axhline(700, color='gray', linestyle=':', alpha=0.7, linewidth=1.2)
ax2.text(75, 720, 'Y/T', fontsize=7, color='gray')
ax2.axhspan(1250, 1350, alpha=0.08, color='gray')
ax2.axhspan(650, 750, alpha=0.08, color='gray')

ax2.set_xlabel('Mass (M$_\mathrm{Jup}$)', fontsize=9.0)
ax2.set_ylabel('Effective Temperature (K)', fontsize=9.0)
ax2.set_title(f'(b) Temperature-Mass Isochrones (N={len(df_clean)})', fontsize=10)
ax2.set_xlim(0, 82)
ax2.set_ylim(200, 3300)
ax2.invert_yaxis()
ax2.grid(alpha=0.25, linestyle='--', linewidth=0.5)

# ================================================================
# Legends
# ================================================================
ax1.legend(loc='upper left', bbox_to_anchor=(1.01, 1.0), ncol=1,
           framealpha=0.9, edgecolor='black', fancybox=False, title='Mass')
ax2.legend(loc='upper left', bbox_to_anchor=(1.01, 1.0), ncol=1,
           framealpha=0.9, edgecolor='black', fancybox=False, title='Age')

# ================================================================
# Export (PDF only)
# ================================================================
plt.tight_layout()
plt.savefig('age_temp_cooling_evolution.pdf', dpi=300, facecolor='white')
print("Saved: age_temp_cooling_evolution.pdf")

# ================================================================
# Power-law cooling fit
# ================================================================
print("\n" + "="*70)
print("Empirical cooling relation fit (T = T0 x t^(-beta))")
print("="*70)

def power_law(age, T0, beta):
    return T0 * age**(-beta)

ages = df_clean['Age_Gyr_mid'].values
temps = df_clean['EffectiveTemperature_K_mid'].values
mask = (ages > 0.1) & (temps > 300) & (temps < 3000)
ages_fit, temps_fit = ages[mask], temps[mask]
print(f"Fit points: {len(ages_fit)} (age>0.1 Gyr, 300K<T<3000K)")

if len(ages_fit) > 10:
    popt, pcov = curve_fit(power_law, ages_fit, temps_fit, p0=[1000, 0.3])
    perr = np.sqrt(np.diag(pcov))
    print(f"\n  Fit result:")
    print(f"    T_eff = {popt[0]:.0f} x t^(-{popt[1]:.3f})")
    print(f"    T0 = {popt[0]:.0f} +/- {perr[0]:.0f} K")
    print(f"    beta = {popt[1]:.3f} +/- {perr[1]:.3f}")
    print(f"\n  Theoretical expectation: beta ~ 0.3")
    print(f"  Deviation: {abs(popt[1] - 0.3)/0.3*100:.1f}%")
    
    # Calculate R-squared
    pred = power_law(ages_fit, *popt)
    residuals = temps_fit - pred
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((temps_fit - np.mean(temps_fit))**2)
    r2 = 1 - (ss_res / ss_tot)
    print(f"  R^2 = {r2:.3f}")
else:
    print(f"  Insufficient data points ({len(ages_fit)} < 10)")

print("\n" + "="*70)
print("Done!")
