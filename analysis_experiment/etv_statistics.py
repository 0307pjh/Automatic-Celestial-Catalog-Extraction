#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETV Candidate Statistics
------------------------
Reproduces Figure 5 of the paper: distribution statistics of ETV candidates
extracted from the literature.

Panel (a): distribution of ETV_candidate_type for records with a valid type
           label (excluding the mixed class companion_and_orbital_decay).
Panel (b): distribution of ETV_candidate_status for records with a non-empty
           status label.
Panel (c): number of observable ETV targets across four seasons under Lenghu
           site conditions (altitude > 30 deg, V-band magnitude 10-17), based
           on the final filtered and coordinate-deduplicated sample of 345
           ETV candidates.

Filtering / deduplication logic (consistent with etv_observable_targets.py):
- ETV_candidate_type == UNCERTAIN
- Exclude STRONG / CONFIRMED / REJECTED
- Coordinate deduplication with 0.001 deg tolerance
- Deduplicate by simbad_name
- Altitude > 30 deg and 10 <= V <= 17

Input:
    etv.csv    (the released ETV measurement catalog)

Outputs:
    Figures/etv_statistics_panel.pdf
    Figures/etv_statistics_panel.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.units as u
import warnings
warnings.filterwarnings('ignore')

# ========== Configuration ==========
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 22,
    'axes.labelsize': 28,
    'xtick.labelsize': 22,
    'ytick.labelsize': 22,
    'legend.fontsize': 20,
    'axes.titlesize': 26,
    'axes.linewidth': 1.5,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})


def calculate_altitude(ra_deg, dec_deg, longitude_deg, latitude_deg, time_utc):
    """Calculate the target altitude angle."""
    try:
        location = EarthLocation(lon=longitude_deg * u.deg, lat=latitude_deg * u.deg, height=4200 * u.m)
        coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
        altaz = coord.transform_to(AltAz(location=location, obstime=Time(time_utc)))
        return altaz.alt.deg
    except Exception:
        return np.nan


def deduplicate_by_coordinates(df, coord_tolerance=0.001):
    """Coordinate-based deduplication (consistent with etv_observable_targets.py)."""
    if df.empty:
        return df

    df['simbad_RA_d'] = pd.to_numeric(df['simbad_RA_d'], errors='coerce')
    df['simbad_DEC_d'] = pd.to_numeric(df['simbad_DEC_d'], errors='coerce')

    df_valid = df.dropna(subset=['simbad_RA_d', 'simbad_DEC_d']).copy()

    if len(df_valid) == 0:
        return df_valid

    df_valid['RA_rounded'] = np.round(df_valid['simbad_RA_d'] / coord_tolerance) * coord_tolerance
    df_valid['DEC_rounded'] = np.round(df_valid['simbad_DEC_d'] / coord_tolerance) * coord_tolerance

    df_dedup = df_valid.drop_duplicates(
        subset=['RA_rounded', 'DEC_rounded'],
        keep='first'
    )

    df_dedup = df_dedup.drop(columns=['RA_rounded', 'DEC_rounded'])

    return df_dedup


# ========== Read data ==========
print("=" * 70)
print("ETV Candidate Statistics")
print("=" * 70)

df = pd.read_csv('etv.csv', encoding='utf-8-sig', low_memory=False)
print(f"Total records: {len(df):,}")

# ========== 1. ETV_candidate_type distribution ==========
print("\n[ETV_candidate_type distribution]")
if 'ETV_candidate_type' in df.columns:
    df_type = df[df['ETV_candidate_type'] != 'companion_and_orbital_decay']
    type_counts = df_type['ETV_candidate_type'].value_counts()
    # Percentage denominator: sum of displayed valid type counts (excluding empty)
    type_denom = int(type_counts.sum())
    n_missing_type = len(df_type) - type_denom
    print(f"  Denominator (valid types): {type_denom:,} "
          f"(missing/other: {n_missing_type:,})")
    for typ, count in type_counts.items():
        print(f"  {typ}: {count} ({count / type_denom * 100:.1f}%)")
else:
    print("  Column 'ETV_candidate_type' not found")

# ========== 2. ETV_candidate_status distribution ==========
print("\n[ETV_candidate_status distribution]")
if 'ETV_candidate_status' in df.columns:
    status_counts = df['ETV_candidate_status'].value_counts()
    status_denom = int(status_counts.sum())
    n_missing = len(df) - status_denom
    print(f"  Denominator (non-empty status): {status_denom:,} (missing: {n_missing:,})")
    for status, count in status_counts.items():
        print(f"  {status}: {count} ({count / status_denom * 100:.1f}%)")
