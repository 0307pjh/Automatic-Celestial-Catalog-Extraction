import shutil
from typing import Dict, Any, List, Set, Optional
import os
import requests
import time
import json
import pandas as pd
import fitz  # PyMuPDF
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from threading import Lock
import argparse
from queue import Queue, Empty

# ===================== Import all configurations from config =====================
from config import (
    AIHUBMIX_CLIENT,
    DEEPSEEK_CLIENT,
    QWEN_CLIENT,
    ASTRO_PAPERS,
    OUTPUT_FILE,
    LOG_FILE,
    PDF_ROOT,
    DOWNLOAD_TIMEOUT,
    API_REQUEST_TIMEOUT,
    API_CONNECTION_TIMEOUT,
    SINGLE_CHUNK_TIMEOUT,
    CHUNK_RESULT_TIMEOUT,
    OVERALL_CHUNK_TIMEOUT,
    CHUNK_QUEUE_TIMEOUT,
    PAPER_PROCESS_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    RETRY_BACKOFF,
    MAX_WORKERS,
    CHUNK_WORKERS,
    PAGES_PER_CHUNK,
    DEFAULT_TIMEOUT,
)

from prompts import BROWN_DWARF_PROMPT


# ===================== Global statistics and locks =====================
time_stats = {
    "download": {"total_time": 0.0, "count": 0, "total_pages": 0},
    "extract_text": {"total_time": 0.0, "count": 0, "total_pages": 0, "total_chars": 0},
    "api_extract": {
        "total_time": 0.0,
        "count": 0,
        "total_pages": 0,
        "total_chunks": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_input_chars": 0,
        "total_output_chars": 0,
    },
    "total": {"total_time": 0.0, "papers": 0, "total_pages": 0}
}

stats_lock = Lock()
csv_lock = Lock()
log_lock = Lock()


# ===================== Utility functions =====================
def arxiv_id_to_safe(arxiv_id: str) -> str:
    """Convert arXiv ID to safe filename format (underscore)"""
    return arxiv_id.replace(".", "_").replace("/", "_").replace("\\", "_")

def safe_to_arxiv_id(safe_id: str) -> str:
    """Convert safe format back to arXiv ID (dot)"""
    return safe_id.replace("_", ".")

def find_existing_pdf(safe_id: str, pdf_root: str) -> Optional[str]:
    """
    Check if PDF already exists, supporting multiple naming formats:
    1. Underscore format: safe_id.pdf (e.g., astro-ph_0312285.pdf)
    2. Dot format: arxiv_id.pdf (e.g., astro-ph.0312285.pdf)
    3. Slash format: original format (e.g., astro-ph/0312285.pdf)
    """
    # 1. Check underscore format (most common)
    path_underscore = os.path.join(pdf_root, f"{safe_id}.pdf")
    if os.path.exists(path_underscore):
        return path_underscore
    
    # 2. Check dot format (arXiv standard format)
    arxiv_id = safe_to_arxiv_id(safe_id)
    path_dot = os.path.join(pdf_root, f"{arxiv_id}.pdf")
    if os.path.exists(path_dot):
        return path_dot
    
    # 3. Check slash format (if original ID contains /)
    if '/' in safe_id:
        path_slash = os.path.join(pdf_root, f"{safe_id}.pdf")
        if os.path.exists(path_slash):
            return path_slash
    
    # 4. Try other underscore variants
    if '/' in safe_id:
        safe_version = safe_id.replace('/', '_')
        path_variant = os.path.join(pdf_root, f"{safe_version}.pdf")
        if os.path.exists(path_variant):
            return path_variant
    
    return None

