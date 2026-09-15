"""Run news ingestion in the safe, reproducible order.

Publisher/provider metadata is collected first, then deterministic country and
market classification, and finally conservative canonical threading. GDELT is
opt-in because its public endpoint can rate-limit independently.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_worker(name: str, *arguments: str, required: bool = True) -> bool:
    result = subprocess.run([sys.executable, str(ROOT / name), *arguments], check=False)
    if result.returncode and required:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-gdelt", action="store_true", help="Make one optional discovery request after publisher feeds")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run_worker("rss_news.py")
    if (os.environ.get("ALPHA_VANTAGE_API_KEY") or os.environ.get("ALPHA_API_KEY")) and not run_worker("alpha_vantage_news.py", required=False):
        print("Alpha Vantage did not complete; continuing with source-health visibility.")
    if args.with_gdelt and not run_worker("gdelt_discovery.py", required=False):
        print("GDELT did not complete; continuing with publisher evidence already collected.")
    run_worker("classify_news.py")
    run_worker("thread_news_events.py")
    run_worker("fomc_calendar.py")
    if not run_worker("bank_of_england_calendar.py", required=False):
        print("Bank of England calendar did not complete; the official FOMC calendar remains available.")
    if not run_worker("ecb_calendar.py", required=False):
        print("ECB calendar did not complete; the official FOMC and Bank of England calendars remain available.")
    if not run_worker("asia_pacific_policy_calendars.py", required=False):
        print("Asia-Pacific policy calendars did not complete; existing official calendars remain available.")
    if os.environ.get("BUSINESSQUANT_API_KEY") and not run_worker("businessquant_calendar.py", required=False):
        print("BusinessQuant did not complete; the FOMC calendar remains available.")
    print("Research pipeline completed: ingest → classify → canonical-thread → official calendars.")


if __name__ == "__main__":
    main()
