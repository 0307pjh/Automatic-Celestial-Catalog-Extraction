import json
import csv
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from config import DEEPSEEK_CLIENT
from prompts import FILTER_PROMPT


# ===================== Global statistics variables =====================
time_stats = {
    "api_extract": {
        "total_time": 0.0,
        "count": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_input_chars": 0,
        "total_output_chars": 0,
    },
    "total": {
        "total_time": 0.0,
        "papers": 0
    }
}

stats_lock = Lock()


# ===================== Print time statistics =====================
def print_time_stats():
    """Print time statistics"""
    print("\n" + "="*80)
    print("Time Statistics Report")
    print("="*80)
    
    # API statistics
    api = time_stats["api_extract"]
    if api["count"] > 0:
        avg = api["total_time"] / api["count"]
        print(f"\n[API Calls]")
        print(f"  Total time: {api['total_time']:.2f} s")
        print(f"  Count: {api['count']}")
        print(f"  Avg: {avg:.2f} s/call")
        if api["total_input_tokens"] > 0:
            print(f"  Tokens - Input: {api['total_input_tokens']:,}")
            print(f"  Tokens - Output: {api['total_output_tokens']:,}")
            print(f"  Tokens - Total: {api['total_input_tokens'] + api['total_output_tokens']:,}")
        if api["total_input_chars"] > 0:
            print(f"  Chars - Input: {api['total_input_chars']:,}")
            print(f"  Chars - Output: {api['total_output_chars']:,}")
            print(f"  Chars - Total: {api['total_input_chars'] + api['total_output_chars']:,}")
    
    # Overall statistics
    total = time_stats["total"]
    print(f"\n[Overall]")
    print(f"  Total time: {total['total_time']:.2f} s ({total['total_time']/60:.2f} min)")
    print(f"  Papers processed: {total['papers']}")
    if total['papers'] > 0 and total['total_time'] > 0:
        print(f"  Avg per paper: {total['total_time']/total['papers']:.2f} s/paper")
    
    print("="*80)


# ===================== Define output structure =====================
class BrownDwarfClassification:
    """Brown dwarf paper classification result"""
    def __init__(self, data: Dict[str, Any]):
        self.has_candidate_discovery = data.get("has_candidate_discovery", 0)
        self.has_confirmed_discovery = data.get("has_confirmed_discovery", 0)
        self.has_parameter_update = data.get("has_parameter_update", 0)
        self.candidate_count = data.get("candidate_count", 0)
        self.confirmed_count = data.get("confirmed_count", 0)
        self.primary_category = data.get("primary_category", "none")
        self.confidence = data.get("confidence", "low")
        self.reasoning = data.get("reasoning", "")


