from scrape_state_manager import ScrapeStateManager


def test_scrape_state_roundtrip(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    mgr = ScrapeStateManager(db_path=str(db_path))
    mgr.update_scrape_state("twitter", last_post_id="1", last_post_url="u", posts_scraped=3, success=True)
    info = mgr.get_last_scrape_info("twitter")
    assert info is not None
    assert info["last_post_id"] == "1"
    count = mgr.get_scraped_posts_count("twitter")
    assert count == 0
    mgr.mark_post_scraped("p1", "twitter", url="u", title="t", author="a")
    assert mgr.get_scraped_posts_count("twitter") == 1

