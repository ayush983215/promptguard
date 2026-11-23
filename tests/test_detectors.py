import pytest

from pguard.detectors import detect, luhn_ok, shannon_entropy

FAKE_AWS = "AKIAIOSFODNN7EXAMPLE"
FAKE_AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
FAKE_GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
FAKE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA1234\n-----END RSA PRIVATE KEY-----"


def types(text):
    return {f.type for f in detect(text)}


@pytest.mark.parametrize("text,expected", [
    (f"key {FAKE_AWS}", "aws_access_key"),
    (f"aws_secret_access_key = {FAKE_AWS_SECRET}", "aws_secret_key"),
    (f"token {FAKE_GH}", "github_token"),
    (f"here:\n{FAKE_KEY}\nthanks", "private_key"),
    ("xoxb-1234567890-abcdefghij", "slack_token"),
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U", "jwt"),
    ("mail jane.doe@example.com", "email"),
    ("pay with 4111 1111 1111 1111", "credit_card"),
    ("server at 192.168.10.5", "internal_ip"),
    ("host payroll-db.corp is down", "internal_hostname"),
    ("call +91 98765 43210", "phone"),
    ("call (555) 123-4567", "phone"),
    ("secret Xk9mQ2vL8pR4tY7wZ3nB6cD1fG5hJ0a", "high_entropy"),
])
def test_detects(text, expected):
    assert expected in types(text)


def test_unterminated_private_key_takes_the_rest():
    f = [x for x in detect("x -----BEGIN PRIVATE KEY-----\nabc") if x.type == "private_key"][0]
    assert f.end == len("x -----BEGIN PRIVATE KEY-----\nabc")


@pytest.mark.parametrize("text", [
    "plain sentence about sorting lists",
    "commit 3f786850e387550fdab836ed7e6dc881de23001b",            # git SHA
    "id 123e4567-e89b-12d3-a456-426614174000",                    # UUID
    "built at 2024-01-15 10:30:45 ok",                            # timestamp
    "version 3.12.1 and ip 8.8.8.8 and loopback 127.0.0.1",       # public/loopback IPs
    "order 1234567890123456 total",                               # 16 digits, fails Luhn
    "def get_customer_account_balance_for_user(): pass",          # long identifier
    "https://example.com/docs/getting-started",
])
def test_no_false_positive(text):
    assert detect(text) == []


def test_luhn():
    assert luhn_ok("4111111111111111")
    assert not luhn_ok("4111111111111112")


def test_entropy_orders_random_above_english():
    assert shannon_entropy("Xk9mQ2vL8pR4tY7wZ3nB6cD1fG5hJ0a") > shannon_entropy("aaaaaaaabbbbbbbbaaaaaaaabbbbbbbb")


def test_base64_wrapped_secret_is_caught():
    import base64
    blob = base64.b64encode(FAKE_AWS.encode()).decode()
    assert "encoded_secret" in types(f"please decode {blob}")


def test_overlap_keeps_higher_priority():
    # the email sits inside a private key block: only the key survives
    text = "-----BEGIN PRIVATE KEY-----\nbob@example.com\n-----END PRIVATE KEY-----"
    assert types(text) == {"private_key"}


def test_repr_does_not_leak_value():
    f = detect(f"key {FAKE_AWS}")[0]
    assert FAKE_AWS not in repr(f)


# ---- encoding hardening ----
def _b64(s):
    import base64
    return base64.b64encode(s.encode()).decode()


def test_hex_encoded_key_is_caught():
    assert "encoded_secret" in types("see " + FAKE_AWS.encode().hex())


def test_double_and_triple_base64_are_caught():
    assert "encoded_secret" in types(_b64(_b64(FAKE_AWS)))
    assert "encoded_secret" in types(_b64(_b64(_b64(FAKE_AWS))))


def test_git_sha_is_not_treated_as_encoded_secret():
    assert detect("3f786850e387550fdab836ed7e6dc881de23001b") == []


def test_encoded_harmless_text_is_not_flagged():
    assert "encoded_secret" not in types(_b64("this is just a perfectly ordinary sentence"))