# ===================== Load paper data =====================
def load_papers_from_json(json_file: str) -> List[Dict[str, Any]]:
    """Read paper data from JSON file (one JSON object per line)"""
    papers = []
    with open(json_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                paper = json.loads(line)
                papers.append(paper)
            except json.JSONDecodeError as e:
                print(f"Warning: JSON parse error: {e}")
                continue
    return papers


# ===================== Single paper classification function =====================
def classify_single_paper(
    paper: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: int = 2,
    timeout: int = 1000
) -> Dict[str, Any]:
    """
    Classify a single paper (direct API call)
    """
    paper_id = paper.get("id", "")
    abstract = paper.get("abstract", "")
    input_chars = len(abstract)
    
    # If abstract is too short, return default result
    if not abstract or len(abstract.strip()) < 50:
        return {
            "paper_id": paper_id.replace(".", "_"),
            "has_candidate_discovery": 0,
            "has_confirmed_discovery": 0,
            "has_parameter_update": 0,
            "candidate_count": 0,
            "confirmed_count": 0,
            "primary_category": "none",
            "confidence": "low",
            "reasoning": "abstract too short or empty",
            "_input_chars": input_chars,
            "_output_chars": 0,
            "_input_tokens": 0,
            "_output_tokens": 0,
            "_api_time": 0.0
        }
    
    for attempt in range(max_retries):
        try:
            api_start_time = time.time()
            
            completion = DEEPSEEK_CLIENT.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": FILTER_PROMPT},
                    {"role": "user", "content": f"<abstract>{abstract}</abstract>"}
                ],
                response_format={"type": "json_object"},
                extra_body={"enable_thinking": False, "enable_search": False},
                seed=1,
                temperature=0,
                top_p=0.01,
                max_tokens=300000,
                timeout=timeout
            )
            
            api_elapsed = time.time() - api_start_time
            raw_content = completion.choices[0].message.content or ""
            output_chars = len(raw_content)
            
            # Get token information
            input_tokens = 0
            output_tokens = 0
            if hasattr(completion, "usage") and completion.usage:
                input_tokens = completion.usage.prompt_tokens or 0
                output_tokens = completion.usage.completion_tokens or 0
            
            # Clean Markdown code blocks
            cleaned = raw_content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            result_data = json.loads(cleaned)
            
            # Print raw output
            print(f"  Raw output: {raw_content[:200]}..." if len(raw_content) > 200 else raw_content)
            
            return {
                "paper_id": paper_id.replace(".", "_"),
                "has_candidate_discovery": result_data.get("has_candidate_discovery", 0),
                "has_confirmed_discovery": result_data.get("has_confirmed_discovery", 0),
                "has_parameter_update": result_data.get("has_parameter_update", 0),
                "candidate_count": result_data.get("candidate_count", 0),
                "confirmed_count": result_data.get("confirmed_count", 0),
                "primary_category": result_data.get("primary_category", "none"),
                "confidence": result_data.get("confidence", "low"),
                "reasoning": result_data.get("reasoning", ""),
                "_input_chars": input_chars,
                "_output_chars": output_chars,
                "_input_tokens": input_tokens,
                "_output_tokens": output_tokens,
                "_api_time": api_elapsed
            }
            
        except json.JSONDecodeError as e:
            print(f"  JSON parse error for {paper_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return {
                "paper_id": paper_id.replace(".", "_"),
                "has_candidate_discovery": 0,
                "has_confirmed_discovery": 0,
                "has_parameter_update": 0,
                "candidate_count": 0,
                "confirmed_count": 0,
                "primary_category": "none",
                "confidence": "low",
                "reasoning": f"JSON parse error: {str(e)}",
                "_input_chars": input_chars,
                "_output_chars": 0,
                "_input_tokens": 0,
                "_output_tokens": 0,
                "_api_time": 0.0
            }
            
        except Exception as e:
            print(f"  API call error for {paper_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return {
                "paper_id": paper_id.replace(".", "_"),
                "has_candidate_discovery": 0,
                "has_confirmed_discovery": 0,
                "has_parameter_update": 0,
                "candidate_count": 0,
                "confirmed_count": 0,
                "primary_category": "none",
                "confidence": "low",
                "reasoning": f"API error: {str(e)}",
                "_input_chars": input_chars,
                "_output_chars": 0,
                "_input_tokens": 0,
                "_output_tokens": 0,
                "_api_time": 0.0
            }
    
    return {
        "paper_id": paper_id.replace(".", "_"),
        "has_candidate_discovery": 0,
        "has_confirmed_discovery": 0,
        "has_parameter_update": 0,
        "candidate_count": 0,
        "confirmed_count": 0,
        "primary_category": "none",
        "confidence": "low",
        "reasoning": "max retries exceeded",
        "_input_chars": input_chars,
        "_output_chars": 0,
        "_input_tokens": 0,
        "_output_tokens": 0,
        "_api_time": 0.0
    }


