import pytest
from tools.clone_repo import parse_github_url


@pytest.mark.parametrize("url,expected_owner,expected_repo", [
    ("https://github.com/bravetux/Code_AI_Maniac.git", "bravetux", "Code_AI_Maniac"),
    ("https://github.com/bravetux/Code_AI_Maniac", "bravetux", "Code_AI_Maniac"),
    ("github.com/bravetux/Code_AI_Maniac", "bravetux", "Code_AI_Maniac"),
    ("bravetux/Code_AI_Maniac", "bravetux", "Code_AI_Maniac"),
    ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
])
def test_parse_github_url(url, expected_owner, expected_repo):
    result = parse_github_url(url)
    assert result["owner"] == expected_owner
    assert result["repo"] == expected_repo
    assert result["slug"] == f"{expected_owner}/{expected_repo}"


def test_parse_github_url_invalid():
    with pytest.raises(ValueError):
        parse_github_url("")
    with pytest.raises(ValueError):
        parse_github_url("not-a-url")