def get_processed_papers_from_csv(output_file: str) -> Set[str]:
    if not os.path.exists(output_file):
        return set()
    try:
        processed = set()
        with open(output_file, 'r', encoding='utf-8-sig', newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("paper_id", "").strip()
                if pid:
                    processed.add(pid)
        return processed
    except Exception:
        try:
            df = pd.read_csv(output_file, dtype=str)
            if "paper_id" in df.columns:
                return set(df["paper_id"].dropna().unique())
        except Exception:
            pass
        return set()

def load_processing_log(log_file: str = LOG_FILE) -> Dict[str, Any]:
    default_log = {
        "processed_papers": [],
        "failed_papers": [],
        "last_run": None,
        "total_processed": 0,
        "total_failed": 0
    }
    if not os.path.exists(log_file):
        return default_log
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log = json.load(f)
        for k in default_log:
            if k not in log:
                log[k] = default_log[k]
        return log
    except Exception:
        return default_log

def save_processing_log(safe_id: str, status: str, error_msg: str = "", log_file: str = LOG_FILE):
    with log_lock:
        log = load_processing_log(log_file)
        if status == "success":
            if safe_id not in log["processed_papers"]:
                log["processed_papers"].append(safe_id)
            log["failed_papers"] = [
                item for item in log["failed_papers"]
                if item.get("paper_id") != safe_id
            ]
        else:
            exist = any(item.get("paper_id") == safe_id for item in log["failed_papers"])
            if not exist:
                log["failed_papers"].append({
                    "paper_id": safe_id,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
        log["last_run"] = datetime.now().isoformat()
        log["total_processed"] = len(log["processed_papers"])
        log["total_failed"] = len(log["failed_papers"])
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save log: {e}")

def print_time_stats():
    print("\n" + "="*80)
    print("Time Statistics Report")
    print("="*80)
    dl = time_stats["download"]
    if dl["count"] > 0:
        avg = dl["total_time"] / dl["count"]
        print(f"\n[PDF Download] Total: {dl['total_time']:.2f}s | Count: {dl['count']} | Avg: {avg:.2f}s/request | Total pages: {dl['total_pages']}")
    ext = time_stats["extract_text"]
    if ext["count"] > 0:
        avg = ext["total_time"] / ext["count"]
        print(f"\n[Text Extraction] Total: {ext['total_time']:.2f}s | Count: {ext['count']} | Avg: {avg:.2f}s/request | Total chars: {ext['total_chars']:,}")
    api = time_stats["api_extract"]
    if api["count"] > 0:
        avg = api["total_time"] / api["count"]
        print(f"\n[API Calls] Total: {api['total_time']:.2f}s | Count: {api['count']} | Avg: {avg:.2f}s/call | Total chunks: {api['total_chunks']}")
        if api["total_input_tokens"] > 0:
            print(f"  Tokens - Input: {api['total_input_tokens']:,} | Output: {api['total_output_tokens']:,}")
        if api["total_input_chars"] > 0:
            print(f"  Chars - Input: {api['total_input_chars']:,} | Output: {api['total_output_chars']:,}")
    total = time_stats["total"]
    print(f"\n[Overall] Total time: {total['total_time']:.2f}s ({total['total_time']/60:.2f}min) | Papers: {total['papers']} | Total pages: {total['total_pages']}")
    print("="*80)

def save_targets_to_csv_immediate(
    safe_paper_id: str, chunk_id: int, pages: str,
    targets: List[Dict], output_file: str
):
    """Save extracted targets to CSV"""
    if not targets:
        return
    
    processed = []
    for target in targets:
        if hasattr(target, "dict"):
            td = target.dict()
        elif isinstance(target, dict):
            td = target.copy()
        else:
            td = {"data": str(target)}
        
        td["paper_id"] = safe_paper_id
        td["source_chunk"] = chunk_id
        td["source_pages"] = pages
        
        for k, v in td.items():
            if isinstance(v, str):
                td[k] = v.replace("\n", " ").replace("\r", " ").replace("\t", " ").strip()
        processed.append(td)
    
    if not processed:
        return

    expected_cols = [
    # Identifier fields
    "Name",
    "Type",
    "RA",
    "RA_Error",
    "Dec",
    "Dec_Error",
    "SpectralType",
    "IsBrownDwarf",
    
    # Physical parameters: Mass_MJ (value + error + unit)
    "Mass_MJ",
    "Mass_MJ_Error_Plus",
    "Mass_MJ_Error_Minus",
    "Mass_MJ_unit",
    "Mass_Msun",
    "Mass_Msun_Error_Plus",
    "Mass_Msun_Error_Minus",
    "Mass_Msun_unit",
    "Radius_RJ",
    "Radius_RJ_Error_Plus",
    "Radius_RJ_Error_Minus",
    "Radius_RJ_unit",
    "EffectiveTemperature_K",
    "EffectiveTemperature_K_Error_Plus",
    "EffectiveTemperature_K_Error_Minus",
    "EffectiveTemperature_K_unit",
    "LogG",
    "LogG_Error_Plus",
    "LogG_Error_Minus",
    "LogG_unit",
    
    "Reason",
    
    # Coordinate related
    "Parallax_mas",
    "Parallax_mas_Error_Plus",
    "Parallax_mas_Error_Minus",
    "Parallax_mas_unit",
    "Distance_pc",
    "Distance_pc_Error_Plus",
    "Distance_pc_Error_Minus",
    "Distance_pc_unit",
    "ProperMotion_RA_mas_yr",
    "ProperMotion_RA_mas_yr_Error_Plus",
    "ProperMotion_RA_mas_yr_Error_Minus",
    "ProperMotion_RA_mas_yr_unit",
    "ProperMotion_Dec_mas_yr",
    "ProperMotion_Dec_mas_yr_Error_Plus",
    "ProperMotion_Dec_mas_yr_Error_Minus",
    "ProperMotion_Dec_mas_yr_unit",
    
    # Redshift (dimensionless, no unit field)
    "Redshift",
    "Redshift_Error_Plus",
    "Redshift_Error_Minus",
    
    # Brightness
    "Brightness",
    "Brightness_Error_Plus",
    "Brightness_Error_Minus",
    "Brightness_unit",
    "Band",
    
    # Radius (solar)
    "Radius_Sun",
    "Radius_Sun_Error_Plus",
    "Radius_Sun_Error_Minus",
    "Radius_Sun_unit",
    
    # Metallicity
    "Metallicity_FeH",
    "Metallicity_FeH_Error_Plus",
    "Metallicity_FeH_Error_Minus",
    "Metallicity_FeH_unit",
    
    # Age
    "Age_Gyr",
    "Age_Gyr_Error_Plus",
    "Age_Gyr_Error_Minus",
    "Age_Gyr_unit",
    
    # Luminosity
    "Luminosity_logLbol",
    "Luminosity_logLbol_Error_Plus",
    "Luminosity_logLbol_Error_Minus",
    "Luminosity_logLbol_unit",
    
    # Orbital parameters
    "SemiMajorAxis_AU",
    "SemiMajorAxis_AU_Error_Plus",
    "SemiMajorAxis_AU_Error_Minus",
    "SemiMajorAxis_AU_unit",
    "OrbitalPeriod_days",
    "OrbitalPeriod_days_Error_Plus",
    "OrbitalPeriod_days_Error_Minus",
    "OrbitalPeriod_days_unit",
    # Eccentricity (dimensionless, no unit field)
    "Eccentricity",
    "Eccentricity_Error_Plus",
    "Eccentricity_Error_Minus",
    "Inclination_deg",
    "Inclination_deg_Error_Plus",
    "Inclination_deg_Error_Minus",
    "Inclination_deg_unit",
    "VelocitySemiamplitude_K",
    "VelocitySemiamplitude_K_Error_Plus",
    "VelocitySemiamplitude_K_Error_Minus",
    "VelocitySemiamplitude_K_unit",
    
    # System fields
    "HostStar",
    "SystemType",
    "BinaryFlag",
    "IsDiscoveryTarget",
    "DiscoveryInstrument",
    
    # Metadata
    "paper_id",
    "source_chunk",
    "source_pages"
]
    
    df = pd.DataFrame(processed)
    
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    
    df = df[expected_cols]

    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with csv_lock:
        file_exists = os.path.exists(output_file)
        df.to_csv(
            output_file,
            mode="a" if file_exists else "w",
            header=not file_exists,
            index=False,
            encoding="utf-8-sig",
            quoting=csv.QUOTE_MINIMAL
        )


# ===================== PDF download and text extraction =====================
def download_pdf_if_needed(arxiv_id: str, safe_id: str, pdf_root: str) -> Optional[str]:
    """Download PDF, return existing path if already present"""
    existing_path = find_existing_pdf(safe_id, pdf_root)
    if existing_path:
        print(f"  PDF already exists: {os.path.basename(existing_path)}")
        return existing_path
    
    pdf_path = os.path.join(pdf_root, f"{safe_id}.pdf")
    arxiv_id_dot = arxiv_id.replace('_', '.')
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id_dot}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        resp = requests.get(pdf_url, timeout=DOWNLOAD_TIMEOUT, headers=headers)
        resp.raise_for_status()
        os.makedirs(pdf_root, exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(resp.content)
        print(f"  Download complete: {os.path.basename(pdf_path)}")
        return pdf_path
    except Exception as e:
        print(f"  Download failed for {arxiv_id}: {e}")
        return None

def extract_chunks_from_paper(arxiv_id: str, safe_id: str, pdf_path: str, pages_per_chunk: int = 1) -> List[Dict]:
    """Extract all chunks from paper, return list of chunks"""
    chunks = []
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        for chunk_num in range((total_pages + pages_per_chunk - 1) // pages_per_chunk):
            cid = chunk_num + 1
            s_page = chunk_num * pages_per_chunk
            e_page = min(s_page + pages_per_chunk, total_pages)
            page_range = f"{s_page+1}-{e_page}"
            
            text_parts = []
            for page_num in range(s_page, e_page):
                if page_num >= len(doc):
                    break
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"\n\n--- Page {page_num + 1} ---\n\n{page_text}")
                else:
                    words = page.get_text("words")
                    if words:
                        word_str = " ".join([w[4] for w in words if len(w) > 4])
                        text_parts.append(f"\n\n--- Page {page_num + 1} ---\n\n{word_str}")
                    else:
                        text_parts.append(f"\n\n--- Page {page_num + 1} ---\n\n[Text extraction failed]")
            
            chunk_text = "".join(text_parts)
            if chunk_text and len(chunk_text.strip()) >= 50:
                chunks.append({
                    "safe_id": safe_id,
                    "chunk_id": cid,
                    "pages": page_range,
                    "text": chunk_text
                })
        
        doc.close()
        return chunks
    except Exception as e:
        print(f"  Chunk extraction failed for {arxiv_id}: {e}")
        return []


def cleanup_pdf_after_processing(pdf_path: str, safe_id: str):
    """Delete PDF immediately after processing"""
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"  PDF deleted: {os.path.basename(pdf_path)}")
            return True
    except Exception as e:
        print(f"  Failed to delete PDF for {safe_id}: {e}")
    return False


# ===================== LLM processing functions =====================
def process_single_chunk_with_llm(
    safe_paper_id: str, chunk_id: int, pages: str, chunk_text: str,
    output_file: str, client, max_retries: int = MAX_RETRIES, 
    retry_delay: int = RETRY_DELAY
) -> List[Dict]:
    """Process a single chunk using BROWN_DWARF_PROMPT"""
    if not chunk_text or len(chunk_text.strip()) < 50:
        return []

    for attempt in range(max_retries):
        try:
            api_start = time.time()
            completion = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": BROWN_DWARF_PROMPT},
                    {"role": "user", "content": f"<target_paper>\n{chunk_text}\n</target_paper>"}
                ],
                response_format={"type": "json_object"},
                extra_body={"enable_thinking": False, "enable_search": False},
                seed=1,
                temperature=0,
                top_p=0.01,
                max_tokens=350000,
                timeout=API_REQUEST_TIMEOUT
            )
            api_elapsed = time.time() - api_start

            with stats_lock:
                time_stats["api_extract"]["total_time"] += api_elapsed
                time_stats["api_extract"]["count"] += 1
                time_stats["api_extract"]["total_chunks"] += 1
                time_stats["api_extract"]["total_input_chars"] += len(chunk_text)
                if completion.choices[0].message.content:
                    out_content = completion.choices[0].message.content
                    time_stats["api_extract"]["total_output_chars"] += len(out_content)
                if hasattr(completion, "usage") and completion.usage:
                    time_stats["api_extract"]["total_input_tokens"] += completion.usage.prompt_tokens
                    time_stats["api_extract"]["total_output_tokens"] += completion.usage.completion_tokens

            raw_content = completion.choices[0].message.content or ""
            
            if not raw_content.strip():
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (RETRY_BACKOFF ** attempt)
                    time.sleep(wait_time)
                    continue
                return []
            
            cleaned = raw_content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            try:
                res = json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (RETRY_BACKOFF ** attempt)
                    time.sleep(wait_time)
                    continue
                return []
            
            if isinstance(res, dict):
                chunk_targets = res.get("targets", [])
            else:
                chunk_targets = []
            
            valid = []
            for t in chunk_targets:
                if isinstance(t, dict) and t.get("Name"):
                    valid.append(t)
            
            if valid:
                save_targets_to_csv_immediate(safe_paper_id, chunk_id, pages, valid, output_file)
            
            return valid

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (RETRY_BACKOFF ** attempt)
                print(f"      Retry {attempt+2}/{max_retries} in {wait_time}s... (error: {str(e)[:50]})")
                time.sleep(wait_time)
                continue
            return []
    return []