# ===================== Parallel batch classification =====================
def batch_classify_parallel(
    papers: List[Dict[str, Any]],
    max_workers: int = 2000,
    max_retries: int = 3,
    retry_delay: int = 2
) -> List[Dict[str, Any]]:
    """
    Parallel batch classification
    """
    results = [None] * len(papers)
    total = len(papers)
    completed_count = 0
    lock = Lock()
    
    # Statistics
    total_api_time = 0.0
    total_input_chars = 0
    total_output_chars = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    print(f"\nStarting parallel classification, max workers: {max_workers}")
    print(f"   Total papers: {total}")
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(classify_single_paper, paper, max_retries, retry_delay): idx
            for idx, paper in enumerate(papers)
        }
        
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
                results[idx] = result
                
                # Accumulate statistics
                if result:
                    total_api_time += result.get("_api_time", 0)
                    total_input_chars += result.get("_input_chars", 0)
                    total_output_chars += result.get("_output_chars", 0)
                    total_input_tokens += result.get("_input_tokens", 0)
                    total_output_tokens += result.get("_output_tokens", 0)
                
                with lock:
                    completed_count += 1
                    if completed_count % 10 == 0 or completed_count == total:
                        elapsed = time.time() - start_time
                        rate = completed_count / elapsed if elapsed > 0 else 0
                        print(f"   Progress: {completed_count}/{total} ({completed_count/total*100:.1f}%) | "
                              f"Elapsed: {elapsed:.1f}s | Rate: {rate:.2f} papers/s")
                        
            except Exception as e:
                print(f"  Task execution error (index {idx}): {e}")
                results[idx] = {
                    "paper_id": papers[idx].get("id", "").replace(".", "_"),
                    "has_candidate_discovery": 0,
                    "has_confirmed_discovery": 0,
                    "has_parameter_update": 0,
                    "candidate_count": 0,
                    "confirmed_count": 0,
                    "primary_category": "none",
                    "confidence": "low",
                    "reasoning": f"execution error: {str(e)}",
                    "_input_chars": 0,
                    "_output_chars": 0,
                    "_input_tokens": 0,
                    "_output_tokens": 0,
                    "_api_time": 0.0
                }
    
    elapsed = time.time() - start_time
    
    # Update global statistics
    with stats_lock:
        time_stats["api_extract"]["total_time"] = total_api_time
        time_stats["api_extract"]["count"] = total
        time_stats["api_extract"]["total_input_tokens"] = total_input_tokens
        time_stats["api_extract"]["total_output_tokens"] = total_output_tokens
        time_stats["api_extract"]["total_input_chars"] = total_input_chars
        time_stats["api_extract"]["total_output_chars"] = total_output_chars
        time_stats["total"]["total_time"] = elapsed
        time_stats["total"]["papers"] = total
    
    print(f"\nParallel classification complete, total time: {elapsed:.2f}s, avg: {elapsed/total:.2f}s/paper")
    
    return results


# ===================== Save results =====================
def save_results_to_csv(results: List[Dict[str, Any]], output_file: str):
    """Save classification results to CSV file"""
    
    expected_columns = [
        "paper_id",
        "has_candidate_discovery",
        "has_confirmed_discovery",
        "has_parameter_update",
        "candidate_count",
        "confirmed_count",
        "primary_category",
        "confidence",
        "reasoning"
    ]
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=expected_columns, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        
        for result in results:
            if result is None:
                continue
            row = {col: result.get(col, "") for col in expected_columns}
            writer.writerow(row)
    
    print(f"\nResults saved to: {output_file}")


# ===================== Summary statistics =====================
def print_summary(results: List[Dict[str, Any]]):
    """Print summary statistics"""
    total = len(results)
    
    candidate_count = sum(1 for r in results if r and r.get("has_candidate_discovery") == 1)
    confirmed_count = sum(1 for r in results if r and r.get("has_confirmed_discovery") == 1)
    update_count = sum(1 for r in results if r and r.get("has_parameter_update") == 1)
    
    category_counts = {}
    for r in results:
        if r is None:
            continue
        cat = r.get("primary_category", "none")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\n" + "="*60)
    print("Classification Summary")
    print("="*60)
    print(f"Total papers: {total}")
    print(f"  With candidate discovery: {candidate_count} papers")
    print(f"  With confirmed discovery: {confirmed_count} papers")
    print(f"  With parameter update: {update_count} papers")
    print(f"\nPrimary category distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} papers")
    print("="*60)


# ===================== Main entry point =====================
def main():
    # Configuration
    json_file = "test2.json"
    output_file = "brown_dwarf_classification_results.csv"
    max_workers = 100  # Concurrency, adjust based on API rate limit and machine performance
    
    # 1. Load paper data
    print(f"Loading: {json_file}")
    papers = load_papers_from_json(json_file)
    print(f"   Loaded {len(papers)} papers")
    
    if not papers:
        print("No papers loaded")
        return
    
    # 2. Parallel classification
    results = batch_classify_parallel(papers, max_workers=max_workers)
    
    # 3. Save results
    save_results_to_csv(results, output_file)
    
    # 4. Print summary
    print_summary(results)
    
    # 5. Print time statistics
    print_time_stats()


if __name__ == "__main__":
    main()