import importlib.util
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.py"


def load_settings(monkeypatch, **environment):
    """Import config/settings.py afresh under `environment`.

    Loaded under a throwaway module name rather than reloaded in place: the
    real `config.settings` is what `tests/settings.py` star-imported, and
    reloading that would rewrite it underneath the running suite.
    """
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    spec = importlib.util.spec_from_file_location("settings_under_test", SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_statement_timeout_is_set_when_the_url_carries_no_options(monkeypatch):
    settings = load_settings(
        monkeypatch,
        DJANGO_DATABASE_URL="postgres://u:p@localhost:5432/billow",
        DJANGO_STATEMENT_TIMEOUT_MS="5000",
    )

    options = settings.DATABASES["default"]["OPTIONS"]

    assert options["options"] == "-c statement_timeout=5000"


def test_statement_timeout_is_appended_to_options_from_the_url(monkeypatch):
    settings = load_settings(
        monkeypatch,
        DJANGO_DATABASE_URL=(
            "postgres://u:p@localhost:5432/billow?options=-c%20search_path%3Dtenant"
        ),
        DJANGO_STATEMENT_TIMEOUT_MS="5000",
    )

    options = settings.DATABASES["default"]["OPTIONS"]

    assert options["options"] == "-c search_path=tenant -c statement_timeout=5000"


def test_other_options_from_the_url_survive(monkeypatch):
    settings = load_settings(
        monkeypatch,
        DJANGO_DATABASE_URL="postgres://u:p@localhost:5432/billow?sslmode=require",
    )

    assert settings.DATABASES["default"]["OPTIONS"]["sslmode"] == "require"
