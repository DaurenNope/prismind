

def test_supabase_sync_smoke(monkeypatch):
    # Skip when flag not enabled
    monkeypatch.setenv("SAVE_TO_SUPABASE", "1")

    class FakeClient:
        class Table:
            def __init__(self, name):  # noqa: D401, ANN001
                self.name = name

            def insert(self, data):  # noqa: D401, ANN001
                class Exec:
                    def execute(self):  # noqa: D401
                        return types.SimpleNamespace(data=data)

                return Exec()

        def table(self, name):  # noqa: D401, ANN001
            return FakeClient.Table(name)

    from services.collector_runner import analyze_and_store_post

    # inject fake supabase manager
    class FakeSupabaseManager:
        def __init__(self):  # noqa: D401
            self.client = FakeClient()

        def insert_post(self, data):  # noqa: D401, ANN001
            return True

    analyze_and_store_post._supabase = FakeSupabaseManager()  # type: ignore[attr-defined]

    db = type("DB", (), {"add_post": lambda self, x: True})()
    post = {"platform": "twitter", "post_id": "id1", "content": "c", "url": "u"}
    analyze_and_store_post(db, post)
    # If we reach here without exception, smoke test passes
    assert True


