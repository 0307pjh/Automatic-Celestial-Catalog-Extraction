#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aitoff All-Sky Map of ETV Candidates
-------------------------------------
Reproduces Figure 6 of the paper: the sky distribution of ETV follow-up
observable targets across the four seasons, evaluated from the Lenghu site
(altitude > 30 deg, V-band magnitude 10-17).

For visual clarity, up to 10 spatially well-separated representative targets
(minimum angular separation 15 deg) are labeled per season, and the total
number of unique observable targets is shown in the title.

Inputs (produced by etv_observable_targets.py):
    etv_experiments/observable_targets_spring.csv
    etv_experiments/observable_targets_summer.csv
    etv_experiments/observable_targets_autumn.csv
    etv_experiments/observable_targets_winter.csv

Outputs:
    Figures/aitoff_manuscript.pdf
    Figures/aitoff_manuscript.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from astropy import units as u
from astropy.coordinates import SkyCoord
import random
random.seed(42)

# ========== Season colors (consistent with the paper figure) ==========
SEASON_COLORS = {
    'Spring': '#73d216',    # green
    'Summer': '#e06666',    # pink
    'Autumn': '#f57900',    # orange
    'Winter': '#2962ff'     # blue
}

SEASON_MARKERS = {
    'Spring': 'o',
    'Summer': 'o',
    'Autumn': 'o',
    'Winter': 'o'
}

# ========== Compact configuration ==========
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'font.size': 12,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
    'axes.linewidth': 1.2,
    'xtick.major.width': 1.2,
    'ytick.major.width': 1.2,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
})


def read_season_data(season_files):
    """Read the four seasonal target files."""
    season_names = {'spring': 'Spring', 'summer': 'Summer', 'autumn': 'Autumn', 'winter': 'Winter'}

    all_data = []
    for season_key, file_path in season_files.items():
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            df['season'] = season_names[season_key]
            df['color'] = SEASON_COLORS[season_names[season_key]]
            df['marker'] = SEASON_MARKERS[season_names[season_key]]
            all_data.append(df)
            print(f"  {season_names[season_key]}: {len(df)} targets")
        except FileNotFoundError:
            print(f"  Warning: file not found: {file_path}")

    if not all_data:
        return None
    return pd.concat(all_data, ignore_index=True)


def dedup_by_coord_tolerance(df, tol=0.001):
    """
    Deduplicate by coordinate tolerance (consistent with
    deduplicate_by_coordinates in etv_observable_targets.py).
    """
    if df.empty:
        return df

    df = df.copy()
    df['simbad_RA_d'] = pd.to_numeric(df['simbad_RA_d'], errors='coerce')
    df['simbad_DEC_d'] = pd.to_numeric(df['simbad_DEC_d'], errors='coerce')
    df = df.dropna(subset=['simbad_RA_d', 'simbad_DEC_d'])

    if len(df) == 0:
        return df

    df['RA_rounded'] = np.round(df['simbad_RA_d'] / tol) * tol
    df['DEC_rounded'] = np.round(df['simbad_DEC_d'] / tol) * tol
    df = df.drop_duplicates(subset=['RA_rounded', 'DEC_rounded'], keep='first')
    df = df.drop(columns=['RA_rounded', 'DEC_rounded'])

    return df


def angular_distance(ra1, dec1, ra2, dec2):
    """Angular separation in degrees."""
    ra1_rad = np.radians(ra1)
    dec1_rad = np.radians(dec1)
    ra2_rad = np.radians(ra2)
    dec2_rad = np.radians(dec2)

    d_ra = ra2_rad - ra1_rad
    d_dec = dec2_rad - dec1_rad

    a = np.sin(d_dec/2)**2 + np.cos(dec1_rad) * np.cos(dec2_rad) * np.sin(d_ra/2)**2
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    return np.degrees(c)


