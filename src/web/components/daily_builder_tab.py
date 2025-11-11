"""
Daily Builder Post Generator for Qronoya

Conversational UI that helps extract today's updates and combines them with
usable_posts from the database to create authentic daily builder posts.
"""

import streamlit as st
import asyncio
from datetime import datetime
from supabase import create_client
import os
from typing import List, Dict
import google.generativeai as genai

# Configure Gemini
gemini_key = os.getenv('GEMINI_API_KEY')
if gemini_key:
    genai.configure(api_key=gemini_key)


def render_daily_builder_tab():
    """Render the daily builder post generator"""

    st.header("📝 Daily Builder Post")
    st.markdown("Let's create today's builder update for Qronoya")

    # Initialize session state
    if 'daily_builder_state' not in st.session_state:
        st.session_state.daily_builder_state = {
            'step': 1,
            'today_work': '',
            'wins': [],
            'challenges': [],
            'learned': '',
            'related_posts': [],
            'generated_post': ''
        }

    state = st.session_state.daily_builder_state

    # Show progress
    st.progress(state['step'] / 5)

    st.divider()

    if state['step'] == 1:
        render_step_1(state)
    elif state['step'] == 2:
        render_step_2(state)
    elif state['step'] == 3:
        render_step_3(state)
    elif state['step'] == 4:
        render_step_4(state)
    elif state['step'] == 5:
        render_step_5(state)


def render_step_1(state):
    """Step 1: What did you work on today?"""

    st.subheader("💻 What did you work on today?")
    st.caption("Be specific - what feature, bug, or experiment?")

    work = st.text_area(
        "Today's work:",
        value=state['today_work'],
        height=150,
        placeholder="e.g., Built an AI wizard that generates social media profiles from conversational interviews..."
    )

    if st.button("Next →", type="primary"):
        if work.strip():
            state['today_work'] = work
            state['step'] = 2
            st.rerun()
        else:
            st.error("Please describe what you worked on")


def render_step_2(state):
    """Step 2: Quick wins"""

    st.subheader("🎯 What worked today?")
    st.caption("Quick wins, breakthroughs, or things that clicked")

    st.markdown(f"**Working on:** {state['today_work'][:100]}...")

    win1 = st.text_input("Win #1:", key="win1", placeholder="e.g., Wizard completes profile setup in under 10 mins")
    win2 = st.text_input("Win #2 (optional):", key="win2", placeholder="e.g., Data-driven angle suggestions actually work")
    win3 = st.text_input("Win #3 (optional):", key="win3", placeholder="")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back"):
            state['step'] = 1
            st.rerun()

    with col2:
        if st.button("Next →", type="primary"):
            if win1.strip():
                state['wins'] = [w for w in [win1, win2, win3] if w.strip()]
                state['step'] = 3
                st.rerun()
            else:
                st.error("At least one win please!")