# ===================== Single paper processing (with chunk-level parallelism) =====================
def process_single_paper(
    arxiv_id: str, safe_id: str, output_file: str, client,
    pages_per_chunk: int = PAGES_PER_CHUNK, 
    max_retries: int = MAX_RETRIES, 
    retry_delay: int = RETRY_DELAY,
    total_papers: int = 1, paper_idx: int = 1,
    chunk_workers: int = CHUNK_WORKERS
) -> bool:
    """
    Process a single paper: download -> extract chunks -> parallel process all chunks -> delete PDF
    Supports chunk-level parallelism
    """
    print(f"\n{'='*60}")
    print(f"[{paper_idx}/{total_papers}] Processing paper: {arxiv_id} (ID: {safe_id})")
    print(f"{'='*60}")
    
    paper_start_time = time.time()
    pdf_path = None
    
    try:
        # 1. Download PDF
        print(f"  Step 1/4: Checking/downloading PDF...")
        pdf_path = download_pdf_if_needed(arxiv_id, safe_id, PDF_ROOT)
        if not pdf_path:
            save_processing_log(safe_id, "failed", "PDF download failed")
            return False
        
        # 2. Extract all chunks
        print(f"  Step 2/4: Extracting text chunks...")
        chunks = extract_chunks_from_paper(arxiv_id, safe_id, pdf_path, pages_per_chunk)
        
        if not chunks:
            print(f"  Warning: No valid chunks extracted")
            cleanup_pdf_after_processing(pdf_path, safe_id)
            save_processing_log(safe_id, "failed", "No valid text chunks")
            return False
        
        # Get total page count
        try:
            with fitz.open(pdf_path) as doc:
                total_pages_doc = len(doc)
            print(f"  Extracted {len(chunks)} chunks (Total pages: {total_pages_doc})")
        except:
            print(f"  Extracted {len(chunks)} chunks")
        
        # 3. Parallel process all chunks
        print(f"  Step 3/4: Parallel processing {len(chunks)} chunks (chunk workers: {chunk_workers})...")
        print(f"      Single chunk timeout: {SINGLE_CHUNK_TIMEOUT}s, Overall timeout: {OVERALL_CHUNK_TIMEOUT}s")
        
        all_targets = []
        chunk_success = 0
        chunk_empty = 0
        chunk_error = 0
        chunk_timeout = 0
        
        actual_workers = min(chunk_workers, len(chunks))
        chunk_start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=actual_workers) as chunk_executor:
            future_to_chunk = {}
            for idx, chunk in enumerate(chunks, 1):
                chunk_id = chunk["chunk_id"]
                pages = chunk["pages"]
                chunk_text = chunk["text"]
                
                future = chunk_executor.submit(
                    process_single_chunk_with_llm,
                    safe_id, chunk_id, pages, chunk_text,
                    output_file, client, max_retries, retry_delay
                )
                future_to_chunk[future] = (idx, chunk_id, pages)
            
            # Collect results with overall timeout
            remaining = set(future_to_chunk.keys())
            
            while remaining:
                # Check overall timeout
                if time.time() - chunk_start_time > OVERALL_CHUNK_TIMEOUT:
                    print(f"  Overall timeout reached ({OVERALL_CHUNK_TIMEOUT}s), canceling remaining {len(remaining)} chunks")
                    for f in remaining:
                        f.cancel()
                        chunk_timeout += 1
                    break
                
                # Wait for next completion (max 30s)
                done, remaining = wait(remaining, timeout=30, return_when=FIRST_COMPLETED)
                
                for future in done:
                    idx, chunk_id, pages = future_to_chunk[future]
                    try:
                        result = future.result(timeout=CHUNK_RESULT_TIMEOUT)
                        if result:
                            chunk_success += 1
                            all_targets.extend(result)
                            print(f"      Chunk [{idx}/{len(chunks)}] {safe_id}_{chunk_id} (pages {pages}) completed: {len(result)} targets")
                        else:
                            chunk_empty += 1
                            print(f"      Chunk [{idx}/{len(chunks)}] {safe_id}_{chunk_id} (pages {pages}) completed: no valid targets")
                    except Exception as e:
                        chunk_error += 1
                        print(f"      Chunk [{idx}/{len(chunks)}] {safe_id}_{chunk_id} (pages {pages}) error: {e}")
        
        print(f"  Chunk processing summary: {chunk_success} with targets, {chunk_empty} empty, {chunk_error} errors, {chunk_timeout} timeouts")
        
        # 4. Delete PDF
        print(f"  Step 4/4: Cleaning up PDF...")
        cleanup_pdf_after_processing(pdf_path, safe_id)
        pdf_path = None
        
        # 5. Log results
        paper_elapsed = time.time() - paper_start_time
        
        if all_targets:
            save_processing_log(safe_id, "success")
            print(f"  [{paper_idx}/{total_papers}] {arxiv_id} completed! "
                  f"Extracted {len(all_targets)} targets (time: {paper_elapsed:.2f}s)")
        else:
            save_processing_log(safe_id, "success")
            print(f"  [{paper_idx}/{total_papers}] {arxiv_id} completed! "
                  f"No targets found (time: {paper_elapsed:.2f}s)")
        
        return True
        
    except Exception as e:
        paper_elapsed = time.time() - paper_start_time
        print(f"  [{paper_idx}/{total_papers}] {arxiv_id} failed: {e} (time: {paper_elapsed:.2f}s)")
        if pdf_path and os.path.exists(pdf_path):
            cleanup_pdf_after_processing(pdf_path, safe_id)
        save_processing_log(safe_id, "failed", str(e))
        return False


