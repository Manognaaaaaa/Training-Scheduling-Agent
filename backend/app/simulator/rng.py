"""Deterministic random numbers.

Python's built-in ``hash()`` changes between runs, so we build our own stable hash
from SHA-256. Every random decision in the simulator gets its own tiny RNG seeded from
(seed, decision name, ids...). That makes results independent of *how many days* we
advance at once: advancing 7 + 7 days gives the same outcome as 14.
"""
import hashlib
import random


def stable_hash(*parts: object) -> int:
    """Turn any mix of values into the same big integer on every run and machine."""
    text = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def rng_for(seed: int, *parts: object) -> random.Random:
    """A fresh ``random.Random`` dedicated to one decision, e.g. rng_for(42, "attend", session_id, driver_id)."""
    return random.Random(stable_hash(seed, *parts))
