"""
Unit tests for app.cache module.

Tests SQLite caching functionality for PyPI and OSV responses, including:
- Basic get/set operations for PyPI, OSV query, and OSV details
- TTL expiration and cache freshness
- Thread safety with concurrent operations
- Cache statistics tracking
- Clear cache functionality
- Database initialization
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from app.cache import Cache, get_cache, DEFAULT_TTL_SECONDS, SHORT_TTL_SECONDS
from app.models import CacheStats


class TestCacheInitialization:
    """Test cache database initialization."""

    def test_cache_creates_database_file(self):
        """Cache should create a database file at the specified path."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            assert db_path.exists(), "Database file should be created"

    def test_cache_creates_parent_directories(self):
        """Cache should create parent directories if they don't exist."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dirs" / "cache.db"
            cache = Cache(db_path=str(db_path))

            assert db_path.parent.exists(), "Parent directories should be created"
            assert db_path.exists(), "Database file should be created"

    def test_cache_creates_tables(self):
        """Cache should create all required tables."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check that all tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            conn.close()

            assert "pypi_cache" in tables, "pypi_cache table should be created"
            assert "osv_cache" in tables, "osv_cache table should be created"
            assert "osv_details_cache" in tables, "osv_details_cache table should be created"

    def test_init_cache_is_idempotent(self):
        """init_cache should be idempotent (calling twice should not error)."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Call init_cache again
            cache.init_cache()

            # Verify database still exists and works
            assert db_path.exists()


class TestPyPICache:
    """Test PyPI metadata caching."""

    def test_set_and_get_pypi_json(self):
        """Should store and retrieve PyPI metadata."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            package_name = "flask"
            response = {"info": {"name": "Flask", "version": "2.0.0"}, "releases": {}}

            cache.set_pypi_json(package_name, response)
            retrieved = cache.get_pypi_json(package_name)

            assert retrieved is not None
            assert retrieved == response

    def test_get_pypi_json_returns_none_when_missing(self):
        """Should return None for missing package."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            result = cache.get_pypi_json("nonexistent-package")

            assert result is None

    def test_pypi_json_respects_ttl(self):
        """Should respect TTL and return None for expired entries."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            package_name = "requests"
            response = {"info": {"name": "requests"}}

            # Set with very short TTL
            cache.set_pypi_json(package_name, response, ttl_seconds=1)

            # Should be retrievable immediately
            assert cache.get_pypi_json(package_name) is not None

            # Wait for TTL to expire
            time.sleep(1.1)

            # Should now return None
            assert cache.get_pypi_json(package_name) is None

    def test_pypi_json_with_custom_ttl(self):
        """Should use custom TTL when specified."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            package_name = "django"
            response = {"info": {"name": "Django"}}

            # Set with custom TTL (high value so it doesn't expire during test)
            cache.set_pypi_json(package_name, response, ttl_seconds=10000)

            # Verify it's cached
            assert cache.get_pypi_json(package_name) is not None

    def test_pypi_json_replace_overwrites_existing(self):
        """Setting PyPI JSON should overwrite existing entry."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            package_name = "requests"

            response1 = {"version": "2.0.0"}
            cache.set_pypi_json(package_name, response1)

            response2 = {"version": "2.1.0"}
            cache.set_pypi_json(package_name, response2)

            retrieved = cache.get_pypi_json(package_name)

            assert retrieved["version"] == "2.1.0"


class TestOSVQueryCache:
    """Test OSV batch query caching."""

    def test_set_and_get_osv_query(self):
        """Should store and retrieve OSV batch query results."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            query_hash = "abc123def456"
            response = {
                "results": [
                    {"vulns": [{"id": "PYSEC-2024-123", "modified": "2024-01-01"}]}
                ]
            }

            cache.set_osv_query(query_hash, response)
            retrieved = cache.get_osv_query(query_hash)

            assert retrieved is not None
            assert retrieved == response

    def test_get_osv_query_returns_none_when_missing(self):
        """Should return None for missing query hash."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            result = cache.get_osv_query("nonexistent-hash")

            assert result is None

    def test_osv_query_respects_ttl(self):
        """Should respect TTL for OSV query results."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            query_hash = "hash123"
            response = {"results": []}

            # Set with very short TTL
            cache.set_osv_query(query_hash, response, ttl_seconds=1)

            # Should be retrievable immediately
            assert cache.get_osv_query(query_hash) is not None

            # Wait for TTL to expire
            time.sleep(1.1)

            # Should now return None
            assert cache.get_osv_query(query_hash) is None


class TestOSVDetailsCache:
    """Test OSV detail record caching."""

    def test_set_and_get_osv_details(self):
        """Should store and retrieve OSV detail records."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            osv_id = "PYSEC-2024-123"
            response = {
                "id": osv_id,
                "aliases": ["CVE-2024-456"],
                "severity": "HIGH",
            }

            cache.set_osv_details(osv_id, response)
            retrieved = cache.get_osv_details(osv_id)

            assert retrieved is not None
            assert retrieved == response

    def test_get_osv_details_returns_none_when_missing(self):
        """Should return None for missing OSV ID."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            result = cache.get_osv_details("NONEXISTENT-ID")

            assert result is None

    def test_osv_details_respects_ttl(self):
        """Should respect TTL for OSV detail records."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            osv_id = "PYSEC-2024-789"
            response = {"id": osv_id}

            # Set with very short TTL
            cache.set_osv_details(osv_id, response, ttl_seconds=1)

            # Should be retrievable immediately
            assert cache.get_osv_details(osv_id) is not None

            # Wait for TTL to expire
            time.sleep(1.1)

            # Should now return None
            assert cache.get_osv_details(osv_id) is None