# ===================== Streaming parallel main function =====================
def process_papers_streaming(
    arxiv_ids: List[str],
    output_file: str,
    client,
    max_workers: int = MAX_WORKERS,
    chunk_workers: int = CHUNK_WORKERS,
    pages_per_chunk: int = PAGES_PER_CHUNK,
    max_retries: int = MAX_RETRIES,
    retry_delay: int = RETRY_DELAY,
    force_reprocess: bool = False
) -> Dict[str, Any]:
    """
    Streaming parallel processing for all papers - paper-level + chunk-level parallelism
    """
    print("\n" + "="*80)
    print("Starting streaming parallel processing")
    print("="*80)
    print(f"Total papers: {len(arxiv_ids)}")
    print(f"Paper workers: {max_workers}")
    print(f"Chunk workers: {chunk_workers}")
    print(f"Pages per chunk: {pages_per_chunk}")
    print(f"Single chunk timeout: {SINGLE_CHUNK_TIMEOUT}s")
    print(f"Overall chunk timeout: {OVERALL_CHUNK_TIMEOUT}s")
    print(f"Paper total timeout: {PAPER_PROCESS_TIMEOUT}s")
    print(f"PDF root: {PDF_ROOT}")
    print(f"Output file: {output_file}")
    print("="*80)
    
    start_time = time.time()
    
    # Get already processed papers (resume support)
    processed_papers = get_processed_papers_from_csv(output_file) if not force_reprocess else set()
    print(f"\nResume mode: {len(processed_papers)} papers already processed")
    
    # Filter papers to process
    papers_to_process = []
    for arxiv_id in arxiv_ids:
        safe_id = arxiv_id_to_safe(arxiv_id)
        if safe_id not in processed_papers:
            papers_to_process.append(arxiv_id)
    
    if not papers_to_process:
        print("All papers already processed")
        return {"papers": 0, "chunks": 0, "status": "done"}
    
    print(f"Pending: {len(papers_to_process)} papers\n")
    
    # Parallel process papers
    success_count = 0
    fail_count = 0
    total_papers = len(papers_to_process)
    
    actual_paper_workers = min(max_workers, len(papers_to_process))
    
    with ThreadPoolExecutor(max_workers=actual_paper_workers) as executor:
        futures = {}
        for idx, arxiv_id in enumerate(papers_to_process, 1):
            safe_id = arxiv_id_to_safe(arxiv_id)
            future = executor.submit(
                process_single_paper,
                arxiv_id, safe_id, output_file, client,
                pages_per_chunk, max_retries, retry_delay,
                total_papers, idx,
                chunk_workers
            )
            futures[future] = (arxiv_id, idx)
        
        # Collect results with PAPER_PROCESS_TIMEOUT
        for future in as_completed(futures):
            arxiv_id, idx = futures[future]
            try:
                result = future.result(timeout=PAPER_PROCESS_TIMEOUT)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
                
                # Print overall progress
                completed = success_count + fail_count
                pct = completed / total_papers * 100
                print(f"\nOverall progress: {completed}/{total_papers} ({pct:.1f}%) "
                      f"| Success: {success_count} | Failed: {fail_count}")
                
            except Exception as e:
                print(f"\nPaper {arxiv_id} timeout/error: {e}")
                fail_count += 1
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print("Streaming processing complete!")
    print("="*80)
    print(f"Total time: {elapsed:.2f}s ({elapsed/60:.2f}min)")
    print(f"Total papers: {total_papers}")
    print(f"Success: {success_count} papers")
    print(f"Failed: {fail_count} papers")
    if total_papers > 0:
        print(f"Success rate: {success_count/total_papers*100:.1f}%")
    print("="*80)
    
    return {
        "papers": total_papers,
        "success": success_count,
        "failed": fail_count,
        "total_time": elapsed,
        "status": "done"
    }


