"""
src/cache/redis_client.py
==========================
Redis 7 client for StatIQ data ingestion layer.

Two jobs:
  Job 1 — NL-SQL cache: stores LLM-generated SQL so Member 2 (API layer)
           doesn't re-call the LLM for repeated questions.
           Key: nlsql:{sha256(question+survey_id)}   TTL: 24h

  Job 2 — Rate limiting: sliding-window counter per API key.
           Key: rate:{api_key_hash}   TTL: 60s   Type: sorted set
"""

import os, json, hashlib, logging, time
from typing import Optional, Tuple
import redis

log = logging.getLogger("statiq.cache")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB   = int(os.getenv("REDIS_DB",  "0"))

NL_SQL_TTL       = 86_400   # 24h  — NL-SQL translation cache
QUERY_RESULT_TTL = 900      # 15min — full query result cache
RATE_WINDOW      = 60       # 60s  — rate-limit sliding window


class StatIQCache:

    def __init__(self):
        pool = redis.ConnectionPool(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=True, max_connections=20,
        )
        self.r = redis.Redis(connection_pool=pool)
        self.r.ping()
        log.info(f"[Redis] Connected: {REDIS_HOST}:{REDIS_PORT}")

    def _hash(self, *parts: str) -> str:
        return hashlib.sha256("|".join(str(p).strip().lower() for p in parts).encode()).hexdigest()

    # ── NL-SQL cache ─────────────────────────────────────────

    def get_nl_sql(self, question: str, survey_id: str) -> Optional[str]:
        key    = f"nlsql:{self._hash(question, survey_id)}"
        cached = self.r.get(key)
        if cached:
            log.debug(f"[Cache] NL-SQL HIT")
        return cached

    def set_nl_sql(self, question: str, survey_id: str, sql: str, ttl: int = NL_SQL_TTL):
        key = f"nlsql:{self._hash(question, survey_id)}"
        self.r.setex(key, ttl, sql)

    def get_query_result(self, sql: str, tier: str) -> Optional[dict]:
        key = f"result:{self._hash(sql, tier)}"
        raw = self.r.get(key)
        return json.loads(raw) if raw else None

    def set_query_result(self, sql: str, tier: str, result: dict, ttl: int = QUERY_RESULT_TTL):
        key = f"result:{self._hash(sql, tier)}"
        self.r.setex(key, ttl, json.dumps(result, default=str))

        # Track key in survey set for invalidation
        sql_lower = sql.lower()
        if "plfs" in sql_lower:
            self.r.sadd("survey_keys:plfs", key)
            self.r.expire("survey_keys:plfs", ttl)
        if "hces" in sql_lower:
            self.r.sadd("survey_keys:hces", key)
            self.r.sadd("survey_keys:hces_health", key)
            self.r.expire("survey_keys:hces", ttl)
            self.r.expire("survey_keys:hces_health", ttl)

    def invalidate_survey(self, survey_id: str):
        """Clear all cached results after a new ingestion run."""
        set_key = f"survey_keys:{survey_id.lower()}"
        keys = self.r.smembers(set_key)
        if keys:
            self.r.delete(*keys)
            self.r.delete(set_key)
            log.info(f"[Cache] Invalidated {len(keys)} results for: {survey_id}")

        # Fallback to scan_iter just in case
        scan_keys = list(self.r.scan_iter(match=f"result:*{survey_id}*"))
        if scan_keys:
            self.r.delete(*scan_keys)
            log.info(f"[Cache] Invalidated {len(scan_keys)} scanned results for: {survey_id}")

    # ── Rate limiting (sliding window) ───────────────────────

    def check_rate_limit(self, api_key_hash: str, limit_per_minute: int = 100) -> Tuple[bool, int]:
        key  = f"rate:{api_key_hash}"
        now  = time.time()
        pipe = self.r.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - RATE_WINDOW)
        pipe.zcard(key)
        pipe.expire(key, RATE_WINDOW)
        results   = pipe.execute()
        count     = results[2]
        allowed   = count <= limit_per_minute
        remaining = max(0, limit_per_minute - count)
        if not allowed:
            log.warning(f"[Cache] Rate limit exceeded: {api_key_hash[:16]}...")
        return allowed, remaining

    # ── Monthly quota ────────────────────────────────────────

    def increment_monthly_calls(self, api_key_hash: str) -> int:
        import datetime
        now = datetime.datetime.utcnow()
        key = f"quota:{api_key_hash}:{now.year}:{now.month:02d}"
        n   = self.r.incr(key)
        self.r.expire(key, 31 * 86_400)
        return n

    def get_monthly_calls(self, api_key_hash: str) -> int:
        import datetime
        now = datetime.datetime.utcnow()
        key = f"quota:{api_key_hash}:{now.year}:{now.month:02d}"
        val = self.r.get(key)
        return int(val) if val else 0

    # ── Epsilon budget (DP) ──────────────────────────────────

    def consume_epsilon(self, api_key_hash: str, epsilon: float, max_budget: float = 10.0) -> Tuple[bool, float]:
        import datetime
        today    = datetime.datetime.utcnow().strftime("%Y%m%d")
        key      = f"epsilon:{api_key_hash}:{today}"
        new_val  = self.r.incrby(key, int(epsilon * 10_000))
        self.r.expire(key, 86_400)
        consumed  = new_val / 10_000
        remaining = max(0.0, max_budget - consumed)
        return consumed <= max_budget, remaining

    def health(self) -> dict:
        info = self.r.info()
        return {
            "status":           "ok",
            "connected_clients": info.get("connected_clients"),
            "used_memory_mb":   round(info.get("used_memory", 0) / 1e6, 1),
        }
