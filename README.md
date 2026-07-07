# Automatic Celestial Catalog Extraction Using Large Language Models

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)
![arXiv](https://img.shields.io/badge/arXiv-XXXX.XXXXX-B31B1B.svg)

Official implementation of the paper:

> **Automatic Celestial Catalog Extraction Using Large Language Models**

**Authors**

Jun-Hao Peng, Yi-Cheng Rui, Peng-Ju Wang, Wen-Yong Kang, Yu-Long Gao, Zheng-Jun Du

---

## Contents

- Overview
- Repository Structure
- Installation
- Usage
- Benchmark Results
- Data Availability
- Citation
- License

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

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/Automatic-Celestial-Catalog-Extraction.git

cd Automatic-Celestial-Catalog-Extraction
```

---

## 2. Create a Python Environment

We recommend using Python **3.11** or newer.

Using `venv`:

```bash
python -m venv venv
```

Activate the environment:

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

Alternatively, using Conda:

```bash
conda create -n celestial python=3.11
conda activate celestial
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Typical dependencies include

- pandas
- numpy
- matplotlib
- scipy
- requests
- tqdm
- PyMuPDF
- pdfplumber
- openai
- langchain
- langchain-core
- langchain-openai
- pydantic

---

# Configuration

The pipeline requires API keys for one or more supported LLM providers.

Create a file named

```text
.env
```

under the project root.

Example:

```text
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENAI_API_KEY=your_openai_api_key
QWEN_API_KEY=your_qwen_api_key
BAIDU_API_KEY=your_baidu_api_key
AIHUBMIX_API_KEY=your_aihubmix_api_key
```

Alternatively, the keys can be configured directly inside

```text
config.py
```

depending on your deployment environment.

---

# Input Data

The pipeline expects a list of candidate papers obtained from arXiv.

The filtering stage automatically identifies brown dwarf related publications.

Input files include

```
validate_brown_dwarf.json
```

which stores the filtered paper list used in the paper.

The extraction stage downloads PDFs automatically and processes them in parallel.

---

# Output

The final structured catalog is exported as

```text
brown_dwarf.csv
```

Each record corresponds to a single literature report rather than a merged object entry.

Representative fields include

| Field | Description |
|------|-------------|
| Name | Object name |
| SpectralType | Spectral classification |
| Mass_MJ | Mass |
| Radius_RJ | Radius |
| EffectiveTemperature_K | Effective temperature |
| LogG | Surface gravity |
| Distance_pc | Distance |
| ProperMotion_RA_mas_yr | Proper motion (RA) |
| ProperMotion_Dec_mas_yr | Proper motion (Dec) |
| RadialVelocity_km_s | Radial velocity |
| Age_Gyr | Age |
| Metallicity | Metallicity |
| DiscoveryReference | Discovery paper |
| DOI | Paper DOI |
| PaperID | arXiv identifier |
| Page | Source page |
| Text | Original extracted text |

All quantities preserve the original values reported in the literature whenever possible.

---

# Supported Models

The extraction framework supports multiple Large Language Models through a unified interface.

Current implementations include

- DeepSeek-V4-Flash
- DeepSeek-V4-Pro
- GPT-5.4-Mini
- Claude-Haiku-4.5
- Gemini-3.5-Flash
- Qwen-Long

Additional models can be incorporated by modifying the model configuration in `config.py`.

---

# Usage

The complete workflow consists of two sequential stages:

1. Paper filtering
2. Catalog extraction

---

# Step 1 — Filter Relevant Papers

Screen astrophysical papers downloaded from arXiv and identify publications containing brown dwarf observations.

Run

```bash
python filter_chain.py
```

Output:

```
validate_brown_dwarf.json
```

which contains all papers selected for catalog extraction.

---

# Step 2 — Extract the Catalog

Run the main extraction pipeline

```bash
python extraction_chain_stream_parallel.py
```

The pipeline automatically performs

- PDF downloading
- PDF chunking
- Parallel processing
- LLM inference
- Result aggregation
- Duplicate removal
- CSV export

The final catalog will be written to

```text
brown_dwarf.csv
```

---

# Optional Arguments

Force reprocessing of all papers

```bash
python extraction_chain_stream_parallel.py --force
```

Retry only failed papers

```bash
python extraction_chain_stream_parallel.py --retry-failed
```

Specify the number of parallel workers

```bash
python extraction_chain_stream_parallel.py \
    --max-workers 30 \
    --chunk-workers 20
```

---

# Evaluation

Model performance can be reproduced using the benchmark dataset provided in

```
valid_experiments/
```

Run

```bash
cd valid_experiments

python metric.py
```

The script computes

- Precision
- Recall
- F1 score

for every evaluated model.

---

# Reproducing Figures

All analysis scripts are located in

```
analysis_experiment/
```

## Figure 3

Physical parameter distributions

```bash
python analysis_experiment/catalog_summary.py
```

---

## Figure 4

Cooling evolution

```bash
python analysis_experiment/age_temp_cooling_evolution.py
```

---

## Figure 5

Brown dwarf kinematics

```bash
python analysis_experiment/kinematic_analysis.py
```

---

## Figure 6

Mass versus semi-major axis

```bash
python analysis_experiment/mass_semimajor.py
```

All figures are exported into

```
Figures/
```

in PDF format suitable for publication.

---

# Pipeline Overview

The automated workflow is summarized below.

```
arXiv

   │

   ▼

Paper Filtering

   │

   ▼

PDF Download

   │

   ▼

PDF Chunking

   │

   ▼

Parallel LLM Extraction

   │

   ▼

Structured JSON

   │

   ▼

Duplicate Checking

   │

   ▼

CSV Catalog

   │

   ▼

Scientific Analysis
```

---

# Reproducibility

The repository contains everything required to reproduce the experiments reported in the paper, including

- benchmark datasets
- evaluation scripts
- extraction prompts
- analysis scripts
- generated figures
- extracted catalog

Running the pipeline with the same configuration should reproduce results that are consistent with those reported in the manuscript, subject to minor variations introduced by stochastic LLM inference.

---

# LLM Benchmark Results

To evaluate the effectiveness of different Large Language Models for astronomical information extraction, we constructed a manually annotated benchmark consisting of

- **Validation set:** 60 papers, 2,818 annotated entities
- **Test set:** 60 papers, 1,511 annotated entities

The benchmark evaluates both object identification and structured parameter extraction.

---

## Performance Comparison

| Model | Precision ↑ | Recall ↑ | F1 ↑ | API Time ↓ | Total Time ↓ | Cost ↓ |
|------|------------:|----------:|------:|-----------:|-------------:|--------:|
| Gemini-3.5-Flash | 94.95% | 88.15% | 91.42% | 23.82 s | 5811.4 s | $69.01 |
| Claude-Haiku-4.5 | 96.04% | 56.00% | 70.75% | 7.84 s | 2657.4 s | $21.06 |
| GPT-5.4-Mini | 92.21% | 72.25% | 81.02% | **3.56 s** | **888.8 s** | $6.29 |
| DeepSeek-V4-Pro | **97.00%** | **94.14%** | **95.55%** | 51.90 s | 18343.8 s | $6.86 |
| **DeepSeek-V4-Flash** | **96.81%** | **92.62%** | **94.67%** | 19.83 s | 4762.4 s | $1.47 |
| Qwen-Long | 96.00% | 86.94% | 91.25% | 12.58 s | 4461.0 s | **$0.80** |

---

## Model Selection

Among all evaluated models, **DeepSeek-V4-Flash** provides the best overall balance between

- extraction accuracy,
- inference efficiency,
- deployment cost, and
- large-scale scalability.

Therefore, it was adopted as the default model for constructing the full brown dwarf catalog presented in this work.

---

## Benchmark Dataset

The complete benchmark is available in

```
valid_experiments/
```

including

```
dataset.xlsx
metric.py
test_set.json
valid_set.json
```

as well as the prediction outputs of all evaluated models.

---

## Evaluation Metrics

The benchmark reports three standard information extraction metrics.

### Precision

\[
\mathrm{Precision}
=
\frac{TP}{TP+FP}
\]

Measures the fraction of extracted entities that are correct.

---

### Recall

\[
\mathrm{Recall}
=
\frac{TP}{TP+FN}
\]

Measures the fraction of ground-truth entities successfully extracted.

---

### F1 Score

\[
F1
=
\frac{2PR}{P+R}
\]

where

- **P** denotes Precision
- **R** denotes Recall

The F1 score is used as the primary evaluation metric throughout the paper.

---

## Cost Analysis

The benchmark demonstrates that extraction quality is not solely determined by model size.

For example,

- DeepSeek-V4-Pro achieved the highest F1 score but required the longest inference time.
- GPT-5.4-Mini exhibited the fastest inference speed.
- Qwen-Long achieved the lowest monetary cost.
- DeepSeek-V4-Flash offered the most favorable trade-off between accuracy, runtime, and cost.

---

## Scalability

Using the selected DeepSeek-V4-Flash model, the complete pipeline processed

- **1,410 papers**
- **21,989 brown dwarfs**
- **49,546 measurement records**

within approximately **25 minutes** at a total API cost of **$14.83**, demonstrating that LLM-based astronomical catalog construction is practical for large-scale literature mining.

---

# Data Availability

The complete brown dwarf catalog generated in this work is included in this repository as

```
brown_dwarf.csv
```

The catalog contains

- **21,989** unique brown dwarfs
- **49,546** literature measurement records

Each record preserves the original literature provenance, including the corresponding publication, page number, and extracted text.

Large datasets and future releases will also be archived through Zenodo.

## Zenodo

```
https://zenodo.org/record/XXXXXXX
```

## DOI

```
10.5281/zenodo.XXXXXXX
```

---

# Citation

If you use this repository, the extracted catalog, or any part of the code in your research, please cite the accompanying paper.

```bibtex
@article{peng2026automatic,
  title={Automatic Celestial Catalog Extraction Using Large Language Models},
  author={Peng, Jun-Hao and Rui, Yi-Cheng and Wang, Peng-Ju and Kang, Wen-Yong and Gao, Yu-Long and Du, Zheng-Jun},
  journal={The Astrophysical Journal},
  year={2026}
}
```

If you use the released catalog, please also cite the corresponding Zenodo dataset after publication.

---

# License

This project is released under the **MIT License**.

See

```
LICENSE
```

for the complete license text.

---

# Acknowledgments

This work was supported in part by

- **Qinghai University Research Ability Enhancement Project**
  (Grant No. **2025KTSQ26**)

- **National Natural Science Foundation of China**
  (Grant No. **62562052**)

We gratefully acknowledge the developers of the open-source software and Large Language Models used throughout this work, as well as the arXiv platform for providing open access to the scientific literature.

---

# Contact

For questions, bug reports, or suggestions, please open an issue on GitHub.

Alternatively, contact the corresponding authors.

**Yi-Cheng Rui**

Email:

```
your_email@example.com
```

**Zheng-Jun Du**

Email:

```
dzj@qhu.edu.cn
```

---

# Project Status

✅ Active

The repository will continue to be updated with

- improved extraction prompts,
- additional benchmark datasets,
- new LLM backends,
- expanded celestial catalogs,
- and future releases accompanying subsequent publications.

---

# Roadmap

Future planned developments include

- [ ] Support for exoplanet extraction
- [ ] Support for stellar catalogs
- [ ] Support for galaxy catalogs
- [ ] Automatic catalog versioning
- [ ] Cross-matching with SIMBAD and Gaia
- [ ] Web-based catalog browser
- [ ] Interactive visualization dashboard

---

# Star History

If you find this repository useful, please consider giving it a ⭐ on GitHub.

It helps increase the visibility of the project and supports future development.

---