else:
    print("  Column 'ETV_candidate_status' not found")

# ========== 3. Basic filtering ==========
print("\n[Basic filtering]")
df_filtered = df.copy()

if 'ETV_candidate_type' in df.columns:
    before = len(df_filtered)
    df_filtered = df_filtered[df_filtered['ETV_candidate_type'].str.upper() == 'UNCERTAIN']
    print(f"  ETV_candidate_type = 'uncertain': {before} -> {len(df_filtered)}")

if 'ETV_candidate_status' in df.columns:
    before = len(df_filtered)
    exclude_status = ['STRONG', 'CONFIRMED', 'REJECTED']
    df_filtered = df_filtered[~df_filtered['ETV_candidate_status'].str.upper().isin(exclude_status)]
    print(f"  Excluding 'strong', 'confirmed', 'rejected': {before} -> {len(df_filtered)}")

print(f"\n  Candidates after filtering: {len(df_filtered)}")

# ========== 4. Coordinate conversion and deduplication ==========
df_filtered['simbad_RA_d'] = pd.to_numeric(df_filtered['simbad_RA_d'], errors='coerce')
df_filtered['simbad_DEC_d'] = pd.to_numeric(df_filtered['simbad_DEC_d'], errors='coerce')
df_filtered['simbad_V_mag'] = pd.to_numeric(df_filtered['simbad_V_mag'], errors='coerce')

# 4.1 Coordinate tolerance deduplication
df_dedup = deduplicate_by_coordinates(df_filtered, coord_tolerance=0.001)
after_coord = len(df_dedup)

# 4.2 Deduplicate by simbad_name
df_dedup = df_dedup.sort_values(
    by=['simbad_name', 'simbad_RA_d', 'simbad_V_mag'],
    ascending=[True, False, False],
    na_position='last'
)
df_dedup = df_dedup.drop_duplicates(subset=['simbad_name'], keep='first')

print(f"\n  After coordinate dedup (0.001 deg): {after_coord}")
print(f"  Unique targets after name dedup: {len(df_dedup)}")

# ========== 5. Seasonal observability ==========
print("\n[Seasonal observability]")

OBS_LONGITUDE = 93.90
OBS_LATITUDE = 38.60

seasons = {
    'spring': {'time': '2026-03-20 14:00:00', 'name': 'Spring'},
    'summer': {'time': '2026-06-21 14:00:00', 'name': 'Summer'},
    'autumn': {'time': '2026-09-23 14:00:00', 'name': 'Autumn'},
    'winter': {'time': '2026-12-21 14:00:00', 'name': 'Winter'}
}

MIN_ALTITUDE = 30
MIN_VMAG = 10
MAX_VMAG = 17

season_counts = {}

for season_key, season_info in seasons.items():
    alt_list = []
    for idx, row in df_dedup.iterrows():
        ra = row['simbad_RA_d']
        dec = row['simbad_DEC_d']
        if pd.notna(ra) and pd.notna(dec):
            alt = calculate_altitude(ra, dec, OBS_LONGITUDE, OBS_LATITUDE, season_info['time'])
            alt_list.append(alt)
        else:
            alt_list.append(np.nan)

    df_dedup[f'altitude_{season_key}'] = alt_list

    mask = (
        df_dedup[f'altitude_{season_key}'] > MIN_ALTITUDE) & \
        df_dedup['simbad_V_mag'].notna() & \
        (df_dedup['simbad_V_mag'] >= MIN_VMAG) & \
        (df_dedup['simbad_V_mag'] <= MAX_VMAG)

    count = int(mask.sum())
    season_counts[season_key] = count
    print(f"  {season_info['name']}: {count} targets")

# ========== 6. Plotting ==========
print("\n" + "=" * 70)
print("Generating ETV statistics figure...")
print("=" * 70)

fig, axes = plt.subplots(1, 3, figsize=(28, 10))

# ---- Light color palette ----
COLOR_TYPE = ['#a6c8e8', '#a8d5a2', '#f7c97e', '#f0a0a0', '#c9b0d9']
COLOR_STATUS = ['#e8a0a0', '#f7c97e', '#e8d88a', '#a8c8e8', '#c9b0d9']
COLOR_SEASON = ['#a8d5a2', '#f0a0a0', '#f7c97e', '#a8c8e8']