# ===================== Main entry point =====================
def main():
    parser = argparse.ArgumentParser(description="arXiv paper brown dwarf entity extraction tool - paper-level + chunk-level parallel version")
    parser.add_argument("--force", action="store_true", help="Force full reprocessing")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only historically failed papers")
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS, help="Paper parallel threads")
    parser.add_argument("--chunk-workers", type=int, default=CHUNK_WORKERS, help="Chunk parallel threads per paper")
    parser.add_argument("--pages-per-chunk", type=int, default=PAGES_PER_CHUNK, help="Pages per chunk")
    args = parser.parse_args()

    total_start = time.time()
    json_path = ASTRO_PAPERS
    output_file = OUTPUT_FILE
    client = DEEPSEEK_CLIENT

    if not os.path.exists(json_path):
        print(f"Data source file not found: {json_path}")
        return
    
    try:
        with open(json_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        all_arxiv_ids = [rec["id"] for rec in data.get("records", []) if rec.get("id")]
        if not all_arxiv_ids:
            print("No valid paper IDs found")
            return
        print(f"Loaded {len(all_arxiv_ids)} paper IDs")
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        return

    to_process: List[str] = []
    skipped_count = 0
    
    if args.force:
        to_process = all_arxiv_ids
        print("Force mode: full reprocessing")
    elif args.retry_failed:
        log = load_processing_log()
        failed_items = log.get("failed_papers", [])
        failed_safe_ids = []
        for it in failed_items:
            if isinstance(it, dict) and "paper_id" in it:
                failed_safe_ids.append(it["paper_id"])
            elif isinstance(it, str):
                failed_safe_ids.append(it)
        to_process = [safe_to_arxiv_id(sid) for sid in failed_safe_ids]
        print(f"Retry mode: {len(to_process)} historically failed papers to retry")
    else:
        processed_safe = get_processed_papers_from_csv(output_file)
        for aid in all_arxiv_ids:
            sid = arxiv_id_to_safe(aid)
            if sid in processed_safe:
                skipped_count += 1
            else:
                to_process.append(aid)
        print(f"\nStatistics: Total {len(all_arxiv_ids)} | Processed {skipped_count} | Pending {len(to_process)}")
        if not to_process:
            print("All papers processed, nothing to do")
            return

    max_workers = max(1, min(args.max_workers, 100))
    chunk_workers = max(1, min(args.chunk_workers, 50))
    pages_per_chunk = args.pages_per_chunk
    
    result = process_papers_streaming(
        to_process,
        output_file,
        client,
        max_workers=max_workers,
        chunk_workers=chunk_workers,
        pages_per_chunk=pages_per_chunk,
        force_reprocess=args.force
    )
    
    total_elapsed = time.time() - total_start
    with stats_lock:
        time_stats["total"]["total_time"] = total_elapsed
    
    print_time_stats()
    print(f"\nLog: {LOG_FILE}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()