import pandas as pd
from typing import Dict, List, Set, Tuple, Optional
import os
import re


def normalize_paper_id(paper_id: str) -> str:
    """Normalize paper ID by replacing dots with underscores"""
    if pd.isna(paper_id) or paper_id == "":
        return ""
    return str(paper_id).strip().replace('.', '_')


def load_and_preprocess_data(doi_standard_path: str, test_csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    doi_df = pd.read_excel(doi_standard_path)
    test_df = pd.read_csv(test_csv_path, encoding='utf-8-sig')
    return doi_df, test_df


def filter_by_is_celestial(df: pd.DataFrame, is_celestial_col: str = 'IsCelestial') -> pd.DataFrame:
    """
    Filter data by IsCelestial field, supporting both numeric and string types
    """
    df = df.copy()
    
    if is_celestial_col not in df.columns:
        print(f"Warning: Column '{is_celestial_col}' not found, using all data")
        return df
    
    print(f"Debug info:")
    print(f"   - Column type: {df[is_celestial_col].dtype}")
    print(f"   - Unique values: {df[is_celestial_col].unique()[:20]}")
    
    try:
        numeric_vals = pd.to_numeric(df[is_celestial_col], errors='coerce')
        filtered_df = df[numeric_vals == 1].copy()
    except:
        filtered_df = df[df[is_celestial_col].astype(str).str.strip() == '1'].copy()
    
    original_count = len(df)
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    
    print(f"\nIsCelestial filter statistics:")
    print(f"   - Original count: {original_count}")
    print(f"   - Retained (IsCelestial=1): {filtered_count}")
    print(f"   - Removed: {removed_count}")
    
    return filtered_df


def filter_by_type(df: pd.DataFrame, exclude_candidate_flag: bool = False, type_col: str = 'Type') -> pd.DataFrame:
    """
    Filter by Type field, optionally excluding planet candidates
    
    Args:
        df: Input DataFrame
        exclude_candidate_flag: If True, exclude planet candidates
        type_col: Type column name
    
    Returns:
        Filtered DataFrame
    """
    df = df.copy()
    
    if not exclude_candidate_flag:
        print(f"Type filter: exclude_candidate_flag = False, keeping all types")
        return df
    
    if type_col not in df.columns:
        print(f"Warning: Column '{type_col}' not found, skipping type filter")
        return df
    
    original_count = len(df)
    
    exclude_patterns = ['unnamed', 'candidate']
    
    type_str = df[type_col].fillna('').astype(str).str.lower().str.strip()
    exclude_mask = pd.Series(False, index=df.index)
    
    for pattern in exclude_patterns:
        exclude_mask = exclude_mask | type_str.str.contains(pattern, na=False)
    
    filtered_df = df[~exclude_mask].copy()
    
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    
    print(f"\nType filter statistics (exclude_candidate_flag = True):")
    print(f"   - Original count: {original_count}")
    print(f"   - Removed candidates: {removed_count}")
    print(f"   - Retained: {filtered_count}")
    
    excluded_types = df[exclude_mask][type_col].unique()
    if len(excluded_types) > 0:
        print(f"   - Excluded types: {excluded_types[:5].tolist()}")
    
    return filtered_df


def clean_name(name: str, remove_hyphens: bool = True) -> str:
    """
    Clean celestial object name for matching and comparison
    """
    if pd.isna(name):
        return ""
    
    name = str(name).strip()
    
    # Unify hyphens
    hyphen_map = {
        '−': '-', '‐': '-', '‑': '-', '‒': '-',
        '–': '-', '—': '-', '―': '-', '﹣': '-', '－': '-'
    }
    for old, new in hyphen_map.items():
        name = name.replace(old, new)
    
    # Unify brackets
    name = name.replace('（', '(').replace('）', ')')
    name = name.replace('【', '[').replace('】', ']')
    
    # Unify quotes
    quote_map = {
        '’': "'", '‘': "'", '`': "'", '´': "'",
        '"': '"', '“': '"', '”': '"', '″': '"'
    }
    for old, new in quote_map.items():
        name = name.replace(old, new)
    
    # Unify whitespace
    name = re.sub(r'[\s\u00A0]+', ' ', name)
    
    name = name.strip()
    
    if remove_hyphens:
        name = name.replace('-', '')
    
    name = re.sub(r'\.0\b', '', name)
    name = name.replace('_', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'\s+', '', name)
    name = name.lower()
    
    return name


def is_match(true_name: str, pred_name: str) -> bool:
    if not true_name or not pred_name:
        return False
    return clean_name(true_name) == clean_name(pred_name)


def deduplicate(df: pd.DataFrame, name_col: str = 'Name') -> pd.DataFrame:
    """Deduplicate entries by paper_id and Name"""
    df = df.copy()
    df[name_col] = df[name_col].apply(clean_name)
    df = df[df[name_col] != '']
    res = []
    for pid, group in df.groupby('paper_id'):
        uniq_names = group[name_col].unique()
        res.append(pd.DataFrame({'paper_id': [pid] * len(uniq_names), name_col: uniq_names}))
    return pd.concat(res, ignore_index=True)


def run_eval(doi_df, test_df, name_col='Name'):
    """
    Evaluation function
    
    Args:
        doi_df: Ground truth DataFrame
        test_df: Model prediction DataFrame
        name_col: Object name column
    """
    doi_dedup = deduplicate(doi_df, name_col)
    test_dedup = deduplicate(test_df, name_col)

    doi_dedup['pid_norm'] = doi_dedup['paper_id'].apply(normalize_paper_id)
    test_dedup['pid_norm'] = test_dedup['paper_id'].apply(normalize_paper_id)

    doi_pid_set = set(doi_dedup['pid_norm'])
    test_pid_set = set(test_dedup['pid_norm'])

    only_in_doi = doi_pid_set - test_pid_set
    only_in_test = test_pid_set - doi_pid_set
    common_pid = doi_pid_set & test_pid_set

    # Print matching status
    print('=' * 60)
    print('Paper ID matching status')
    print('=' * 60)
    
    if only_in_doi:
        print(f'\n[Missing in prediction] Only in ground truth ({len(only_in_doi)}):')
        for pid in sorted(only_in_doi):
            original_pid = doi_dedup[doi_dedup['pid_norm'] == pid]['paper_id'].iloc[0]
            print(f'   - {original_pid}')
    else:
        print('\n[OK] No paper IDs only in ground truth')
    
    if only_in_test:
        print(f'\n[Extra] Only in prediction ({len(only_in_test)}):')
        for pid in sorted(only_in_test):
            original_pid = test_dedup[test_dedup['pid_norm'] == pid]['paper_id'].iloc[0]
            print(f'   - {original_pid}')
    else:
        print('\n[OK] No paper IDs only in prediction')
    
    print(f'\n[OK] Participating paper IDs ({len(common_pid)}):')
    for pid in sorted(common_pid):
        original_pid = doi_dedup[doi_dedup['pid_norm'] == pid]['paper_id'].iloc[0]
        print(f'   - {original_pid}')
    
    print('=' * 60)
    print()

    if len(common_pid) == 0:
        print("No common paper IDs, cannot evaluate")
        return

    missing_rows = []
    per_file_results = []

    for pid_norm in sorted(common_pid):
        pid_real = doi_dedup[doi_dedup['pid_norm'] == pid_norm]['paper_id'].iloc[0]
        T = list(doi_dedup[doi_dedup['pid_norm'] == pid_norm][name_col])
        P = list(test_dedup[test_dedup['pid_norm'] == pid_norm][name_col])

        matched_T = set()
        matched_P = set()
        for t in T:
            for p in P:
                if is_match(t, p):
                    matched_T.add(t)
                    matched_P.add(p)
                    break

        missing = set(T) - matched_T
        missing_names_original = []
        for name in sorted(missing):
            original_names = doi_df[doi_df['paper_id'] == pid_real]['Name'].tolist()
            original_matches = [orig for orig in original_names if clean_name(orig) == name]
            original_name = original_matches[0] if original_matches else name
            missing_rows.append({'paper_id': pid_real, 'Name': original_name})
            missing_names_original.append(original_name)

        extra = set(P) - matched_P
        extra_names_original = []
        for name in sorted(extra):
            original_names = test_df[test_df['paper_id'] == pid_real]['Name'].tolist()
            original_matches = [orig for orig in original_names if clean_name(orig) == name]
            original_name = original_matches[0] if original_matches else name
            extra_names_original.append(original_name)

        TP = len(matched_T)
        FP = len(extra)
        FN = len(missing)
        precision = TP / (TP + FP) if (TP + FP) != 0 else 0
        recall = TP / (TP + FN) if (TP + FN) != 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) != 0 else 0

        per_file_results.append({
            'id': pid_real,
            'TP': TP,
            'FP': FP,
            'FN': FN,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'missing_names': missing_names_original,
            'extra_names': extra_names_original
        })

    # Sort by F1 score ascending
    per_file_results.sort(key=lambda x: x['f1'])
    
    # Filter out entries with precision == 1.0 and recall == 1.0
    filtered_results = [res for res in per_file_results if not (res['precision'] == 1.0 and res['recall'] == 1.0)]
    
    # Print sorted IDs to console
    print('\n' + '=' * 60)
    print('Paper IDs sorted by F1 score (ascending)')
    print('=' * 60)
    for idx, res in enumerate(filtered_results, 1):
        print(f"{idx:3d}. {res['id']:20}")
    print('=' * 60 + '\n')

    # Output to txt file
    with open('evaluation_results.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Evaluation results sorted by F1 score (ascending)\n")
        f.write("(Entries with Precision=Recall=1.0 are excluded)\n")
        f.write("=" * 80 + "\n\n")
        
        for res in filtered_results:
            f.write(f"paper_id: {res['id']}\n")
            f.write(f"TP (matched): {res['TP']}\n")
            f.write(f"FP (false positives): {res['FP']}\n")
            f.write(f"FN (false negatives): {res['FN']}\n")
            f.write(f"Precision: {res['precision']:.4f}\n")
            f.write(f"Recall: {res['recall']:.4f}\n")
            f.write(f"F1 Score: {res['f1']:.4f}\n")
            
            f.write("Missing objects (in ground truth, not predicted):\n")
            if res['missing_names']:
                for name in res['missing_names']:
                    f.write(f"  - {name}\n")
            else:
                f.write("  (none)\n")
            
            f.write("Extra objects (predicted, not in ground truth):\n")
            if res['extra_names']:
                for name in res['extra_names']:
                    f.write(f"  - {name}\n")
            else:
                f.write("  (none)\n")
            
            f.write("\n" + "-" * 80 + "\n\n")
        
        # Overall statistics
        f.write("\n" + "=" * 80 + "\n")
        f.write("Overall Statistics\n")
        f.write("=" * 80 + "\n")
        total_TP = sum(r['TP'] for r in per_file_results)
        total_FP = sum(r['FP'] for r in per_file_results)
        total_FN = sum(r['FN'] for r in per_file_results)
        total_true = total_TP + total_FN
        total_pred = total_TP + total_FP
        overall_precision = total_TP / total_pred if total_pred != 0 else 0
        overall_recall = total_TP / total_true if total_true != 0 else 0
        overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) != 0 else 0
        
        f.write(f"Total ground truth objects: {total_true}\n")
        f.write(f"Total predicted objects: {total_pred}\n")
        f.write(f"TP (correct matches): {total_TP}\n")
        f.write(f"FP (extra predictions): {total_FP}\n")
        f.write(f"FN (missed objects): {total_FN}\n")
        f.write(f"Overall Precision: {overall_precision:.4f}\n")
        f.write(f"Overall Recall: {overall_recall:.4f}\n")
        f.write(f"Overall F1 Score: {overall_f1:.4f}\n")

    # Save missing objects CSV
    pd.DataFrame(missing_rows).to_csv('missing_names.csv', index=False, encoding='utf-8-sig')

    # Print overall metrics to console
    print('=' * 60)
    print('Overall Evaluation Metrics')
    print('=' * 60)
    print(f'Total ground truth objects: {total_true}')
    print(f'Total predicted objects: {total_pred}')
    print(f'TP (correct matches): {total_TP}')
    print(f'FP (extra predictions): {total_FP}')
    print(f'FN (missed objects): {total_FN}')
    print(f'Precision: {overall_precision:.4f}')
    print(f'Recall: {overall_recall:.4f}')
    print(f'F1 Score: {overall_f1:.4f}')
    print('Saved: missing_names.csv')
    print('Saved: evaluation_results.txt (sorted by F1 score ascending)')


def main():
    # ============================================================
    # Configuration
    # ============================================================
    
    # Option 1: Exclude planet candidates (True=exclude, False=keep)
    exclude_candidate_flag = True

    # ============================================================
    
    # Load data
    doi_df, test_df = load_and_preprocess_data('dataset.xlsx', 'valid_set_qwen_long.csv')
    
    # Filter by IsCelestial
    test_df = filter_by_is_celestial(test_df, is_celestial_col='IsCelestial')
    
    # Filter by Type (exclude candidates)
    test_df = filter_by_type(test_df, exclude_candidate_flag=exclude_candidate_flag, type_col='Type')
    
    # Run evaluation
    run_eval(doi_df, test_df)


if __name__ == '__main__':
    main()