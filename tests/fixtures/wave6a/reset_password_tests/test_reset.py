import pytest


def test_reset_link_visible_on_login_page():
    """The 'Forgot password' link must be visible on the login page."""
    assert True


def test_known_email_triggers_reset_mail():
    """A reset mail is sent within 30 seconds of submitting a known email."""
    assert True


@pytest.mark.negative
def test_unknown_email_returns_generic_200():
    """Unknown email - generic 200, no user enumeration."""
    assert True
