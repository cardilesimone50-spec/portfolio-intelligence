from src.ui import identity


def test_is_admin_false_without_secrets():
    # nessun secrets.toml in test: la allowlist è vuota, nessuno è admin
    assert identity.is_admin("someone@example.com") is False


def test_auth_required_but_missing_false_by_default(monkeypatch):
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    assert identity.auth_required_but_missing() is False


def test_auth_required_but_missing_true_when_flag_set_and_no_auth(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert identity.auth_required_but_missing() is True


def test_auth_required_but_missing_false_when_flag_off(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    assert identity.auth_required_but_missing() is False
