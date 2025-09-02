from services.database import DatabaseManager


def test_database_crud(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    post = {
        "post_id": "p1",
        "platform": "twitter",
        "author": "alice",
        "content": "hello",
        "created_at": "2024-01-01T00:00:00",
        "url": "https://x.com/1",
    }
    db.add_post(post)
    rows = db.get_posts(limit=10)
    assert any(r.get("post_id") == "p1" for r in rows)

