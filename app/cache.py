"""
SQLite-backed cache for PyPI and OSV responses.

Implements R2.5: caching of metadata and OSV responses with TTL-based freshness.
Provides thread-safe access to cached data with automatic schema initialization
and statistics tracking.

Design principles:
- TTL-based freshness: cached entries older than the TTL are re-fetched
- Never cache failures as success: errors cached with short TTL or as durable Unknown
- Render ephemeral storage: cache improves session latency but is not relied on for persistence
- Thread-safe: all database operations guarded by a threading.Lock
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.models import CacheStats


# Default cache location
DEFAULT_CACHE_DIR = Path.home() / ".postmortem"
DEFAULT_CACHE_DB = DEFAULT_CACHE_DIR / "cache.db"

# Default TTL: 24 hours
DEFAULT_TTL_SECONDS = 86400

# Short TTL for transient failures (e.g., timeout): 1 hour
SHORT_TTL_SECONDS = 3600


class Cache:
    """
    SQLite-backed cache for PyPI metadata and OSV responses.

    Thread-safe, with automatic schema creation and TTL-based expiration.
    Tracks cache statistics (hits/misses) for monitoring.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the cache with an optional database path.

        Args:
            db_path: Path to the SQLite database file. If None, uses ~/.postmortem/cache.db.
        """
        if db_path is None:
            db_path = str(DEFAULT_CACHE_DB)

        self.db_path = db_path
        self._lock = threading.Lock()
        self._stats = {
            "pypi_hits": 0,
            "pypi_misses": 0,
            "osv_query_hits": 0,
            "osv_query_misses": 0,
            "osv_details_hits": 0,
            "osv_details_misses": 0,
        }

        # Initialize database schema
        self.init_cache()

    def init_cache(self) -> None:
        """
        Initialize the SQLite cache database.

        Creates the database file and tables if they don't exist.
        Thread-safe and idempotent.
        """
        with self._lock:
            # Ensure parent directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # Create pypi_cache table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pypi_cache (
                        package_name TEXT PRIMARY KEY,
                        response_json TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        ttl_seconds INTEGER NOT NULL
                    )
                    """
                )

                # Create osv_cache table (batch query results)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS osv_cache (
                        query_hash TEXT PRIMARY KEY,
                        response_json TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        ttl_seconds INTEGER NOT NULL
                    )
                    """
                )

                # Create osv_details_cache table (per-id detail records)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS osv_details_cache (
                        osv_id TEXT PRIMARY KEY,
                        response_json TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        ttl_seconds INTEGER NOT NULL
                    )
                    """
                )

                conn.commit()
            finally:
                conn.close()

    def get_pypi_json(self, package_name: str) -> Optional[dict]:
        """
        Fetch PyPI metadata from cache if fresh.

        Args:
            package_name: Canonical package name.

        Returns:
            Cached response dict if fresh and present, else None.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT response_json, fetched_at, ttl_seconds FROM pypi_cache WHERE package_name = ?",
                    (package_name,),
                )
                row = cursor.fetchone()

                if row is None:
                    self._stats["pypi_misses"] += 1
                    return None

                response_json, fetched_at_str, ttl_seconds = row
                fetched_at = datetime.fromisoformat(fetched_at_str)

                # Check if entry is still fresh
                if datetime.now() - fetched_at < timedelta(seconds=ttl_seconds):
                    self._stats["pypi_hits"] += 1
                    return json.loads(response_json)
                else:
                    # Entry expired; delete it
                    cursor.execute("DELETE FROM pypi_cache WHERE package_name = ?", (package_name,))
                    conn.commit()
                    self._stats["pypi_misses"] += 1
                    return None

            finally:
                conn.close()

    def set_pypi_json(
        self, package_name: str, response: dict, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> None:
        """
        Store PyPI metadata in cache.

        Args:
            package_name: Canonical package name.
            response: Response dict to cache.
            ttl_seconds: Time-to-live in seconds (default 24h).
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                response_json = json.dumps(response)
                fetched_at = datetime.now()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO pypi_cache
                    (package_name, response_json, fetched_at, ttl_seconds)
                    VALUES (?, ?, ?, ?)
                    """,
                    (package_name, response_json, fetched_at.isoformat(), ttl_seconds),
                )

                conn.commit()
            finally:
                conn.close()

    def get_osv_query(self, query_hash: str) -> Optional[dict]:
        """
        Fetch OSV batch query result from cache if fresh.

        Args:
            query_hash: Hash of the query request (e.g., SHA-256 of JSON).

        Returns:
            Cached response dict if fresh and present, else None.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT response_json, fetched_at, ttl_seconds FROM osv_cache WHERE query_hash = ?",
                    (query_hash,),
                )
                row = cursor.fetchone()

                if row is None:
                    self._stats["osv_query_misses"] += 1
                    return None

                response_json, fetched_at_str, ttl_seconds = row
                fetched_at = datetime.fromisoformat(fetched_at_str)

                # Check if entry is still fresh
                if datetime.now() - fetched_at < timedelta(seconds=ttl_seconds):
                    self._stats["osv_query_hits"] += 1
                    return json.loads(response_json)
                else:
                    # Entry expired; delete it
                    cursor.execute("DELETE FROM osv_cache WHERE query_hash = ?", (query_hash,))
                    conn.commit()
                    self._stats["osv_query_misses"] += 1
                    return None

            finally:
                conn.close()

    def set_osv_query(
        self, query_hash: str, response: dict, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> None:
        """
        Store OSV batch query result in cache.

        Args:
            query_hash: Hash of the query request.
            response: Response dict to cache.
            ttl_seconds: Time-to-live in seconds (default 24h).
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                response_json = json.dumps(response)
                fetched_at = datetime.now()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO osv_cache
                    (query_hash, response_json, fetched_at, ttl_seconds)
                    VALUES (?, ?, ?, ?)
                    """,
                    (query_hash, response_json, fetched_at.isoformat(), ttl_seconds),
                )

                conn.commit()
            finally:
                conn.close()

    def get_osv_details(self, osv_id: str) -> Optional[dict]:
        """
        Fetch OSV detail record from cache if fresh.

        Args:
            osv_id: OSV record ID (e.g., 'PYSEC-2024-123').

        Returns:
            Cached response dict if fresh and present, else None.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT response_json, fetched_at, ttl_seconds FROM osv_details_cache WHERE osv_id = ?",
                    (osv_id,),
                )
                row = cursor.fetchone()

                if row is None:
                    self._stats["osv_details_misses"] += 1
                    return None

                response_json, fetched_at_str, ttl_seconds = row
                fetched_at = datetime.fromisoformat(fetched_at_str)

                # Check if entry is still fresh
                if datetime.now() - fetched_at < timedelta(seconds=ttl_seconds):
                    self._stats["osv_details_hits"] += 1
                    return json.loads(response_json)
                else:
                    # Entry expired; delete it
                    cursor.execute("DELETE FROM osv_details_cache WHERE osv_id = ?", (osv_id,))
                    conn.commit()
                    self._stats["osv_details_misses"] += 1
                    return None

            finally:
                conn.close()

    def set_osv_details(
        self, osv_id: str, response: dict, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> None:
        """
        Store OSV detail record in cache.

        Args:
            osv_id: OSV record ID.
            response: Response dict to cache.
            ttl_seconds: Time-to-live in seconds (default 24h).
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                response_json = json.dumps(response)
                fetched_at = datetime.now()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO osv_details_cache
                    (osv_id, response_json, fetched_at, ttl_seconds)
                    VALUES (?, ?, ?, ?)
                    """,
                    (osv_id, response_json, fetched_at.isoformat(), ttl_seconds),
                )

                conn.commit()
            finally:
                conn.close()

    def clear_cache(self) -> None:
        """
        Delete all cached data.

        Used for testing and cache reset. Thread-safe and idempotent.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute("DELETE FROM pypi_cache")
                cursor.execute("DELETE FROM osv_cache")
                cursor.execute("DELETE FROM osv_details_cache")
                conn.commit()
            finally:
                conn.close()

    def cache_stats(self) -> CacheStats:
        """
        Return cache statistics.

        Returns:
            CacheStats object with hit/miss counts and cache size.
        """
        with self._lock:
            # Get cache file size
            cache_size_bytes = 0
            try:
                cache_size_bytes = Path(self.db_path).stat().st_size
            except FileNotFoundError:
                pass

            return CacheStats(
                pypi_hits=self._stats["pypi_hits"],
                pypi_misses=self._stats["pypi_misses"],
                osv_query_hits=self._stats["osv_query_hits"],
                osv_query_misses=self._stats["osv_query_misses"],
                osv_details_hits=self._stats["osv_details_hits"],
                osv_details_misses=self._stats["osv_details_misses"],
                cache_size_bytes=cache_size_bytes,
            )


# Singleton cache instance (created on demand)
_cache_instance: Optional[Cache] = None
_cache_lock = threading.Lock()


def get_cache(db_path: Optional[str] = None) -> Cache:
    """
    Get or create the global cache instance.

    Args:
        db_path: Path to the SQLite database file. If None, uses ~/.postmortem/cache.db.
                 Only used on first call; ignored on subsequent calls.

    Returns:
        The global Cache instance.
    """
    global _cache_instance

    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = Cache(db_path)

    return _cache_instance
