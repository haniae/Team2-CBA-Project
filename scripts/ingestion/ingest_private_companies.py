#!/usr/bin/env python3
"""Example script for ingesting private company data from a proprietary API.

This script demonstrates how to:
1. Connect to a proprietary API for private company data
2. Fetch financial data for private companies
3. Store it in the chatbot database
4. Make it queryable via the chatbot

Usage:
    python scripts/ingestion/ingest_private_companies.py \
        --company-ids PRIV-001 PRIV-002 \
        --years 10

Or with environment variables:
    export ENABLE_PRIVATE_COMPANIES=true
    export PRIVATE_API_URL=https://api.example.com/v1
    export PRIVATE_API_KEY=your_api_key_here
    python scripts/ingestion/ingest_private_companies.py --all
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from datetime import datetime, timezone

from finanlyzeos_chatbot import database
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.data_sources_private import (
    PrivateCompanyClient,
    create_private_company_client,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def ingest_private_company(
    client: PrivateCompanyClient,
    company_id: str,
    database_path: Path,
    years: int = 10,
) -> dict:
    """Ingest data for a single private company.
    
    Args:
        client: PrivateCompanyClient instance
        company_id: Company identifier
        database_path: Path to SQLite database
        years: Number of years of historical data
    
    Returns:
        Dictionary with ingestion results
    """
    LOGGER.info("Ingesting data for private company: %s", company_id)
    
    try:
        # Fetch financial facts
        facts = client.fetch_company_financials(company_id, years=years)
        LOGGER.info("Fetched %d financial facts for %s", len(facts), company_id)
        
        # Store in database
        facts_inserted = 0
        for fact in facts:
            try:
                database.insert_financial_fact(database_path, fact)
                facts_inserted += 1
            except Exception as exc:
                LOGGER.warning(
                    "Failed to insert fact for %s: %s",
                    company_id,
                    exc,
                )
        
        # Add company to ticker aliases for name resolution
        try:
            metadata = client.get_company_metadata(company_id)
            company_name = metadata.get("name", company_id)
            
            # Add alias so chatbot can find the company by name
            # For private companies, use empty string for CIK
            alias_record = database.TickerAliasRecord(
                ticker=company_id,
                cik="",  # Private companies don't have CIKs
                company_name=company_name,
                updated_at=datetime.now(timezone.utc),
            )
            database.upsert_ticker_aliases(database_path, [alias_record])
            LOGGER.info("Added ticker alias: %s -> %s", company_name, company_id)
        except Exception as exc:
            LOGGER.warning(
                "Failed to add ticker alias for %s: %s",
                company_id,
                exc,
            )
        
        return {
            "company_id": company_id,
            "facts_fetched": len(facts),
            "facts_inserted": facts_inserted,
            "success": True,
            "error": None,
        }
    
    except Exception as exc:
        LOGGER.error("Failed to ingest %s: %s", company_id, exc, exc_info=True)
        return {
            "company_id": company_id,
            "facts_fetched": 0,
            "facts_inserted": 0,
            "success": False,
            "error": str(exc),
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest private company data from proprietary API"
    )
    parser.add_argument(
        "--company-ids",
        nargs="+",
        help="List of company IDs to ingest",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all available companies from API",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years of historical data to fetch (default: 10)",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        help="Path to database file (default: from settings)",
    )
    
    args = parser.parse_args()
    
    # Load settings
    settings = load_settings()
    
    # Check if private companies are enabled
    if not settings.enable_private_companies:
        LOGGER.error(
            "Private companies are not enabled. Set ENABLE_PRIVATE_COMPANIES=true"
        )
        sys.exit(1)
    
    # Create private company client
    client = create_private_company_client(settings)
    if not client:
        LOGGER.error(
            "Failed to create private company client. "
            "Check PRIVATE_API_URL and PRIVATE_API_KEY settings."
        )
        sys.exit(1)
    
    # Initialize database
    database_path = args.database_path or settings.database_path
    database.initialise(database_path)
    
    # Determine which companies to ingest
    if args.all:
        LOGGER.info("Fetching list of all companies from API...")
        companies = client.list_companies()
        company_ids = [c["company_id"] for c in companies]
        LOGGER.info("Found %d companies", len(company_ids))
    elif args.company_ids:
        company_ids = args.company_ids
    else:
        LOGGER.error("Must specify either --company-ids or --all")
        sys.exit(1)
    
    # Ingest each company
    results = []
    for company_id in company_ids:
        result = ingest_private_company(
            client,
            company_id,
            database_path,
            years=args.years,
        )
        results.append(result)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Ingestion Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["success"])
    total_facts = sum(r["facts_inserted"] for r in results)
    
    print(f"Companies processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Total facts inserted: {total_facts}")
    
    if any(not r["success"] for r in results):
        print("\nFailures:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['company_id']}: {r['error']}")
    
    print("\n" + "=" * 60)
    print("You can now query these companies via the chatbot!")
    print("Example: 'What is PRIV-001's revenue for 2023?'")
    print("=" * 60)


if __name__ == "__main__":
    main()

