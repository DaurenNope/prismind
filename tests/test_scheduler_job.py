import types
from services.aps_scheduler_runner import run_collection_job


def test_scheduler_job_monkeypatch(monkeypatch):
    # Patch DatabaseManager to return empty
    class FakeDB:
        def get_all_posts(self, include_deleted=False):
            import pandas as pd
            return pd.DataFrame()

    monkeypatch.setattr("services.aps_scheduler_runner.DatabaseManager", lambda: FakeDB(), raising=True)

    # Patch collectors to no-op
    monkeypatch.setattr("services.aps_scheduler_runner.collect_twitter_bookmarks", lambda db, ids, urls: 0, raising=True)
    monkeypatch.setattr("services.aps_scheduler_runner.collect_reddit_bookmarks", lambda db, ids, urls: 0, raising=True)

    # Patch notifier
    class FakeNotifier:
        def __init__(self):
            self.called = False

        def enabled(self):
            return True

        def notify(self, payload):
            self.called = True
            return True

    fake = FakeNotifier()
    monkeypatch.setattr("services.aps_scheduler_runner.WebhookNotifier", lambda: fake, raising=True)

    run_collection_job()
    assert fake.called is True

