# Automatic Celestial Catalog Extraction Using Large Language Models

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)
![arXiv](https://img.shields.io/badge/arXiv-XXXX.XXXXX-B31B1B.svg)

Official implementation of the paper:

> **Automatic Celestial Catalog Extraction Using Large Language Models**

**Authors**

Jun-Hao Peng, Yi-Cheng Rui, Peng-Ju Wang, Wen-Yong Kang, Yu-Long Gao, Zheng-Jun Du

---

# Overview

This repository contains the official implementation and experimental results for an automated literature-mining pipeline that constructs structured celestial catalogs directly from astrophysical papers using Large Language Models (LLMs).

Unlike traditional rule-based information extraction systems, our framework performs semantic understanding of full-text scientific papers and automatically extracts celestial objects together with their reported physical parameters while preserving literature provenance.

The pipeline consists of two major stages:

1. **Paper Filtering**
   - Automatically screens approximately **340,000** arXiv astrophysics papers.
   - Identifies publications containing brown dwarf observations.

2. **Catalog Extraction**
   - Extracts celestial objects and reported physical parameters.
   - Produces a structured literature-centric catalog with complete provenance information.

---

# Key Results

| Metric | Result |
|---------|--------|
| Papers processed | **1,410** |
| Unique brown dwarfs | **21,989** |
| Measurement records | **49,546** |
| Processing time | **~25 min** |
| Total API cost | **$14.83** |
| Best extraction model | **DeepSeek-V4-Flash** |
| Best F1 score | **94.67%** |

---

# Features

- Automatic literature screening from arXiv
- Large Language Model based information extraction
- Literature-centric catalog construction
- Provenance preservation
- Structured physical parameter extraction
- Parallel PDF processing
- Multi-model benchmarking
- Fully reproducible analysis pipeline

---

# Repository Structure

```
.
├── Figures/
│   ├── Pipeline.pdf
│   ├── age_temp_cooling_evolution.pdf
│   ├── arxiv_astrophysics_yearly.pdf
│   ├── catalog_summary.pdf
│   ├── kinematic_analysis.pdf
│   └── mass_semimajor.pdf
│
├── analysis_experiment/
│   ├── age_temp_cooling_evolution.py
│   ├── catalog_summary.py
│   ├── kinematic_analysis.py
│   └── mass_semimajor.py
│
├── valid_experiments/
│   ├── dataset.xlsx
│   ├── metric.py
│   ├── test_set.json
│   ├── valid_set.json
│   ├── valid_set_claude_haiku_4_5.csv
│   ├── valid_set_deepseek_v4_flash.csv
│   ├── valid_set_deepseek_v4_pro.csv
│   ├── valid_set_gemini_3_5_flash.csv
│   ├── valid_set_gpt_5_4_mini.csv
│   └── valid_set_qwen_long.csv
│
├── brown_dwarf.csv
├── config.py
├── extraction_chain_stream_parallel.py
├── filter_chain.py
├── prompts.py
├── requirements.txt
├── validate_brown_dwarf.json
└── README.md

```

## Directory Description

| Directory | Description |
|------------|-------------|
| Figures | All figures used in the paper |
| analysis_experiment | Scripts for reproducing all figures |
| valid_experiments | LLM benchmark datasets and evaluation |
| brown_dwarf.csv | Final extracted brown dwarf catalog |
| filter_chain.py | Paper filtering pipeline |
| extraction_chain_stream_parallel.py | Main extraction pipeline |
| prompts.py | Prompt templates |
| config.py | Configuration file |

---
