"""R-613: SovereignCompressor.reset() regression tests.

Bug: reset() called undefined self._load_index() and self.core (never assigned)
— same class as R-609/R-612. Fixed to use get_core() + real _load_index().
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def test_compressor_reset_works():
    """reset() must not raise (was AttributeError: _load_index / core)."""
    from memory.compress import SovereignCompressor

    c = SovereignCompressor()
    c.reset()
    assert c._index is not None
    assert "compressions" in c._index


def test_compressor_reset_twice():
    """reset() must be idempotent."""
    from memory.compress import SovereignCompressor

    c = SovereignCompressor()
    c.reset()
    c.reset()
    assert c.compression_history == []
