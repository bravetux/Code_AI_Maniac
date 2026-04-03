import pytest
from tools.chunk_file import chunk_by_lines, estimate_tokens


def test_chunk_small_file_returns_one_chunk():
    content = "\n".join(f"line {i}" for i in range(10))
    chunks = chunk_by_lines(content, max_tokens=4000)
    assert len(chunks) == 1
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 10


def test_chunk_large_file_returns_multiple():
    content = "\n".join(f"line {i}" for i in range(200))
    chunks = chunk_by_lines(content, max_tokens=200)
    assert len(chunks) > 1
    # chunks should be contiguous
    for i in range(len(chunks) - 1):
        assert chunks[i]["end_line"] + 1 == chunks[i + 1]["start_line"]


def test_estimate_tokens():
    assert estimate_tokens("hello world") == pytest.approx(3, abs=1)


def test_chunk_preserves_content():
    content = "def foo():\n    pass\ndef bar():\n    return 1\n"
    chunks = chunk_by_lines(content, max_tokens=4000)
    reassembled = "".join(c["content"] for c in chunks)
    assert reassembled == content