def render_step_3(state):
    """Step 3: Challenges/learnings"""

    st.subheader("🤔 What was tricky? What did you learn?")
    st.caption("Challenges faced or insights gained")

    st.markdown(f"**Wins:**")
    for i, win in enumerate(state['wins'], 1):
        st.markdown(f"✓ {win}")

    challenge1 = st.text_input("Challenge/Learning #1:", key="chal1", placeholder="e.g., Rate limiting on free Gemini tier")
    challenge2 = st.text_input("Challenge/Learning #2 (optional):", key="chal2", placeholder="")

    learned = st.text_area(
        "Key insight:",
        height=100,
        placeholder="e.g., Angle suggestions need actual data patterns, not generic AI advice"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back"):
            state['step'] = 2
            st.rerun()

    with col2:
        if st.button("Next →", type="primary"):
            challenges = [c for c in [challenge1, challenge2] if c.strip()]
            if challenges or learned.strip():
                state['challenges'] = challenges
                state['learned'] = learned
                state['step'] = 4
                st.rerun()
            else:
                st.error("Share at least one challenge or learning")


def render_step_4(state):
    """Step 4: Pull related posts from usable_posts"""

    st.subheader("🔍 Finding Related Content")
    st.caption("Looking for relevant posts from your collection...")

    # Get related posts
    if not state['related_posts']:
        with st.spinner("Analyzing usable_posts..."):
            state['related_posts'] = asyncio.run(get_related_posts(
                work_description=state['today_work'],
                wins=state['wins'],
                challenges=state['challenges']
            ))

    if state['related_posts']:
        st.success(f"Found {len(state['related_posts'])} relevant posts!")

        with st.expander("📚 Related Posts"):
            for i, post in enumerate(state['related_posts'][:3], 1):
                st.markdown(f"**Post {i}:** {post.get('topic', 'N/A')}")
                st.caption(post.get('content', '')[:200] + '...')
                st.caption(f"Platform: {post.get('platform')} | Score: {post.get('best_persona_score', 0)}/10")
                st.divider()
    else:
        st.info("No directly related posts found - that's okay, we'll create something original!")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("← Back"):
            state['step'] = 3
            st.rerun()

    with col2:
        if st.button("Generate Post →", type="primary"):
            state['step'] = 5
            st.rerun()


def render_step_5(state):
    """Step 5: Generate the daily post"""

    st.subheader("✨ Generated Daily Post")

    if not state['generated_post']:
        with st.spinner("Crafting your builder post..."):
            state['generated_post'] = asyncio.run(generate_builder_post(state))

    if state['generated_post']:
        st.text_area(
            "Your post:",
            value=state['generated_post'],
            height=300
        )

        st.caption(f"Character count: {len(state['generated_post'])}")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Regenerate"):
                state['generated_post'] = ''
                st.rerun()

        with col2:
            if st.button("📋 Copy to Clipboard"):
                st.code(state['generated_post'])
                st.success("Copied!")

        with col3:
            if st.button("✅ Post to Threads", type="primary"):
                # TODO: Integrate with threads publisher
                st.success("Posted! (TODO: implement)")

        st.divider()

        if st.button("← Start Over"):
            st.session_state.daily_builder_state = {
                'step': 1,
                'today_work': '',
                'wins': [],
                'challenges': [],
                'learned': '',
                'related_posts': [],
                'generated_post': ''
            }
            st.rerun()


async def get_related_posts(work_description: str, wins: List[str], challenges: List[str]) -> List[Dict]:
    """
    Query usable_posts for content related to today's work.
    Uses semantic search and keywords.
    """
    try:
        client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

        # Extract keywords from today's work
        keywords = extract_keywords(work_description, wins, challenges)

        # Query usable_posts for qronoya
        query = client.table('usable_posts').select('*').eq('best_persona_key', 'qronoya')

        # Filter by relevance window (recent and evergreen)
        query = query.in_('relevance_window', ['same-day', '24-72h', 'this-week', 'evergreen'])

        # Limit results
        query = query.limit(20)

        result = query.execute()

        if not result.data:
            return []

        # Score posts by relevance to today's work
        scored_posts = []
        for post in result.data:
            score = calculate_relevance_score(post, keywords, work_description)
            post['relevance_score'] = score
            scored_posts.append(post)

        # Sort by relevance
        scored_posts.sort(key=lambda x: x['relevance_score'], reverse=True)

        return scored_posts[:5]

    except Exception as e:
        st.error(f"Error fetching posts: {e}")
        return []


def extract_keywords(work: str, wins: List[str], challenges: List[str]) -> List[str]:
    """Extract key terms from today's work"""
    import re

    text = f"{work} {' '.join(wins)} {' '.join(challenges)}"

    # Simple keyword extraction
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())

    # Remove common words
    stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'been', 'were', 'what', 'when'}
    keywords = [w for w in words if w not in stop_words]

    return list(set(keywords))[:10]


def calculate_relevance_score(post: Dict, keywords: List[str], work_description: str) -> float:
    """Score how relevant a post is to today's work"""
    score = 0.0

    # Check content for keywords
    content = post.get('content', '').lower()
    for keyword in keywords:
        if keyword in content:
            score += 1.0

    # Check tags
    tags = post.get('tags', [])
    if isinstance(tags, list):
        for keyword in keywords:
            if any(keyword in str(tag).lower() for tag in tags):
                score += 0.5

    # Check topics
    topics = post.get('key_concepts', [])
    if isinstance(topics, list):
        for keyword in keywords:
            if any(keyword in str(topic).lower() for topic in topics):
                score += 0.3

    # Boost recent posts
    if post.get('relevance_window') in ['same-day', '24-72h']:
        score += 1.0

    # Boost high-quality posts
    quality = post.get('quality_score', 0)
    score += quality * 0.1

    return score


async def generate_builder_post(state: Dict) -> str:
    """
    Generate the final builder post using AI.
    Combines today's updates with related posts for context.
    """

    # Build context from related posts
    related_context = ""
    if state['related_posts']:
        related_context = "\n\nRELEVANT POSTS FROM COLLECTION:\n"
        for post in state['related_posts'][:3]:
            related_context += f"- {post.get('topic', 'Post')}: {post.get('content', '')[:150]}...\n"

    prompt = f"""You are Qronoya, a technical builder sharing daily updates. Your voice is:
- Technical but accessible
- Focused on learning and building in public
- Data-driven when relevant
- Honest about challenges
- Russian language, casual tone

TODAY'S UPDATE:
Work: {state['today_work']}

Wins:
{chr(10).join(['- ' + w for w in state['wins']])}

Challenges:
{chr(10).join(['- ' + c for c in state['challenges']])}

Key Learning:
{state['learned']}
{related_context}

Write a daily builder post in Russian that:
1. Starts with what you built/worked on
2. Highlights the key win or breakthrough
3. Mentions one challenge or learning (be specific!)
4. If relevant posts exist, reference similar concepts or compare approaches
5. Ends with what's next or an insight

Style:
- 150-300 characters
- Conversational, not corporate
- Include technical details when relevant
- Use line breaks for readability
- NO hashtags, NO emojis (unless absolutely necessary)
- Don't say "сегодня" or "я работал" - jump straight to the content

Return ONLY the post text, nothing else."""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating post: {e}"