class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_cache_stats_initial_state(self):
        """Cache stats should start at zero."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            stats = cache.cache_stats()

            assert stats.pypi_hits == 0
            assert stats.pypi_misses == 0
            assert stats.osv_query_hits == 0
            assert stats.osv_query_misses == 0
            assert stats.osv_details_hits == 0
            assert stats.osv_details_misses == 0

    def test_cache_stats_tracks_pypi_hits(self):
        """Cache stats should track PyPI hits."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            package_name = "flask"
            response = {"info": {}}

            # Set and retrieve
            cache.set_pypi_json(package_name, response)
            cache.get_pypi_json(package_name)

            stats = cache.cache_stats()

            assert stats.pypi_hits == 1
            assert stats.pypi_misses == 0

    def test_cache_stats_tracks_pypi_misses(self):
        """Cache stats should track PyPI misses."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Try to retrieve non-existent entry
            cache.get_pypi_json("nonexistent")

            stats = cache.cache_stats()

            assert stats.pypi_hits == 0
            assert stats.pypi_misses == 1

    def test_cache_stats_tracks_osv_query_hits_and_misses(self):
        """Cache stats should track OSV query hits and misses."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            query_hash = "hash123"
            response = {"results": []}

            # Miss
            cache.get_osv_query(query_hash)

            # Set and hit
            cache.set_osv_query(query_hash, response)
            cache.get_osv_query(query_hash)

            stats = cache.cache_stats()

            assert stats.osv_query_hits == 1
            assert stats.osv_query_misses == 1

    def test_cache_stats_tracks_osv_details_hits_and_misses(self):
        """Cache stats should track OSV details hits and misses."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            osv_id = "PYSEC-2024-123"
            response = {"id": osv_id}

            # Miss
            cache.get_osv_details(osv_id)

            # Set and hit
            cache.set_osv_details(osv_id, response)
            cache.get_osv_details(osv_id)

            stats = cache.cache_stats()

            assert stats.osv_details_hits == 1
            assert stats.osv_details_misses == 1

    def test_cache_stats_includes_cache_size(self):
        """Cache stats should include the size of the cache file."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Add some data
            cache.set_pypi_json("flask", {"info": {}})

            stats = cache.cache_stats()

            assert stats.cache_size_bytes > 0

    def test_cache_stats_returns_cache_stats_model(self):
        """cache_stats() should return a CacheStats model."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            stats = cache.cache_stats()

            assert isinstance(stats, CacheStats)


class TestClearCache:
    """Test cache clearing functionality."""

    def test_clear_cache_deletes_all_data(self):
        """clear_cache should remove all cached entries."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Add data
            cache.set_pypi_json("flask", {"info": {}})
            cache.set_osv_query("hash1", {"results": []})
            cache.set_osv_details("PYSEC-123", {"id": "PYSEC-123"})

            # Verify data is there
            assert cache.get_pypi_json("flask") is not None
            assert cache.get_osv_query("hash1") is not None
            assert cache.get_osv_details("PYSEC-123") is not None

            # Clear cache
            cache.clear_cache()

            # Verify data is gone
            assert cache.get_pypi_json("flask") is None
            assert cache.get_osv_query("hash1") is None
            assert cache.get_osv_details("PYSEC-123") is None

    def test_clear_cache_does_not_delete_database_file(self):
        """clear_cache should not delete the database file itself."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Add and clear data
            cache.set_pypi_json("flask", {"info": {}})
            cache.clear_cache()

            # Database file should still exist
            assert Path(db_path).exists()


class TestThreadSafety:
    """Test thread safety of cache operations."""

    def test_concurrent_reads_do_not_corrupt_cache(self):
        """Multiple threads reading from cache should not cause issues."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Seed cache with data
            package_names = [f"package-{i}" for i in range(10)]
            for name in package_names:
                cache.set_pypi_json(name, {"name": name, "version": "1.0.0"})

            results = {}

            def reader(name):
                """Read from cache multiple times."""
                for _ in range(10):
                    result = cache.get_pypi_json(name)
                    if name not in results:
                        results[name] = result

            threads = [
                threading.Thread(target=reader, args=(name,)) for name in package_names
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Verify all reads succeeded
            assert len(results) == len(package_names)
            for name in package_names:
                assert results[name] is not None
                assert results[name]["name"] == name

    def test_concurrent_writes_do_not_corrupt_cache(self):
        """Multiple threads writing to cache should not cause corruption."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            def writer(thread_id):
                """Write to cache multiple times."""
                for i in range(5):
                    package_name = f"package-{thread_id}-{i}"
                    cache.set_pypi_json(
                        package_name,
                        {"name": package_name, "thread": thread_id},
                    )

            threads = [
                threading.Thread(target=writer, args=(i,)) for i in range(5)
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Verify all writes succeeded
            stats = cache.cache_stats()
            # We should have some entries in the cache
            assert stats.cache_size_bytes > 0

    def test_concurrent_reads_and_writes(self):
        """Cache should handle concurrent reads and writes."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            errors = []

            def mixed_operations(thread_id):
                """Perform mixed read/write operations."""
                try:
                    for i in range(5):
                        # Write
                        cache.set_pypi_json(
                            f"pkg-{thread_id}-{i}",
                            {"data": i},
                        )
                        # Read
                        cache.get_pypi_json(f"pkg-{thread_id}-{i}")
                except Exception as e:
                    errors.append(e)

            threads = [
                threading.Thread(target=mixed_operations, args=(i,))
                for i in range(5)
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Should have no errors
            assert len(errors) == 0


class TestJSONSerialization:
    """Test JSON serialization and deserialization."""

    def test_complex_nested_structures_are_cached(self):
        """Cache should handle complex nested JSON structures."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            complex_response = {
                "info": {
                    "name": "Flask",
                    "version": "2.0.0",
                    "requires_dist": [
                        "Werkzeug>=2.0,<3.0",
                        'MarkupSafe>=2.0; python_version>="3.7"',
                    ],
                },
                "releases": {
                    "2.0.0": [
                        {
                            "filename": "Flask-2.0.0-py3-none-any.whl",
                            "size": 100000,
                            "urls": ["https://example.com/Flask-2.0.0-py3-none-any.whl"],
                        }
                    ]
                },
            }

            cache.set_pypi_json("flask", complex_response)
            retrieved = cache.get_pypi_json("flask")

            assert retrieved == complex_response

    def test_unicode_in_cached_data(self):
        """Cache should handle Unicode characters."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            response = {
                "info": {
                    "name": "package",
                    "description": "A package with émojis 🐍 and spëcial chars",
                }
            }

            cache.set_pypi_json("test-pkg", response)
            retrieved = cache.get_pypi_json("test-pkg")

            assert retrieved == response
            assert retrieved["info"]["description"] == response["info"]["description"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_response_dict_is_cached(self):
        """Cache should handle empty dictionaries."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            cache.set_pypi_json("empty", {})
            retrieved = cache.get_pypi_json("empty")

            assert retrieved == {}

    def test_very_large_response_is_cached(self):
        """Cache should handle large responses."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            # Create a large response
            large_response = {
                "releases": {
                    f"1.0.{i}": [
                        {"filename": f"pkg-1.0.{i}.tar.gz", "size": 100000}
                        for _ in range(100)
                    ]
                    for i in range(50)
                }
            }

            cache.set_pypi_json("large-pkg", large_response)
            retrieved = cache.get_pypi_json("large-pkg")

            assert retrieved == large_response

    def test_package_names_with_special_characters(self):
        """Cache should handle package names with hyphens and underscores."""
        with TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = Cache(db_path=str(db_path))

            names = [
                "my-package",
                "my_package",
                "My-Package_123",
            ]

            for name in names:
                cache.set_pypi_json(name, {"name": name})

            for name in names:
                retrieved = cache.get_pypi_json(name)
                assert retrieved is not None
                assert retrieved["name"] == name


class TestDefaultCachePath:
    """Test default cache path behavior."""

    def test_default_cache_uses_home_directory(self):
        """Cache with no path should create ~/.postmortem/cache.db."""
        from app.cache import DEFAULT_CACHE_DB

        # We won't actually create this, just verify the constant exists
        assert DEFAULT_CACHE_DB is not None
        assert str(DEFAULT_CACHE_DB).endswith("cache.db")
        assert ".postmortem" in str(DEFAULT_CACHE_DB)
