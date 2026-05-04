"""
SQLite Cache untuk menyimpan hasil pencarian GetContact.
Gratis, tanpa server, file .db disimpan di folder project.
"""

import sqlite3
import json
import logging
import time
from pathlib import Path
from dataclasses import asdict

from bot.services.datapublik import MultiSourceResponse, SourceResult

logger = logging.getLogger(__name__)

# Default cache expiry: 7 hari (dalam detik)
DEFAULT_CACHE_TTL = 7 * 24 * 60 * 60

# Database file path
DB_PATH = Path(__file__).parent.parent.parent / "cache.db"


class SearchCache:
    """SQLite-based cache for OSINT search results."""

    def __init__(self, db_path: Path = DB_PATH, ttl: int = DEFAULT_CACHE_TTL):
        self.db_path = db_path
        self.ttl = ttl
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database and create tables if needed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store the full raw JSON of the multisource response (Global/Shared)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS search_cache_v2 (
                        phone_number TEXT PRIMARY KEY,
                        raw_data TEXT,
                        created_at REAL,
                        hit_count INTEGER DEFAULT 1
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS search_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone_number TEXT,
                        user_id INTEGER,
                        username TEXT,
                        searched_at REAL,
                        from_cache INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
            logger.info(f"✅ Cache database initialized (Global Mode): {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize cache DB: {e}")

    def get(self, phone_number: str) -> dict | None:
        """
        Get cached raw data for a phone number (Global).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT raw_data, created_at "
                    "FROM search_cache_v2 WHERE phone_number = ?",
                    (phone_number,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                raw_data_json, created_at = row

                # Check if cache has expired
                if time.time() - created_at > self.ttl:
                    self._delete(phone_number)
                    logger.info(f"Cache expired for {phone_number}")
                    return None

                # Increment hit count
                conn.execute(
                    "UPDATE search_cache_v2 SET hit_count = hit_count + 1 "
                    "WHERE phone_number = ?",
                    (phone_number,),
                )
                conn.commit()

                logger.info(f"Cache HIT for {phone_number}")
                return json.loads(raw_data_json)

        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def put(self, phone_number: str, data: dict) -> None:
        """Save a raw result dictionary to global cache."""
        try:
            raw_data_json = json.dumps(data, ensure_ascii=False)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO search_cache_v2 "
                    "(phone_number, raw_data, created_at, hit_count) "
                    "VALUES (?, ?, ?, 1)",
                    (
                        phone_number,
                        raw_data_json,
                        time.time(),
                    ),
                )
                conn.commit()
            logger.info(f"Cache STORED for {phone_number}")
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def log_search(
        self,
        phone_number: str,
        user_id: int,
        username: str | None,
        from_cache: bool,
    ) -> None:
        """Log a search for analytics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO search_log "
                    "(phone_number, user_id, username, searched_at, from_cache) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (phone_number, user_id, username, time.time(), int(from_cache)),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Search log error: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cached_count = conn.execute(
                    "SELECT COUNT(*) FROM search_cache_v2"
                ).fetchone()[0]
                total_searches = conn.execute(
                    "SELECT COUNT(*) FROM search_log"
                ).fetchone()[0]
                cache_hits = conn.execute(
                    "SELECT COUNT(*) FROM search_log WHERE from_cache = 1"
                ).fetchone()[0]

                return {
                    "cached_numbers": cached_count,
                    "total_searches": total_searches,
                    "cache_hits": cache_hits,
                    "cache_miss": total_searches - cache_hits,
                }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {}

    def _delete(self, phone_number: str) -> None:
        """Delete a cached entry."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM search_cache_v2 WHERE phone_number = ?",
                    (phone_number,),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
