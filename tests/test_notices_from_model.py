from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from django.utils import timezone

from notices.models import Notice

from .test_utils import assert_in_content, assert_not_in_content

pytestmark = pytest.mark.django_db


def test_no_notice(client):
    resp = client.get("/", follow=True)
    assert_not_in_content(resp, 'id="noticesClear"', 'id="noticesModal"')


def test_with_notice(client, settings, notice):
    assert notice.version == 1
    for setting in ["NOTICES_TITLE", "NOTICES_CONTENT", "NOTICES_VERSION"]:
        assert not hasattr(settings, setting)

    resp = client.get("/", follow=True)
    assert_in_content(resp, "Test title", "<p>A new thing</p>", 'id="noticesModal"')


def test_colour_settings_with_notice(client, settings, notice):
    assert notice.version == 1
    settings.NOTICES_COLOUR = "#fff"
    settings.NOTICES_SAFE = True
    for setting in ["NOTICES_TITLE", "NOTICES_CONTENT", "NOTICES_VERSION"]:
        assert not hasattr(settings, setting)

    resp = client.get("/", follow=True)
    assert_in_content(
        resp,
        "Test title",
        "<p>A new thing</p>",
        'id="noticesModal"',
        'style="background: #fff;"',
    )


def test_old_colour_settings_with_notice(client, settings, notice):
    assert notice.version == 1
    settings.NOTICES_COLOR = "#fff"
    for setting in ["NOTICES_TITLE", "NOTICES_CONTENT", "NOTICES_VERSION"]:
        assert not hasattr(settings, setting)

    resp = client.get("/", follow=True)
    assert_in_content(
        resp,
        "Test title",
        "<p>A new thing</p>",
        'id="noticesModal"',
        'style="background: #fff;"',
    )


def test_latest_notice(client, notice):
    assert Notice.latest_version() == 1
    Notice.objects.create(title="New Title", content="")
    assert Notice.latest_version() == 2
    resp = client.get("/", follow=True)
    assert_in_content(resp, "New Title", 'id="noticesModal"')


def test_expired_notice(client, notice):
    notice.expires_at = timezone.now() - timedelta(1)
    notice.save()
    resp = client.get("/", follow=True)
    assert_not_in_content(resp, "Test title", 'id="noticesClear"', 'id="noticesModal"')

    notice.expires_at = timezone.now() + timedelta(1)
    notice.save()
    resp = client.get("/", follow=True)
    assert_in_content(resp, "Test title", 'id="noticesModal"')


@pytest.mark.freeze_time("2022-09-01")
def test_not_started_notice(client, notice):
    # not started, start date shown
    notice.starts_at = datetime(2022, 10, 1, 10, tzinfo=UTC)
    notice.save()
    resp = client.get("/", follow=True)
    assert_not_in_content(resp, "Test title", 'id="noticesClear"', 'id="noticesModal"')

    notice.starts_at = datetime(2022, 8, 1, 10, tzinfo=UTC)
    notice.save()
    resp = client.get("/", follow=True)
    assert_in_content(resp, "Test title", 'id="noticesModal"')


def test_version_cookie_seen(client, notice):
    client.cookies = SimpleCookie({"notices_seen": "1"})
    resp = client.get("/", follow=True)
    assert_not_in_content(resp, "Test title", 'id="noticesModal"')

    # we only assert equality, not order. If the cookie is > latest version, we show i
    client.cookies = SimpleCookie({"notices_seen": "2"})
    resp = client.get("/", follow=True)
    assert_in_content(resp, "Test title", 'id="noticesModal"')
