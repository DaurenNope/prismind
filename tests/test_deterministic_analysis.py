from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from core.extraction.social_extractor_base import SocialPost


def test_deterministic_mode_produces_stable_output(monkeypatch):
    monkeypatch.setenv("DETERMINISTIC_ANALYSIS", "1")

    post = SocialPost(
        platform="twitter",
        post_id="p1",
        author="alice",
        author_handle="alice",
        content="Short note about AI and systems design.",
        created_at=None,
        url="https://x.com/1",
        post_type="post",
        media_urls=[],
        hashtags=["ai", "systems"],
        mentions=[],
        engagement={},
        is_saved=True,
        saved_at=None,
        folder_category="",
        analysis=None,
    )

    analyzer = IntelligentContentAnalyzer()
    out1 = analyzer.analyze_bookmark(post)
    out2 = analyzer.analyze_bookmark(post)

    assert out1["summary"] == out2["summary"]
    assert out1["category"] == out2["category"]
    assert out1["intelligent_value_score"] == out2["intelligent_value_score"]

