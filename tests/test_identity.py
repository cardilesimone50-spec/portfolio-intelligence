import os

from portfolio_intelligence.ui import identity


def test_is_admin_false_without_secrets():
    # nessun secrets.toml in test: la allowlist è vuota, nessuno è admin
    assert identity.is_admin("someone@example.com") is False


def test_auth_required_but_missing_false_by_default(monkeypatch):
    # indipendente da un eventuale secrets.toml locale: auth_configured mockata
    monkeypatch.setattr(identity, "auth_configured", lambda: False)
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    assert identity.auth_required_but_missing() is False


def test_auth_required_but_missing_true_when_flag_set_and_no_auth(monkeypatch):
    monkeypatch.setattr(identity, "auth_configured", lambda: False)
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert identity.auth_required_but_missing() is True


def test_auth_required_but_missing_false_when_flag_off(monkeypatch):
    monkeypatch.setattr(identity, "auth_configured", lambda: False)
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    assert identity.auth_required_but_missing() is False


def test_auth_required_but_missing_false_when_auth_is_configured(monkeypatch):
    monkeypatch.setattr(identity, "auth_configured", lambda: True)
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert identity.auth_required_but_missing() is False


# -------------------------------------------- auth_configured: serve client_id vero


def test_auth_configured_false_when_auth_section_has_no_client_id(monkeypatch):
    # [auth] può esistere solo per require_auth, senza nessuna credenziale
    # OIDC: non è "configurato" solo perché la sezione compare nei secrets
    monkeypatch.setattr(identity.st, "secrets", {"auth": {"require_auth": False}})
    assert identity.auth_configured() is False


def test_auth_configured_true_when_client_id_present(monkeypatch):
    monkeypatch.setattr(identity.st, "secrets", {"auth": {"client_id": "abc123"}})
    assert identity.auth_configured() is True


def test_auth_configured_false_without_any_secrets(monkeypatch):
    monkeypatch.setattr(identity.st, "secrets", {})
    assert identity.auth_configured() is False


# --------------------------------------- resolve_require_auth: precedenza env>secrets>default


def test_resolve_require_auth_env_var_explicit_wins_over_secrets(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.setattr(identity.st, "secrets", {"auth": {"require_auth": False}})
    identity.resolve_require_auth(default_if_unset=False)
    assert os.environ["REQUIRE_AUTH"] == "true"  # l'operatore ha scelto, non si tocca


def test_resolve_require_auth_falls_back_to_secrets_when_env_unset(monkeypatch):
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    monkeypatch.setattr(identity.st, "secrets", {"auth": {"require_auth": True}})
    identity.resolve_require_auth(default_if_unset=False)
    assert os.environ["REQUIRE_AUTH"] == "true"  # letto dai secrets, non dal default


def test_resolve_require_auth_falls_back_to_default_when_neither_set(monkeypatch):
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    monkeypatch.setattr(identity.st, "secrets", {})
    identity.resolve_require_auth(default_if_unset=True)
    assert os.environ["REQUIRE_AUTH"] == "true"  # nessuna scelta esplicita: usa il default
