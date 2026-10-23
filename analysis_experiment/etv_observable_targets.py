#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETV Follow-up Observable Target Filtering
-----------------------------------------
Post-processing pipeline for the ETV application of the paper (Section 4.3):
filters the extracted ETV catalog, performs coordinate-based deduplication, and
evaluates seasonal observability from the Lenghu observing site.

Filtering criteria (consistent with the paper):
- ETV_candidate_type == uncertain
- Exclude ETV_candidate_status in {strong, confirmed, rejected}
- Coordinate deduplication with 0.001 deg tolerance (~3.6 arcsec)
- Deduplicate by simbad_name
- Target altitude > 30 deg (airmass ~ 2) and 10 <= V-band magnitude <= 17

Observing site: Lenghu (longitude = 93.90 deg E, latitude = 38.60 deg N,
site elevation ~ 4200 m). Visibility is evaluated at 14:00 UTC (~22:00
Beijing time) on four representative nights: 2026-03-20 (spring),
2026-06-21 (summer), 2026-09-23 (autumn), and 2026-12-21 (winter).

Input:
    etv.csv    (the released ETV measurement catalog)

Outputs (written to etv_experiments/):
    observable_targets_spring.csv / summer / autumn / winter
    etv_all_seasons_altitude.csv
    season_comparison_report.csv
    all_unique_observable_targets.csv
