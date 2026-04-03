import os
from tools.fetch_local import fetch_local_file, fetch_multiple_local_files


def test_fetch_entire_file(tmp_path):
    f = tmp_path / "hello.py"
    f.write_text("line1\nline2\nline3\n")
    result = fetch_local_file(str(f))
    assert result["content"] == "line1\nline2\nline3\n"
    assert result["total_lines"] == 3
    assert result["file_path"] == str(f)


def test_fetch_line_range(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("\n".join(f"line{i}" for i in range(1, 11)) + "\n")
    result = fetch_local_file(str(f), start_line=3, end_line=5)
    assert result["content"] == "line3\nline4\nline5\n"
    assert result["start_line"] == 3
    assert result["end_line"] == 5


def test_fetch_missing_file():
    result = fetch_local_file("/nonexistent/path.py")
    assert "error" in result


def test_fetch_multiple_files(tmp_path):
    files = []
    for i in range(3):
        f = tmp_path / f"file{i}.py"
        f.write_text(f"# file {i}\n")
        files.append(str(f))
    results = fetch_multiple_local_files(files)
    assert len(results) == 3
    assert all("content" in r for r in results)