def select_dispersed_targets(df, labels_per_season=10, min_separation_deg=15):
    """Select spatially dispersed representative targets."""
    seasons = ['Spring', 'Summer', 'Autumn', 'Winter']
    selected_dfs = []
    used_targets = set()
    selected_coords = []

    for season in seasons:
        season_df = df[df['season'] == season]
        if len(season_df) == 0:
            continue

        if 'simbad_V_mag' in season_df.columns:
            season_df = season_df.sort_values('simbad_V_mag')
        else:
            season_df = season_df.sample(frac=1)

        selected = []

        for idx, row in season_df.iterrows():
            target_key = row.get('simbad_name', '')
            if not target_key:
                target_key = f"{row['simbad_RA_d']:.4f}_{row['simbad_DEC_d']:.4f}"

            if target_key in used_targets:
                continue

            ra_new = row['simbad_RA_d']
            dec_new = row['simbad_DEC_d']

            is_too_close = False
            for ra_sel, dec_sel in selected_coords:
                sep_deg = angular_distance(ra_new, dec_new, ra_sel, dec_sel)
                if sep_deg < min_separation_deg:
                    is_too_close = True
                    break

            if not is_too_close and len(selected) < labels_per_season:
                selected.append(row)
                used_targets.add(target_key)
                selected_coords.append((ra_new, dec_new))

        if selected:
            df_selected = pd.DataFrame(selected)
            df_selected['season'] = season
            selected_dfs.append(df_selected)
            print(f"  -> {season}: selected {len(df_selected)} targets")
        else:
            print(f"  -> {season}: 0 targets selected")

    if selected_dfs:
        return pd.concat(selected_dfs, ignore_index=True)
    return pd.DataFrame()