"""

import pandas as pd
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.units as u
from datetime import datetime

OUTPUT_DIR = 'etv_experiments/'


def calculate_altitude(ra_deg, dec_deg, longitude_deg, latitude_deg, time_utc):
    """Calculate the altitude and azimuth angles."""
    try:
        location = EarthLocation(lon=longitude_deg * u.deg, lat=latitude_deg * u.deg, height=4200 * u.m)
        coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
        altaz = coord.transform_to(AltAz(location=location, obstime=Time(time_utc)))
        return altaz.alt.deg, altaz.az.deg
    except Exception:
        return np.nan, np.nan


def deduplicate_by_coordinates(df, coord_tolerance=0.001):
    """
    Coordinate-based deduplication.

    Parameters:
    - df: input DataFrame
    - coord_tolerance: coordinate tolerance in degrees (default 0.001 deg ~ 3.6 arcsec)
    """
    if df.empty:
        return df

    # Ensure coordinate columns are numeric
    df['simbad_RA_d'] = pd.to_numeric(df['simbad_RA_d'], errors='coerce')
    df['simbad_DEC_d'] = pd.to_numeric(df['simbad_DEC_d'], errors='coerce')

    # Remove rows without coordinates
    df_valid = df.dropna(subset=['simbad_RA_d', 'simbad_DEC_d']).copy()

    if len(df_valid) == 0:
        return df_valid

    # Round coordinates to the tolerance level and deduplicate
    df_valid['RA_rounded'] = np.round(df_valid['simbad_RA_d'] / coord_tolerance) * coord_tolerance
    df_valid['DEC_rounded'] = np.round(df_valid['simbad_DEC_d'] / coord_tolerance) * coord_tolerance

    # Deduplicate by rounded coordinates, keep the first
    df_dedup = df_valid.drop_duplicates(
        subset=['RA_rounded', 'DEC_rounded'],
        keep='first'
    )

    # Drop helper columns
    df_dedup = df_dedup.drop(columns=['RA_rounded', 'DEC_rounded'])

    return df_dedup


def deduplicate_season_files(season_files, coord_tolerance=0.001):
    """Deduplicate each of the four seasonal files separately and save."""
    print("\n" + "-" * 70)
    print("Deduplicating the four seasonal files")
    print("-" * 70)

    season_names = {'spring': 'Spring', 'summer': 'Summer', 'autumn': 'Autumn', 'winter': 'Winter'}

    for season_key, file_path in season_files.items():
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            before = len(df)

            df_dedup = deduplicate_by_coordinates(df, coord_tolerance)
            after = len(df_dedup)

            # Save (overwrite the original file)
            df_dedup.to_csv(file_path, index=False, encoding='utf-8-sig')

            print(f"   {season_names[season_key]}: {before} -> {after} targets (removed {before - after})")

        except FileNotFoundError:
            print(f"   File not found: {file_path}")


def filter_observable_targets(input_file, output_file,
                              longitude_deg, latitude_deg, time_utc,
                              min_altitude=30, min_vmag=10, max_vmag=17,
                              season_name=""):
    """Filter observable targets for a specific season."""
    # Read data
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    # Filter ETV_candidate_type = "uncertain"
    if 'ETV_candidate_type' in df.columns:
        df = df[df['ETV_candidate_type'].str.upper() == 'UNCERTAIN']

    # Exclude strong, confirmed and rejected
    if 'ETV_candidate_status' in df.columns:
        exclude_status = ['STRONG', 'CONFIRMED', 'REJECTED']
        df = df[~df['ETV_candidate_status'].str.upper().isin(exclude_status)]

    # Convert numeric columns
    df['simbad_RA_d'] = pd.to_numeric(df['simbad_RA_d'], errors='coerce')
    df['simbad_DEC_d'] = pd.to_numeric(df['simbad_DEC_d'], errors='coerce')
    df['simbad_V_mag'] = pd.to_numeric(df['simbad_V_mag'], errors='coerce')

    # Coordinate deduplication first
    df = deduplicate_by_coordinates(df, coord_tolerance=0.001)

    # Deduplicate by simbad_name (keep the row with the most precise coordinates)
    df = df.sort_values(
        by=['simbad_name', 'simbad_RA_d', 'simbad_V_mag'],
        ascending=[True, False, False],
        na_position='last'
    )
    df = df.drop_duplicates(subset=['simbad_name'], keep='first')

    # Calculate altitude
    alt_list = []
    az_list = []

    for idx, row in df.iterrows():
        ra = row['simbad_RA_d']
        dec = row['simbad_DEC_d']

        if pd.notna(ra) and pd.notna(dec):
            alt, az = calculate_altitude(ra, dec, longitude_deg, latitude_deg, time_utc)
            alt_list.append(alt)
            az_list.append(az)
        else:
            alt_list.append(np.nan)
            az_list.append(np.nan)

    df[f'altitude_{season_name}'] = alt_list
    df[f'azimuth_{season_name}'] = az_list

    # Filter observable targets
    mask = (
        df[f'altitude_{season_name}'] > min_altitude) & \
        df['simbad_V_mag'].notna() & \
        (df['simbad_V_mag'] >= min_vmag) & \
        (df['simbad_V_mag'] <= max_vmag)

    filtered_df = df[mask].copy()
    filtered_df = filtered_df.sort_values('simbad_V_mag', ascending=True)

    # Save
    filtered_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"   {season_name}: {len(filtered_df)} targets")

    return filtered_df, df


def generate_season_report(df_with_all_seasons, output_file="etv_experiments/season_comparison_report.csv"):
    """Generate a comparison report of observable targets across the four seasons."""
    print("\n" + "=" * 70)
    print("Seasonal Observable Target Comparison Report")
    print("=" * 70)

    # Get observable target names for each season
    seasons = ['spring', 'summer', 'autumn', 'winter']
    season_names = {'spring': 'Spring', 'summer': 'Summer', 'autumn': 'Autumn', 'winter': 'Winter'}

    season_targets = {}
    for season in seasons:
        alt_col = f'altitude_{season}'
        if alt_col in df_with_all_seasons.columns:
            mask = (
                df_with_all_seasons[alt_col].notna() &
                (df_with_all_seasons[alt_col] > 30) &
                df_with_all_seasons['simbad_V_mag'].notna() &
                (df_with_all_seasons['simbad_V_mag'] >= 10) &
                (df_with_all_seasons['simbad_V_mag'] <= 17)
            )
            season_targets[season] = set(df_with_all_seasons[mask]['simbad_name'].dropna())

    # Statistics
    print(f"\nObservable targets per season:")
    print("-" * 40)
    for season in seasons:
        count = len(season_targets.get(season, set()))
        print(f"   {season_names[season]}: {count}")

    # Overlap analysis
    print(f"\nSeason overlap analysis:")
    print("-" * 40)

    # Targets visible in all four seasons
    common_all = set.intersection(*[season_targets[s] for s in seasons]) if all(season_targets[s] for s in seasons) else set()
    print(f"   Visible in all four seasons: {len(common_all)}")

    # Pairwise intersections
    for i, s1 in enumerate(seasons):
        for s2 in seasons[i + 1:]:
            common = season_targets[s1] & season_targets[s2]
            print(f"   {season_names[s1]} + {season_names[s2]}: {len(common)}")

    # Unique targets
    print(f"\nTargets unique to each season:")
    print("-" * 40)
    for season in seasons:
        others = set().union(*[season_targets[s] for s in seasons if s != season])
        unique = season_targets[season] - others
        print(f"   {season_names[season]} only: {len(unique)}")

        # Show the first 5 unique targets
        if len(unique) > 0:
            unique_list = list(unique)[:5]
            print(f"       examples: {', '.join(unique_list)}")

    # Create report DataFrame
    report_data = []
    for season in seasons:
        season_data = df_with_all_seasons[
            (df_with_all_seasons[f'altitude_{season}'] > 30) &
            df_with_all_seasons['simbad_V_mag'].notna() &
            (df_with_all_seasons['simbad_V_mag'] >= 10) &
            (df_with_all_seasons['simbad_V_mag'] <= 17)
        ].copy()

        if len(season_data) > 0:
            season_data['season'] = season_names[season]
            season_data['altitude'] = season_data[f'altitude_{season}']
            season_data['azimuth'] = season_data[f'azimuth_{season}']
            report_data.append(season_data[['simbad_name', 'season', 'altitude', 'azimuth', 'simbad_V_mag']])

    if report_data:
        report_df = pd.concat(report_data, ignore_index=True)
        report_df = report_df.sort_values(['simbad_name', 'season'])

        # Save report
        report_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nDetailed report saved: {output_file}")

        # Count how many seasons each target is visible in
        season_count = report_df.groupby('simbad_name').size().reset_index(name='seasons_count')
        print(f"\nDistribution of visible-season counts:")
        print("-" * 40)
        for count in range(1, 5):
            num = len(season_count[season_count['seasons_count'] == count])
            print(f"   {count} season(s): {num} targets")

    return report_df


def merge_and_deduplicate_all_seasons(season_files, output_file="etv_experiments/all_unique_observable_targets.csv"):
    """Merge the four seasonal observable target lists, deduplicate, and save."""
    print("\n" + "=" * 70)
    print("Merging and deduplicating all seasons")
    print("=" * 70)

    season_names = {'spring': 'Spring', 'summer': 'Summer', 'autumn': 'Autumn', 'winter': 'Winter'}

    all_dfs = []

    for season_key, file_path in season_files.items():
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            df['season'] = season_names[season_key]
            all_dfs.append(df)
            print(f"   {season_names[season_key]}: {len(df)} targets")
        except FileNotFoundError:
            print(f"   File not found: {file_path}")

    if not all_dfs:
        print("No data to merge")
        return None

    # Merge
    combined_df = pd.concat(all_dfs, ignore_index=True)
    print(f"\nBefore merge: {len(combined_df)} records")

    # Coordinate deduplication
    combined_dedup = deduplicate_by_coordinates(combined_df, coord_tolerance=0.001)

    # Aggregate season information
    def aggregate_seasons(group):
        seasons_list = group['season'].unique().tolist()
        seasons_str = ' + '.join(seasons_list)
        first_row = group.iloc[0].copy()
        first_row['seasons'] = seasons_str
        first_row['season_count'] = len(seasons_list)
        return first_row

    # Group by coordinates and aggregate season information
    result_df = combined_dedup.groupby(['simbad_RA_d', 'simbad_DEC_d']).apply(aggregate_seasons).reset_index(drop=True)

    # Sort by observable-season count and magnitude
    result_df = result_df.sort_values(['season_count', 'simbad_V_mag'], ascending=[False, True])

    print(f"After deduplication: {len(result_df)} unique targets")

    # Seasonal distribution statistics
    print(f"\nSeason distribution:")
    for count in range(1, 5):
        num = len(result_df[result_df['season_count'] == count])
        print(f"   visible in {count} season(s): {num} targets")

    # Save
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nSaved: {output_file}")

    return result_df


if __name__ == "__main__":
    # ===== Observing site (Lenghu) =====
    OBS_LONGITUDE = 93.90
    OBS_LATITUDE = 38.60

    # ===== Observation times for the four seasons (UTC, ~22:00 local time) =====
    seasons = {
        'spring': {'time': '2026-03-20 14:00:00', 'name': 'Spring (Mar 20)'},
        'summer': {'time': '2026-06-21 14:00:00', 'name': 'Summer (Jun 21)'},
        'autumn': {'time': '2026-09-23 14:00:00', 'name': 'Autumn (Sep 23)'},
        'winter': {'time': '2026-12-21 14:00:00', 'name': 'Winter (Dec 21)'}
    }

    # ===== Filtering criteria =====
    MIN_ALTITUDE = 30
    MIN_VMAG = 10
    MAX_VMAG = 17

    print("=" * 70)
    print("ETV Follow-up Observable Target Filtering")
    print("=" * 70)
    print(f"Observing site: longitude={OBS_LONGITUDE} deg, latitude={OBS_LATITUDE} deg")
    print(f"Filtering criteria: V={MIN_VMAG}-{MAX_VMAG}, Alt>{MIN_ALTITUDE} deg")
    print(f"Input file: etv.csv")
    print("=" * 70)

    # Read base data
    base_df = pd.read_csv('etv.csv', encoding='utf-8-sig')

    # Basic filtering
    if 'ETV_candidate_type' in base_df.columns:
        base_df = base_df[base_df['ETV_candidate_type'].str.upper() == 'UNCERTAIN']
    if 'ETV_candidate_status' in base_df.columns:
        exclude_status = ['STRONG', 'CONFIRMED', 'REJECTED']
        base_df = base_df[~base_df['ETV_candidate_status'].str.upper().isin(exclude_status)]

    # Convert numeric columns
    base_df['simbad_RA_d'] = pd.to_numeric(base_df['simbad_RA_d'], errors='coerce')
    base_df['simbad_DEC_d'] = pd.to_numeric(base_df['simbad_DEC_d'], errors='coerce')
    base_df['simbad_V_mag'] = pd.to_numeric(base_df['simbad_V_mag'], errors='coerce')

    # Coordinate deduplication
    base_df = deduplicate_by_coordinates(base_df, coord_tolerance=0.001)

    # Deduplicate by simbad_name
    base_df = base_df.sort_values(
        by=['simbad_name', 'simbad_RA_d', 'simbad_V_mag'],
        ascending=[True, False, False],
        na_position='last'
    )
    base_df = base_df.drop_duplicates(subset=['simbad_name'], keep='first')

    print(f"\nAfter basic filtering: {len(base_df)} candidates")

    # Calculate altitudes for each season
    all_seasons_df = base_df.copy()
    season_files = {}
    season_results = {}

    print(f"\nCalculating altitudes for the four seasons...")
    for season_key, season_info in seasons.items():
        print(f"\n   {season_info['name']}")
        print(f"      Time: {season_info['time']} (UTC)")

        # Calculate altitudes
        alt_list = []
        az_list = []

        for idx, row in all_seasons_df.iterrows():
            ra = row['simbad_RA_d']
            dec = row['simbad_DEC_d']

            if pd.notna(ra) and pd.notna(dec):
                alt, az = calculate_altitude(ra, dec, OBS_LONGITUDE, OBS_LATITUDE, season_info['time'])
                alt_list.append(alt)
                az_list.append(az)
            else:
                alt_list.append(np.nan)
                az_list.append(np.nan)

        all_seasons_df[f'altitude_{season_key}'] = alt_list
        all_seasons_df[f'azimuth_{season_key}'] = az_list

        # Filter observable targets and save
        mask = (
            all_seasons_df[f'altitude_{season_key}'] > MIN_ALTITUDE) & \
            all_seasons_df['simbad_V_mag'].notna() & \
            (all_seasons_df['simbad_V_mag'] >= MIN_VMAG) & \
            (all_seasons_df['simbad_V_mag'] <= MAX_VMAG)

        season_df = all_seasons_df[mask].copy()
        season_df = season_df.sort_values('simbad_V_mag', ascending=True)

        output_file = f"{OUTPUT_DIR}observable_targets_{season_key}.csv"
        season_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        season_files[season_key] = output_file
        season_results[season_key] = season_df

        print(f"      Observable targets: {len(season_df)}")
        print(f"      Saved: {output_file}")

    # ===== Deduplicate the four seasonal files separately =====
    deduplicate_season_files(season_files, coord_tolerance=0.001)

    # Reload the deduplicated files (update season_results)
    for season_key, file_path in season_files.items():
        season_results[season_key] = pd.read_csv(file_path, encoding='utf-8-sig')

    # Save the complete data (with all seasonal altitudes)
    all_seasons_df.to_csv(f'{OUTPUT_DIR}etv_all_seasons_altitude.csv', index=False, encoding='utf-8-sig')
    print(f"\nComplete data saved: {OUTPUT_DIR}etv_all_seasons_altitude.csv")

    # ===== Generate comparison report =====
    generate_season_report(all_seasons_df, f"{OUTPUT_DIR}season_comparison_report.csv")

    # ===== Merge and deduplicate all seasons =====
    merge_and_deduplicate_all_seasons(season_files, f"{OUTPUT_DIR}all_unique_observable_targets.csv")

    # ===== Annual observation plan recommendation =====
    print("\n" + "=" * 70)
    print("Annual Observation Plan Recommendation")
    print("=" * 70)

    all_targets = set()
    for season in ['spring', 'summer', 'autumn', 'winter']:
        targets = set(season_results[season]['simbad_name'].dropna())
        all_targets.update(targets)

    print(f"\nTotal observable targets across the year: {len(all_targets)}")

    # Count per season
    season_names = {'spring': 'Spring', 'summer': 'Summer', 'autumn': 'Autumn', 'winter': 'Winter'}
    for season in ['spring', 'summer', 'autumn', 'winter']:
        count = len(season_results[season])
        print(f"   {season_names[season]}: {count}")

    # Recommended best observing season
    best_season = max(season_results.keys(), key=lambda x: len(season_results[x]))
    print(f"\nRecommended best observing season: {season_names[best_season]} ({len(season_results[best_season])} targets)")

    print("\n" + "=" * 70)
    print("All tasks completed!")
    print("\nOutput files:")
    print("   - etv_experiments/observable_targets_spring.csv")
    print("   - etv_experiments/observable_targets_summer.csv")
    print("   - etv_experiments/observable_targets_autumn.csv")
    print("   - etv_experiments/observable_targets_winter.csv")
    print("   - etv_experiments/etv_all_seasons_altitude.csv")
    print("   - etv_experiments/season_comparison_report.csv")
    print("   - etv_experiments/all_unique_observable_targets.csv")
    print("=" * 70)
