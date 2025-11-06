"""
Triage Tab - Column-based board for analysis readiness and rewrite candidacy
"""
import streamlit as st
from typing import List, Dict

from src.services.new_database_manager import NewDatabaseManager


def _is_incomplete(post: Dict) -> bool:
    required = [
        'content', 'language', 'analyzed_at', 'analysis_model', 'content_type'
    ]
    for k in required:
        v = post.get(k)
        if v is None or str(v).strip() in ("", "None"):
            return True
    return False


def _is_truncated(post: Dict) -> bool:
    c = (post.get('content') or '').strip()
    if not c:
        return False
    return c.endswith('...') or c.endswith('…') or ('...' in c) or ('…' in c) or (len(c) < 180)


def _is_ready(post: Dict) -> bool:
    if _is_incomplete(post) or _is_truncated(post):
        return False
    # simple readiness heuristic: value_score >= 3 and has ai_summary
    try:
        vs = float(post.get('value_score') or 0)
    except Exception:
        vs = 0.0
    return vs >= 3 and bool((post.get('ai_summary') or '').strip())


def _badge(text: str, color: str):
    st.markdown(f"<span style='background:{color};padding:2px 6px;border-radius:6px;color:#fff;font-size:11px'>{text}</span>", unsafe_allow_html=True)


def _render_card(post: Dict):
    st.markdown(f"**{post.get('platform','')}** · @{post.get('author_handle') or post.get('author') or ''} · {str(post.get('created_at',''))[:10]}")
    content_preview = (post.get('content') or '')[:400]
    st.write(content_preview + ("…" if len((post.get('content') or '')) > 400 else ""))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        try:
            vs = float(post.get('value_score') or 0)
        except Exception:
            vs = 0.0
        _badge(f"Val {vs}", "#6c63ff")
    with col2:
        try:
            qs = float(post.get('quality_score') or 0)
        except Exception:
            qs = 0.0
        _badge(f"Qual {qs}", "#2196f3")
    with col3:
        bk = post.get('best_persona_key') or '—'
        _badge(f"Persona {bk}", "#00b894")
    with col4:
        ct = post.get('content_type') or 'text'
        _badge(ct, "#636e72")


def render_triage_tab():
    st.subheader("🧹 Triage")

    db = NewDatabaseManager()
    posts = db.get_posts(limit=500)

    # Filters
    with st.expander("Filters", expanded=True):
        colf1, colf2, colf3, colf4 = st.columns(4)
        with colf1:
            platform = st.selectbox("Platform", ["all", "twitter", "reddit", "threads"], index=0)
        with colf2:
            min_value = st.slider("Min value score", 0, 10, 0)
        with colf3:
            only_truncated = st.checkbox("Only truncated", value=False)
        with colf4:
            only_incomplete = st.checkbox("Only incomplete", value=False)

    # Apply filters
    def _passes(p: Dict) -> bool:
        if platform != 'all' and p.get('platform') != platform:
            return False
        try:
            vs = float(p.get('value_score') or 0)
        except Exception:
            vs = 0.0
        if vs < min_value:
            return False
        if only_truncated and not _is_truncated(p):
            return False
        if only_incomplete and not _is_incomplete(p):
            return False
        return True

    posts = [p for p in posts if _passes(p)]

    # Metrics
    incomplete = [p for p in posts if _is_incomplete(p)]
    truncated = [p for p in posts if _is_truncated(p)]
    ready = [p for p in posts if _is_ready(p)]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total", len(posts))
    with c2:
        st.metric("Incomplete", len(incomplete))
    with c3:
        st.metric("Truncated", len(truncated))
    with c4:
        st.metric("Ready", len(ready))

    st.markdown("---")

    # Columns board
    colA, colB, colC, colD = st.columns(4)

    with colA:
        st.markdown("### Incomplete")
        for p in incomplete[:30]:
            with st.container(border=True):
                _render_card(p)
                st.button("Re-analyze", key=f"rean_{p.get('post_id')}")

    with colB:
        st.markdown("### Truncated")
        for p in truncated[:30]:
            with st.container(border=True):
                _render_card(p)
                st.button("DOM Refresh", key=f"dom_{p.get('post_id')}")

    with colC:
        st.markdown("### Duplicates")
        st.caption("Cluster view available in Duplicates tab")
        # Placeholder: show top suspected dupes by same author+title/url
        dupes = []
        seen = set()
        for p in posts:
            k = (p.get('author'), p.get('url'))
            if k in seen:
                dupes.append(p)
            else:
                seen.add(k)
        for p in dupes[:30]:
            with st.container(border=True):
                _render_card(p)
                st.button("Mark canonical", key=f"canon_{p.get('post_id')}")

    with colD:
        st.markdown("### Ready to Rewrite")
        for p in ready[:30]:
            with st.container(border=True):
                _render_card(p)
                st.button("Send to Rewrite", key=f"rew_{p.get('post_id')}")