# ---- Panel (a) ETV_candidate_type distribution ----
ax1 = axes[0]
if 'ETV_candidate_type' in df.columns:
    df_type = df[df['ETV_candidate_type'] != 'companion_and_orbital_decay']
    type_counts = df_type['ETV_candidate_type'].value_counts()
    colors_type = COLOR_TYPE[:len(type_counts)]
    bars1 = ax1.bar(type_counts.index, type_counts.values, color=colors_type,
                    edgecolor='black', linewidth=1.2)
    ax1.set_xlabel('Candidate Type', fontsize=28, labelpad=20)
    ax1.set_ylabel('Count', fontsize=28, labelpad=15)
    ax1.set_title('(a) ETV Candidate Type Distribution', fontsize=26, pad=20)
    ax1.tick_params(axis='x', rotation=0, labelsize=24)
    ax1.tick_params(axis='y', labelsize=24)
    ax1.grid(alpha=0.3, linestyle='--', axis='y')
    if len(type_counts) > 0:
        max_a = max(type_counts.values)
        ylim_a = max_a * 1.18
        ax1.set_ylim(0, ylim_a)
        type_denom = int(type_counts.sum())
        for bar, count in zip(bars1, type_counts.values):
            pct = count / type_denom * 100 if type_denom > 0 else 0
            label = f"{count}\n({pct:.1f}%)"
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ylim_a * 0.02,
                     label, ha='center', va='bottom', fontsize=16, fontweight='bold')

# ---- Panel (b) ETV_candidate_status distribution ----
ax2 = axes[1]
if 'ETV_candidate_status' in df.columns:
    status_counts = df['ETV_candidate_status'].value_counts()
    colors_status = COLOR_STATUS[:len(status_counts)]
    bars2 = ax2.bar(status_counts.index, status_counts.values, color=colors_status,
                    edgecolor='black', linewidth=1.2)
    ax2.set_xlabel('Candidate Status', fontsize=28, labelpad=20)
    ax2.set_ylabel('Count', fontsize=28, labelpad=15)
    ax2.set_title('(b) ETV Candidate Status Distribution', fontsize=26, pad=20)
    ax2.tick_params(axis='x', rotation=0, labelsize=24)
    ax2.tick_params(axis='y', labelsize=24)
    ax2.grid(alpha=0.3, linestyle='--', axis='y')
    ylim_b = 2000
    ax2.set_ylim(0, ylim_b)
    status_denom = int(status_counts.sum())
    for bar, count in zip(bars2, status_counts.values):
        pct = count / status_denom * 100 if status_denom > 0 else 0
        label = f"{count}\n({pct:.1f}%)"
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ylim_b * 0.02,
                 label, ha='center', va='bottom', fontsize=16, fontweight='bold')

# ---- Panel (c) Seasonal observability ----
ax3 = axes[2]
season_labels = ['Spring', 'Summer', 'Autumn', 'Winter']
season_values = [season_counts['spring'], season_counts['summer'],
                 season_counts['autumn'], season_counts['winter']]
bars3 = ax3.bar(season_labels, season_values, color=COLOR_SEASON, edgecolor='black', linewidth=1.2)
ax3.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
ax3.set_xlabel('Season', fontsize=28, labelpad=20)
ax3.set_ylabel('Observable Targets', fontsize=28, labelpad=15)
ax3.set_title('(c) Observable ETV Targets per Season', fontsize=26, pad=20)
ax3.tick_params(axis='x', rotation=0, labelsize=24)
ax3.tick_params(axis='y', labelsize=24)
ax3.grid(alpha=0.3, linestyle='--', axis='y')
ylim_c = 150
ax3.set_ylim(0, ylim_c)
for bar, v in zip(bars3, season_values):
    ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ylim_c * 0.02,
             str(v), ha='center', va='bottom', fontsize=18, fontweight='bold')

# ---- Align all x-axis labels ----
fig.align_xlabels()

plt.subplots_adjust(wspace=0.35)
plt.tight_layout()
plt.savefig('Figures/etv_statistics_panel.pdf', dpi=300, facecolor='white', bbox_inches='tight')
print("Saved: Figures/etv_statistics_panel.pdf")
plt.savefig('Figures/etv_statistics_panel.png', dpi=300, facecolor='white', bbox_inches='tight')
print("Saved: Figures/etv_statistics_panel.png")
