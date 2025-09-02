import os
import json
import types
import pytest

from services.notifier_webhook import WebhookNotifier


def test_webhook_notifier_disabled(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    notifier = WebhookNotifier()
    assert notifier.enabled() is False
    assert notifier.notify({"ok": True}) is False


def test_webhook_notifier_enabled_success(monkeypatch):
    def fake_urlopen(req, timeout=10):
        resp = types.SimpleNamespace(status=200)
        return resp

    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/webhook")
    # Patch urllib inside module
    import services.notifier_webhook as mod

    mod.urllib.request.urlopen = fake_urlopen  # type: ignore

    notifier = WebhookNotifier()
    assert notifier.enabled() is True
    assert notifier.notify({"hello": "world"}) is True
