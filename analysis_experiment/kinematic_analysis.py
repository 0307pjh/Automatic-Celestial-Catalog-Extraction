#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
褐矮星运动学分析（APJ投稿格式）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import warnings
warnings.filterwarnings('ignore')

# ========== 配置 ==========
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
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

# ========== 提取数值函数 ==========
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

# ========== 单位转换函数 ==========
def convert_pm(value, unit):
    """将自行统一转换为 mas/yr"""
    if pd.isna(value) or pd.isna(unit):
        return np.nan
    unit_str = str(unit).strip().lower()
    # 已经是 mas/yr
    if unit_str in ['mas/yr', 'mas yr^-1']:
        return value
    # arcsec/yr -> mas/yr (×1000)
    if unit_str in ['arcsec/yr', 'arcsec yr^-1', '"/yr', 'asec yr−1']:
        return value * 1000.0
    return np.nan

def convert_distance(value, unit):
    """将距离统一转换为 pc"""
    if pd.isna(value) or pd.isna(unit):
        return np.nan
    unit_str = str(unit).strip().lower()
    if unit_str in ['pc', 'parsec']:
        return value
    elif unit_str == 'kpc':
        return value * 1000.0
    return np.nan

# ========== 读取数据 ==========
print("="*70)
print("📂 读取数据")
print("="*70)

df = pd.read_csv('brown_dwarf.csv', low_memory=False)
print(f"原始数据: {len(df):,} 行")

# 只保留褐矮星
df = df[df['IsBrownDwarf'] == 1.0].copy()
print(f"褐矮星: {len(df):,} 行")

# ========== 提取自行数据 ==========
print("\n" + "="*70)
print("📋 自行数据提取 + 单位转换")
print("="*70)

df['PM_RA_raw'] = df['ProperMotion_RA_mas_yr'].apply(extract_mid_value)
df['PM_DEC_raw'] = df['ProperMotion_Dec_mas_yr'].apply(extract_mid_value)

df['PM_RA'] = df.apply(lambda row: convert_pm(row['PM_RA_raw'], row['ProperMotion_RA_mas_yr_unit']), axis=1)
df['PM_DEC'] = df.apply(lambda row: convert_pm(row['PM_DEC_raw'], row['ProperMotion_Dec_mas_yr_unit']), axis=1)

print(f"  PM_RA 有效值: {df['PM_RA'].notna().sum():,}")
print(f"  PM_DEC 有效值: {df['PM_DEC'].notna().sum():,}")

# ========== 提取距离数据 ==========
print("\n" + "="*70)
print("📊 距离数据提取 + 单位转换")
print("="*70)

df['Distance_raw'] = df['Distance_pc'].apply(extract_mid_value)
df['Distance'] = df.apply(lambda row: convert_distance(row['Distance_raw'], row['Distance_pc_unit']), axis=1)

print(f"  Distance 有效值: {df['Distance'].notna().sum():,}")

# ========== 筛选有效数据 ==========
print("\n" + "="*70)
print("📊 数据筛选")
print("="*70)

df_clean = df.dropna(subset=['PM_RA', 'PM_DEC', 'Distance'])
df_clean = df_clean[(df_clean['Distance'] > 1) & (df_clean['Distance'] < 200)]

print(f"  有效数据: {len(df_clean):,} 行")

if len(df_clean) < 10:
    print("❌ 数据量不足，退出")
    exit()

# ========== 计算自行和速度 ==========
print("\n" + "="*70)
print("📊 运动学计算")
print("="*70)

df_clean['PM_total'] = np.sqrt(
    df_clean['PM_RA']**2 +
    df_clean['PM_DEC']**2
)
df_clean['PM_total_arcsec'] = (
    df_clean['PM_total'] / 1000.0
)
# 切向速度计算
# V_tan(km/s)=4.74 * μ(arcsec/yr) * d(pc)
df_clean['V_tan'] = (
    4.74 *
    df_clean['PM_total_arcsec'] *
    df_clean['Distance']
)

