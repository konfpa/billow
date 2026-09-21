from apps.core.access import PERMISSION_EXEMPT_URL_NAMES, undeclared_views


def test_only_signing_in_and_out_the_health_check_and_home_are_exempt():
    assert (
        frozenset({"login", "logout", "healthz", "home"}) == PERMISSION_EXEMPT_URL_NAMES
    )


def test_every_view_in_billow_declares_a_permission_or_is_exempt():
    assert undeclared_views() == []


def test_a_view_that_declares_no_permission_is_named():
    assert undeclared_views("tests.core.urls_with_an_undeclared_view") == [
        "an_undeclared_view"
    ]


def test_static_and_media_are_not_billow_views():
    assert undeclared_views("tests.business.urls_serving_files") == []
