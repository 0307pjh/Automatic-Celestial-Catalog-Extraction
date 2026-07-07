# config.py
# Configuration file — API keys, model selection, concurrency parameters, timeout settings, etc.
# Corresponding sections: 3.2 (Filtering), 3.3 (Extraction), 4.1.2 (LLM Benchmark)

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI

load_dotenv()

# ===================== API Configuration =====================

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

AIHUBMIX_API_KEY = os.getenv("AIHUBMIX_API_KEY")
AIHUBMIX_BASE_URL = os.getenv("AIHUBMIX_BASE_URL")


# ===================== Model Names =====================
# Candidate models for Section 4.1.2 benchmark experiments

DEEPSEEK_V4_PRO = "deep-deepseek-v4-pro"
DEEPSEEK_V4_FLASH = "deep-deepseek-v4-flash"          # Final selected model
CLAUDE_4_5 = "claude-haiku-4-5-20251001"
GEMINI_3_5_FLASH = "gemini-3.5-flash"
GPT_4_1 = "gpt-4.1"


# ===================== API Clients =====================

QWEN_CLIENT = OpenAI(
    api_key=QWEN_API_KEY,
    base_url=QWEN_BASE_URL,
)

AIHUBMIX_CLIENT = OpenAI(
    api_key=AIHUBMIX_API_KEY,
    base_url=AIHUBMIX_BASE_URL
)

DEEPSEEK_CLIENT = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# Primary LLM client used for the extraction pipeline (Section 4.2)
DEEPSEEK_LLM = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    seed=1,
    temperature=0,
    top_p=0.01,
    max_tokens=300000,
    timeout=1000,
    max_retries=3,
    model_kwargs={
        "response_format": {"type": "json_object"},
        "extra_body": {
            "enable_thinking": False,
            "enable_search": False
        }
    }
)

# ===================== Timeout Configuration =====================

# Network timeouts
DOWNLOAD_TIMEOUT = 180             # PDF download timeout (seconds)
API_REQUEST_TIMEOUT = 1200          # Single API request timeout
API_CONNECTION_TIMEOUT = 60        # API connection timeout

# Chunk processing timeouts (Section 3.3)
SINGLE_CHUNK_TIMEOUT = 1200         # Single chunk processing timeout
CHUNK_RESULT_TIMEOUT = 1200         # Wait for single chunk result timeout
OVERALL_CHUNK_TIMEOUT = 7200       # Overall chunks processing timeout
CHUNK_QUEUE_TIMEOUT = 60            # Chunk queue timeout

# Paper processing timeout (Section 3.3)
PAPER_PROCESS_TIMEOUT = 10800        # Per-paper total timeout

# Retry configuration
MAX_RETRIES = 3                    # Maximum retry attempts
RETRY_DELAY = 5                    # Retry delay (seconds)
RETRY_BACKOFF = 2                  # Retry backoff multiplier


# ===================== Concurrency Configuration =====================
# See Section 4 for parallelization settings

MAX_WORKERS = 50                    # Concurrent papers
CHUNK_WORKERS = 25                  # Concurrent chunks per paper
PAGES_PER_CHUNK = 2                # Pages per chunk (Section 3.3)


# ===================== File Path Configuration =====================

OUTPUT_FILE = "brown_dwarf.csv"                       # Extracted catalog output
ASTRO_PAPERS = Path("validate_brown_dwarf.json")       # Filtered paper list (Section 3.2)


# ===================== Logging Configuration =====================

LOG_FILE = "processing_log.json"                      # Processing logs with status and errors

# ===================== PDF Processing Configuration =====================

PDF_ROOT = "./brown_dwarf"                             # Local storage for downloaded PDFs

# ===================== Backward Compatibility =====================

DEFAULT_TIMEOUT = API_REQUEST_TIMEOUT