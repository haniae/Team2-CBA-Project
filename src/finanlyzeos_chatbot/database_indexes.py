"""Database indexing optimization for high-performance queries."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Tuple

LOGGER = logging.getLogger(__name__)


class DatabaseIndexOptimizer:
    """Manages database indexes for optimal query performance."""
    
    # Critical indexes for frequently queried columns
    PERFORMANCE_INDEXES = [
        # Metric snapshots - most frequently queried table
        ("idx_metric_snapshots_ticker", "metric_snapshots", ["ticker"]),
        ("idx_metric_snapshots_metric", "metric_snapshots", ["metric"]),
        ("idx_metric_snapshots_ticker_metric", "metric_snapshots", ["ticker", "metric"]),
        ("idx_metric_snapshots_period", "metric_snapshots", ["period"]),
        ("idx_metric_snapshots_updated_at", "metric_snapshots", ["updated_at"]),
        
        # Financial facts - second most queried
        ("idx_financial_facts_ticker", "financial_facts", ["ticker"]),
        ("idx_financial_facts_metric", "financial_facts", ["metric"]),
        ("idx_financial_facts_ticker_metric", "financial_facts", ["ticker", "metric"]),
        ("idx_financial_facts_fiscal_year", "financial_facts", ["fiscal_year"]),
        ("idx_financial_facts_period", "financial_facts", ["period"]),
        
        # Market quotes - for current prices
        ("idx_market_quotes_ticker", "market_quotes", ["ticker"]),
        ("idx_market_quotes_quote_time", "market_quotes", ["quote_time"]),
        ("idx_market_quotes_ticker_time", "market_quotes", ["ticker", "quote_time"]),
        
        # Messages - for conversation history
        ("idx_messages_conversation_id", "messages", ["conversation_id"]),
        ("idx_messages_created_at", "messages", ["created_at"]),
        ("idx_messages_role", "messages", ["role"]),
        
        # Company filings - for SEC data
        ("idx_company_filings_ticker", "company_filings", ["ticker"]),
        ("idx_company_filings_form_type", "company_filings", ["form_type"]),
        ("idx_company_filings_filed_at", "company_filings", ["filed_at"]),
        
        # Ticker aliases - for name resolution
        ("idx_ticker_aliases_ticker", "ticker_aliases", ["ticker"]),
        ("idx_ticker_aliases_company_name", "ticker_aliases", ["company_name"]),
        
        # Portfolio holdings - for portfolio queries
        ("idx_portfolio_holdings_portfolio_id", "portfolio_holdings", ["portfolio_id"]),
        ("idx_portfolio_holdings_ticker", "portfolio_holdings", ["ticker"]),
        
        # Audit events - for system monitoring
        ("idx_audit_events_ticker", "audit_events", ["ticker"]),
        ("idx_audit_events_event_type", "audit_events", ["event_type"]),
        ("idx_audit_events_created_at", "audit_events", ["created_at"]),
    ]
    
    def __init__(self, database_path: Path):
        self.database_path = database_path
    
    def create_performance_indexes(self) -> Tuple[int, int]:
        """
        Create all performance indexes.
        
        Returns:
            Tuple of (created_count, skipped_count)
        """
        created = 0
        skipped = 0
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            for index_name, table_name, columns in self.PERFORMANCE_INDEXES:
                try:
                    # Check if index already exists
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                        (index_name,)
                    )
                    
                    if cursor.fetchone():
                        LOGGER.debug(f"Index {index_name} already exists, skipping")
                        skipped += 1
                        continue
                    
                    # Check if table exists
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table_name,)
                    )
                    
                    if not cursor.fetchone():
                        LOGGER.debug(f"Table {table_name} doesn't exist, skipping index {index_name}")
                        skipped += 1
                        continue
                    
                    # Create the index
                    columns_str = ", ".join(columns)
                    sql = f"CREATE INDEX {index_name} ON {table_name} ({columns_str})"
                    
                    LOGGER.info(f"Creating index: {index_name} on {table_name}({columns_str})")
                    cursor.execute(sql)
                    created += 1
                    
                except sqlite3.Error as e:
                    LOGGER.warning(f"Failed to create index {index_name}: {e}")
                    skipped += 1
        
        LOGGER.info(f"Database indexing complete: {created} created, {skipped} skipped")
        return created, skipped
    
    def analyze_query_performance(self) -> List[Tuple[str, str, float]]:
        """
        Analyze query performance with EXPLAIN QUERY PLAN.
        
        Returns:
            List of (query, plan, estimated_cost) tuples
        """
        test_queries = [
            # Most common query patterns
            "SELECT * FROM metric_snapshots WHERE ticker = 'AAPL'",
            "SELECT * FROM metric_snapshots WHERE ticker = 'AAPL' AND metric = 'revenue'",
            "SELECT * FROM financial_facts WHERE ticker = 'AAPL' AND fiscal_year = 2023",
            "SELECT * FROM market_quotes WHERE ticker = 'AAPL' ORDER BY quote_time DESC LIMIT 1",
            "SELECT * FROM messages WHERE conversation_id = 'test' ORDER BY created_at",
            "SELECT * FROM company_filings WHERE ticker = 'AAPL' AND form_type = '10-K'",
        ]
        
        results = []
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            for query in test_queries:
                try:
                    # Get query plan
                    cursor.execute(f"EXPLAIN QUERY PLAN {query}")
                    plan_rows = cursor.fetchall()
                    plan = " | ".join([row[3] for row in plan_rows])
                    
                    # Estimate cost (simplified - based on plan keywords)
                    cost = 1.0
                    if "SCAN" in plan.upper():
                        cost *= 10  # Table scan is expensive
                    if "INDEX" in plan.upper():
                        cost *= 0.1  # Index usage is fast
                    
                    results.append((query, plan, cost))
                    
                except sqlite3.Error as e:
                    LOGGER.warning(f"Failed to analyze query '{query}': {e}")
        
        return results
    
    def get_index_usage_stats(self) -> List[Tuple[str, int]]:
        """
        Get statistics on index usage.
        
        Returns:
            List of (index_name, usage_count) tuples
        """
        stats = []
        
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Get all indexes
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
                )
                indexes = [row[0] for row in cursor.fetchall()]
                
                for index_name in indexes:
                    # Note: SQLite doesn't provide direct index usage stats
                    # This is a placeholder for monitoring
                    stats.append((index_name, 0))
                    
            except sqlite3.Error as e:
                LOGGER.warning(f"Failed to get index stats: {e}")
        
        return stats
    
    def drop_unused_indexes(self, dry_run: bool = True) -> List[str]:
        """
        Drop indexes that are not being used (placeholder for future implementation).
        
        Args:
            dry_run: If True, only return what would be dropped
            
        Returns:
            List of index names that were/would be dropped
        """
        # Placeholder - would need query log analysis to determine unused indexes
        unused_indexes = []
        
        if not dry_run:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                for index_name in unused_indexes:
                    try:
                        cursor.execute(f"DROP INDEX {index_name}")
                        LOGGER.info(f"Dropped unused index: {index_name}")
                    except sqlite3.Error as e:
                        LOGGER.warning(f"Failed to drop index {index_name}: {e}")
        
        return unused_indexes


def optimize_database_indexes(database_path: Path) -> Tuple[int, int]:
    """
    Optimize database with performance indexes.
    
    Args:
        database_path: Path to SQLite database
        
    Returns:
        Tuple of (created_count, skipped_count)
    """
    optimizer = DatabaseIndexOptimizer(database_path)
    return optimizer.create_performance_indexes()


def analyze_database_performance(database_path: Path) -> None:
    """
    Analyze and report database query performance.
    
    Args:
        database_path: Path to SQLite database
    """
    optimizer = DatabaseIndexOptimizer(database_path)
    
    print("🔍 Database Performance Analysis")
    print("=" * 40)
    
    # Analyze query performance
    query_results = optimizer.analyze_query_performance()
    print(f"\n📊 Query Performance Analysis ({len(query_results)} queries):")
    
    for query, plan, cost in query_results:
        cost_rating = "🚀 FAST" if cost < 1.0 else "⚠️ SLOW" if cost > 5.0 else "✅ OK"
        print(f"\n{cost_rating} (cost: {cost:.1f})")
        print(f"Query: {query[:60]}...")
        print(f"Plan:  {plan}")
    
    # Index usage stats
    index_stats = optimizer.get_index_usage_stats()
    print(f"\n📈 Index Statistics ({len(index_stats)} indexes):")
    for index_name, usage in index_stats:
        print(f"  {index_name}: {usage} uses")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    if len(sys.argv) != 2:
        print("Usage: python database_indexes.py <database_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)
    
    # Create indexes
    created, skipped = optimize_database_indexes(db_path)
    print(f"✅ Created {created} indexes, skipped {skipped}")
    
    # Analyze performance
    analyze_database_performance(db_path)