def plot_aitoff_apj(df, output_file="Figures/aitoff_manuscript.pdf",
                    labels_per_season=10, min_separation_deg=15,
                    n_unique=None):
    """Compact Aitoff all-sky map (paper color scheme)."""
    print("\n" + "=" * 70)
    print("Generating Aitoff all-sky map")
    print(f"   Top {labels_per_season} per season | Min sep: {min_separation_deg} deg")
    print("=" * 70)

    df_plot = select_dispersed_targets(df, labels_per_season, min_separation_deg)

    if len(df_plot) == 0:
        print("No targets selected!")
        return None

    print(f"\n  -> Representative targets: {len(df_plot)}")
    for season in ['Spring', 'Summer', 'Autumn', 'Winter']:
        count = len(df_plot[df_plot['season'] == season])
        print(f"     {season}: {count} targets")
    print("=" * 70)

    # ---- Create the figure ----
    fig = plt.figure(figsize=(12, 7))
    ax = fig.add_subplot(111, projection='aitoff')

    colors = SEASON_COLORS
    markers = SEASON_MARKERS
    seasons = ['Spring', 'Summer', 'Autumn', 'Winter']

    # 1. Scatter plot
    for season in seasons:
        season_df = df_plot[df_plot['season'] == season]
        if len(season_df) == 0:
            continue

        ra_plot = season_df['simbad_RA_d'].copy()
        ra_plot[ra_plot > 180] = ra_plot[ra_plot > 180] - 360
        ra_rad = np.radians(ra_plot)
        dec_rad = np.radians(season_df['simbad_DEC_d'])

        ax.scatter(ra_rad, dec_rad,
                   c=colors[season], marker=markers[season],
                   s=80, alpha=0.8, edgecolors='black', linewidths=0.6,
                   label=f"{season} (N={len(season_df)})", zorder=5)

    # 2. Add labels (below the target near the equator, above otherwise)
    DEC_THRESHOLD = 25.0   # |dec| < 25 deg is treated as near-equator

    for idx, row in df_plot.iterrows():
        ra_label = row['simbad_RA_d']
        if ra_label > 180:
            ra_label = ra_label - 360

        dec_val = row['simbad_DEC_d']

        name = row.get('simbad_name', '')
        if name:
            name = name.replace('NAME ', '').replace('2MASS ', '').replace('WISE ', '').replace('HD ', '')

        offset_ra = np.radians(ra_label) + random.uniform(-0.015, 0.015)

        # Near the equator -> label below; otherwise -> label above
        if abs(dec_val) < DEC_THRESHOLD:
            offset_dec = np.radians(dec_val) - random.uniform(0.06, 0.12)
            va = 'top'
        else:
            offset_dec = np.radians(dec_val) + random.uniform(0.06, 0.12)
            va = 'bottom'

        mag = row.get('simbad_V_mag', '')
        if pd.notna(mag):
            label_text = f"{name[:12]} ({mag:.1f})"
        else:
            label_text = f"{name[:12]}"

        season_color = colors.get(row['season'], 'black')

        ax.text(offset_ra, offset_dec,
                label_text, fontsize=8, ha='center', va=va,
                color=season_color, alpha=0.85, zorder=10, weight='bold')

    # 3. Axis
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)

    ra_ticks = np.radians([-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150])
    ra_labels = ['14h', '16h', '18h', '20h', '22h', '0h', '2h', '4h', '6h', '8h', '10h']
    ax.set_xticks(ra_ticks)
    ax.set_xticklabels(ra_labels, fontsize=11)
    ax.set_xlabel('Right Ascension', fontsize=13)

    dec_ticks = np.radians([-60, -30, 0, 30, 60])
    dec_labels = ['-60 deg', '-30 deg', '0 deg', '+30 deg', '+60 deg']
    ax.set_yticks(dec_ticks)
    ax.set_yticklabels(dec_labels, fontsize=11)
    ax.set_ylabel('Declination', fontsize=13)

    # 4. Galactic equator
    glon = np.linspace(0, 360, 300)
    glat = np.zeros(300)
    coords_gal = SkyCoord(l=glon*u.deg, b=glat*u.deg, frame='galactic')
    coords_icrs = coords_gal.transform_to('icrs')
    ra_gal = coords_icrs.ra.deg
    dec_gal = coords_icrs.dec.deg
    ra_gal[ra_gal > 180] = ra_gal[ra_gal > 180] - 360
    ax.plot(np.radians(ra_gal), np.radians(dec_gal),
            color='gray', linestyle='--', linewidth=1.2, alpha=0.6, zorder=2,
            label='Galactic Equator')

    # 5. Galactic center
    gc_coord = SkyCoord(l=0*u.deg, b=0*u.deg, frame='galactic')
    gc_icrs = gc_coord.transform_to('icrs')
    gc_ra = gc_icrs.ra.deg
    gc_dec = gc_icrs.dec.deg
    if gc_ra > 180:
        gc_ra = gc_ra - 360

    ax.scatter(np.radians(gc_ra), np.radians(gc_dec),
               color='gold', marker='*', s=150, edgecolors='black', linewidth=0.8,
               label='Galactic Center', zorder=20)

    # 6. Legend
    legend = ax.legend(loc='upper right', fontsize=10, framealpha=0.9,
                       edgecolor='black', facecolor='white', fancybox=False)
    legend.get_frame().set_linewidth(1.0)

    # 7. Title: total unique targets + number of representative targets shown
    if n_unique is not None:
        title = (
            f"Four-Season Observable Targets (Alt > 30 deg, V = 10-17)\n"
            f"{n_unique} unique targets; {len(df_plot)} representative targets shown"
        )
    else:
        title = (
            f"Four-Season Observable Targets (Alt > 30 deg, V = 10-17)\n"
            f"{len(df_plot)} representative targets shown"
        )
    ax.set_title(title, fontsize=13, pad=15)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved: {output_file}")
    png_file = output_file.replace('.pdf', '.png')
    plt.savefig(png_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved: {png_file}")
    plt.close()
    return fig


def print_statistics(df):
    """
    Statistics of the four seasons: record counts, exact-coordinate
    deduplication count, and 0.001-deg tolerance deduplication count.
    The 0.001-deg tolerance result is consistent with the 129 targets
    from etv_observable_targets.py.
    """
    print("\n" + "=" * 60)
    print("Season Statistics")
    print("=" * 60)

    season_counts = df['season'].value_counts()
    for season in ['Spring', 'Summer', 'Autumn', 'Winter']:
        print(f"  {season:<8}: {season_counts.get(season, 0):>3} targets")

    unique_exact = df.drop_duplicates(subset=['simbad_RA_d', 'simbad_DEC_d'])
    unique_tol = dedup_by_coord_tolerance(df, tol=0.001)

    print(f"\n  Total season-target records : {len(df)}")
    print(f"  Unique (exact RA/DEC)       : {len(unique_exact)}")
    print(f"  Unique (0.001 deg tolerance): {len(unique_tol)}   <- consistent with etv_observable_targets.py")

    return len(unique_tol)


if __name__ == "__main__":
    season_files = {
        'spring': 'etv_experiments/observable_targets_spring.csv',
        'summer': 'etv_experiments/observable_targets_summer.csv',
        'autumn': 'etv_experiments/observable_targets_autumn.csv',
        'winter': 'etv_experiments/observable_targets_winter.csv'
    }

    print("Reading data...")
    df = read_season_data(season_files)

    if df is None or len(df) == 0:
        print("No data found.")
        exit()

    # Statistics first: get the unique target count consistent with the filter script
    n_unique = print_statistics(df)

    # Then plot, showing both the total unique count and the representative count
    plot_aitoff_apj(
        df,
        "Figures/aitoff_manuscript.pdf",
        labels_per_season=10,
        min_separation_deg=15,
        n_unique=n_unique
    )
