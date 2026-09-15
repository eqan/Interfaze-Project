"""
Unit tests for semantic plain-text chunking.
"""

# pyright: reportMissingImports=false

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3] / "app"
TESTS_ROOT = Path(__file__).resolve().parents[2]
tests_root_str = str(TESTS_ROOT)
while tests_root_str in sys.path:
    sys.path.remove(tests_root_str)
sys.path.insert(0, str(APP_ROOT))
sys.modules.pop("config", None)
sys.modules.pop("config.settings", None)

from web_extract.plain_text_chunks import chunk_plain_text  # noqa: E402

if tests_root_str not in sys.path:
    sys.path.insert(0, tests_root_str)


def test_chunk_plain_text_keeps_blocks_together_when_possible():
    text = "\n".join(
        [
            "h1 | Example Domain",
            "p | First paragraph about the page",
            "p | Second paragraph with supporting context",
            "p | Third paragraph with extra details",
        ]
    )

    chunks = chunk_plain_text(text, chunk_chars=85)

    assert chunks == [
        "h1 | Example Domain\np | First paragraph about the page",
        "p | First paragraph about the page\np | Second paragraph with supporting context",
        "p | Second paragraph with supporting context\np | Third paragraph with extra details",
    ]


def test_chunk_plain_text_preserves_large_block_with_overlap_fallback():
    block = "p | " + ("A" * 120)

    chunks = chunk_plain_text(block, chunk_chars=50)

    assert len(chunks) >= 3
    assert chunks[0] == block[:50]
    assert chunks[1].startswith(block[45:50])
    assert chunks[-1].endswith("A" * 30)
