"""High-performance database connection pooling for SQLite."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, Optional, Iterator

LOGGER = logging.getLogger(__name__)


class ConnectionPool:
    """Thread-safe SQLite connection pool for high performance."""
    
    def __init__(
        self, 
        database_path: Path, 
        pool_size: int = 10,
        max_overflow: int = 5,
        timeout: float = 30.0,
        recycle_time: float = 3600.0  # 1 hour
    ):
        self.database_path = database_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self.recycle_time = recycle_time
        
        # Connection pool
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._overflow_connections: Dict[int, sqlite3.Connection] = {}
        self._connection_times: Dict[int, float] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        self._overflow_count = 0
        
        # Statistics
        self._stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "connections_recycled": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "overflow_used": 0,
        }
        
        # Initialize pool
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool with base connections."""
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                self._pool.put(conn, block=False)
            except Exception as e:
                LOGGER.warning(f"Failed to initialize connection: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new optimized SQLite connection."""
        conn = sqlite3.connect(
            str(self.database_path),
            timeout=self.timeout,
            check_same_thread=False,  # Allow sharing between threads
            isolation_level=None,     # Autocommit mode for better performance
        )
        
        # Optimize SQLite settings for performance
        conn.execute("PRAGMA journal_mode=WAL")          # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")        # Balanced durability/speed
        conn.execute("PRAGMA cache_size=10000")          # 10MB cache
        conn.execute("PRAGMA temp_store=MEMORY")         # Temp tables in memory
        conn.execute("PRAGMA mmap_size=268435456")       # 256MB memory mapping
        conn.execute("PRAGMA optimize")                  # Auto-optimize
        
        # Row factory for easier data access
        conn.row_factory = sqlite3.Row
        
        self._stats["connections_created"] += 1
        return conn
    
    def _is_connection_stale(self, conn_id: int) -> bool:
        """Check if a connection should be recycled."""
        if conn_id not in self._connection_times:
            return False
        
        age = time.time() - self._connection_times[conn_id]
        return age > self.recycle_time
    
    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """
        Get a connection from the pool.
        
        Yields:
            SQLite connection from the pool
        """
        conn = None
        is_overflow = False
        conn_id = None
        
        try:
            # Try to get from pool first
            try:
                conn = self._pool.get(block=False)
                conn_id = id(conn)
                
                # Check if connection is stale
                if self._is_connection_stale(conn_id):
                    conn.close()
                    conn = self._create_connection()
                    conn_id = id(conn)
                    self._stats["connections_recycled"] += 1
                else:
                    self._stats["connections_reused"] += 1
                
                self._stats["pool_hits"] += 1
                
            except Empty:
                # Pool is empty, try overflow
                with self._lock:
                    if self._overflow_count < self.max_overflow:
                        conn = self._create_connection()
                        conn_id = id(conn)
                        self._overflow_connections[conn_id] = conn
                        self._overflow_count += 1
                        is_overflow = True
                        self._stats["overflow_used"] += 1
                        self._stats["pool_misses"] += 1
                    else:
                        # Wait for a connection to become available
                        conn = self._pool.get(timeout=self.timeout)
                        conn_id = id(conn)
                        self._stats["pool_hits"] += 1
            
            # Track connection time
            self._connection_times[conn_id] = time.time()
            
            yield conn
            
        except Exception as e:
            LOGGER.error(f"Connection pool error: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
            
        finally:
            # Return connection to pool or clean up overflow
            if conn:
                try:
                    if is_overflow:
                        # Close overflow connection
                        with self._lock:
                            self._overflow_connections.pop(conn_id, None)
                            self._overflow_count -= 1
                        conn.close()
                    else:
                        # Return to pool
                        try:
                            self._pool.put(conn, block=False)
                        except:
                            # Pool is full, close connection
                            conn.close()
                except Exception as e:
                    LOGGER.warning(f"Error returning connection to pool: {e}")
                finally:
                    self._connection_times.pop(conn_id, None)
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        # Close pool connections
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
            except Empty:
                break
            except Exception as e:
                LOGGER.warning(f"Error closing pool connection: {e}")
        
        # Close overflow connections
        with self._lock:
            for conn in self._overflow_connections.values():
                try:
                    conn.close()
                except Exception as e:
                    LOGGER.warning(f"Error closing overflow connection: {e}")
            self._overflow_connections.clear()
            self._overflow_count = 0
        
        self._connection_times.clear()
    
    def get_stats(self) -> Dict[str, any]:
        """Get connection pool statistics."""
        with self._lock:
            return {
                **self._stats,
                "pool_size": self.pool_size,
                "current_pool_size": self._pool.qsize(),
                "overflow_connections": self._overflow_count,
                "max_overflow": self.max_overflow,
                "hit_rate": self._stats["pool_hits"] / max(
                    self._stats["pool_hits"] + self._stats["pool_misses"], 1
                ),
            }
    
    def health_check(self) -> bool:
        """Check if the connection pool is healthy."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            LOGGER.error(f"Connection pool health check failed: {e}")
            return False


# Global connection pools (one per database)
_connection_pools: Dict[str, ConnectionPool] = {}
_pool_lock = threading.RLock()


def get_connection_pool(database_path: Path, **kwargs) -> ConnectionPool:
    """
    Get or create a connection pool for a database.
    
    Args:
        database_path: Path to the SQLite database
        **kwargs: Additional arguments for ConnectionPool
        
    Returns:
        ConnectionPool instance
    """
    db_key = str(database_path.absolute())
    
    with _pool_lock:
        if db_key not in _connection_pools:
            _connection_pools[db_key] = ConnectionPool(database_path, **kwargs)
            LOGGER.info(f"Created connection pool for {database_path}")
        
        return _connection_pools[db_key]


@contextmanager
def pooled_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    """
    Get a pooled database connection.
    
    Args:
        database_path: Path to the SQLite database
        
    Yields:
        SQLite connection from the pool
    """
    pool = get_connection_pool(database_path)
    with pool.get_connection() as conn:
        yield conn


def close_all_pools() -> None:
    """Close all connection pools."""
    with _pool_lock:
        for pool in _connection_pools.values():
            pool.close_all()
        _connection_pools.clear()
    LOGGER.info("All connection pools closed")


def get_all_pool_stats() -> Dict[str, Dict[str, any]]:
    """Get statistics for all connection pools."""
    with _pool_lock:
        return {
            db_path: pool.get_stats()
            for db_path, pool in _connection_pools.items()
        }