print(f"  速度统计:")
print(f"    最小值: {df_clean['V_tan'].min():.1f} km/s")
print(f"    最大值: {df_clean['V_tan'].max():.1f} km/s")
print(f"    平均值: {df_clean['V_tan'].mean():.1f} km/s")
print(f"    中位数: {df_clean['V_tan'].median():.1f} km/s")

# ========== 绘图 ==========
print("\n" + "="*70)
print("🎨 生成图片")
print("="*70)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.8))

# 左图：距离-速度关系
scatter = ax1.scatter(df_clean['Distance'], df_clean['V_tan'],
                      c=np.log10(df_clean['V_tan'] + 1), cmap='plasma',
                      s=25, alpha=0.7, edgecolors='none')
ax1.set_xlabel('Distance (pc)', fontsize=9.0)
ax1.set_ylabel('Tangential Velocity (km s$^{-1}$)', fontsize=9.0)
ax1.set_title(f'(a) Distance vs Tangential Velocity (N={len(df_clean)})', fontsize=10)

ax1.axhline(550, color='red', linestyle='--', alpha=0.7, linewidth=1.2, label='Galactic Escape')
ax1.axhline(200, color='orange', linestyle='--', alpha=0.7, linewidth=1.2, label='Thick Disk')
ax1.axhline(50, color='gray', linestyle='--', alpha=0.7, linewidth=1.2, label='Thin Disk')
ax1.legend(fontsize=7, frameon=True, fancybox=False, edgecolor='black')

cbar = plt.colorbar(scatter, ax=ax1)
cbar.set_label(r'$\log(V_{\rm tan})$', fontsize=7)

ax1.set_xlim(0, 250)
ax1.set_ylim(0, 600)

# 右图：速度直方图
bins = np.linspace(0, 300, 31)
ax2.hist(df_clean['V_tan'], bins=bins, color='#2870B3', edgecolor='white', alpha=0.8)
ax2.axvline(50, color='gray', linestyle='--', alpha=0.7, linewidth=1.2, label='Thin Disk')
ax2.axvline(200, color='orange', linestyle='--', alpha=0.7, linewidth=1.2, label='Thick Disk')
ax2.axvline(550, color='red', linestyle='--', alpha=0.7, linewidth=1.2, label='Escape')

ax2.set_xlabel('Tangential Velocity (km s$^{-1}$)', fontsize=9.0)
ax2.set_ylabel('Number', fontsize=9.0)
ax2.set_title(f'(b) Velocity Distribution (N={len(df_clean)})', fontsize=10)
ax2.set_xlim(0, 220)
ax2.legend(fontsize=7, frameon=True, fancybox=False, edgecolor='black')

# ========== 保存 ==========
plt.tight_layout()
plt.savefig('kinematic_analysis.pdf', dpi=300, facecolor='white')
print("\n✅ 已保存: kinematic_analysis.pdf")

# ========== 统计 ==========
print("\n" + "="*70)
print("📊 运动学分类统计")
print("="*70)

n_total = len(df_clean)
n_thin = (df_clean['V_tan'] < 50).sum()
n_thick = ((df_clean['V_tan'] >= 50) & (df_clean['V_tan'] < 200)).sum()
n_halo = ((df_clean['V_tan'] >= 200) & (df_clean['V_tan'] < 550)).sum()
n_escape = (df_clean['V_tan'] >= 550).sum()

print(f"  总样本: {n_total}")
print(f"  薄盘 (< 50 km/s):        {n_thin:4d} ({n_thin/n_total*100:5.1f}%)")
print(f"  厚盘 (50-200 km/s):      {n_thick:4d} ({n_thick/n_total*100:5.1f}%)")
print(f"  晕 (200-550 km/s):       {n_halo:4d} ({n_halo/n_total*100:5.1f}%)")
print(f"  逃逸 (> 550 km/s):       {n_escape:4d} ({n_escape/n_total*100:5.1f}%)")

print("\n" + "="*70)
print("✅ 完成！")
print("="*70)