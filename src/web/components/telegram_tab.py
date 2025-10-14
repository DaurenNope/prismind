"""
Telegram Intelligence Tab
Browse, filter, translate, and use Russian crypto intelligence
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path('.env'), override=True)

from supabase import create_client


def get_supabase():
    """Get Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(url, key)


def translate_message(message_id: str, content: str) -> str:
    """Translate Russian message to English using qwen2.5:3b"""
    import httpx
    
    prompt = f"""Translate this Russian crypto/investment text to English. Be concise and clear.

Russian:
{content[:1000]}

English:"""
    
    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            translation = response.json().get('response', '').strip()
            
            # Save to database
            supabase = get_supabase()
            supabase.table('telegram_messages')\
                .update({'content_en': translation})\
                .eq('id', message_id)\
                .execute()
            
            return translation
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Translation failed: {str(e)}"


def render_telegram_tab():
    """Render Telegram Intelligence tab"""
    
    st.title("🇷🇺 Telegram Intelligence")
    st.markdown("**Russian crypto channels** - Browse, filter, translate, and use")
    
    # Get Supabase client
    supabase = get_supabase()
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Filters")
        
        # Quality filter
        min_score = st.slider("Min Quality Score", 0, 10, 7)
        
        # Category filter
        categories = st.multiselect(
            "Categories",
            ["Alpha/News", "Airdrop", "Analysis", "General"],
            default=["Alpha/News", "Airdrop"]
        )
        
        # Special flags
        show_alpha = st.checkbox("🔥 Alpha Signals Only", value=False, key="telegram_alpha_only")
        show_airdrop = st.checkbox("💰 Airdrops Only", value=False, key="telegram_airdrop_only")
        
        # Translation status
        translation_filter = st.radio(
            "Translation Status",
            ["All", "Translated", "Not Translated"],
            index=0
        )
        
        # Channel filter
        channels_data = supabase.table('telegram_messages')\
            .select('channel_username')\
            .execute()
        
        unique_channels = sorted(list(set([m['channel_username'] for m in channels_data.data])))
        selected_channels = st.multiselect(
            "Channels",
            unique_channels,
            default=[]
        )
    
    # Build query
    query = supabase.table('telegram_messages').select('*')
    
    # Apply filters
    if min_score > 0:
        query = query.gte('value_score', min_score)
    
    if categories:
        query = query.in_('category', categories)
    
    if show_alpha:
        query = query.eq('is_alpha', True)
    
    if show_airdrop:
        query = query.eq('is_airdrop', True)
    
    if selected_channels:
        query = query.in_('channel_username', selected_channels)
    
    # Execute query
    result = query.order('date', desc=True).limit(100).execute()
    messages = result.data
    
    # Filter by translation status (client-side)
    if translation_filter == "Translated":
        messages = [m for m in messages if m.get('content_en')]
    elif translation_filter == "Not Translated":
        messages = [m for m in messages if not m.get('content_en')]
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Messages", len(messages))
    with col2:
        translated = len([m for m in messages if m.get('content_en')])
        st.metric("Translated", translated)
    with col3:
        alpha_count = len([m for m in messages if m.get('is_alpha')])
        st.metric("🔥 Alpha", alpha_count)
    with col4:
        airdrop_count = len([m for m in messages if m.get('is_airdrop')])
        st.metric("💰 Airdrops", airdrop_count)
    
    st.markdown("---")
    
    # Actions bar
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    with col2:
        if st.button("📥 Export Selected (CSV)"):
            if messages:
                df = pd.DataFrame(messages)
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "telegram_messages.csv",
                    "text/csv"
                )
    with col3:
        sort_by = st.selectbox("Sort by", ["Date", "Score", "Channel"], index=1)
    
    # Sort messages
    if sort_by == "Date":
        messages = sorted(messages, key=lambda x: x.get('date', ''), reverse=True)
    elif sort_by == "Score":
        messages = sorted(messages, key=lambda x: x.get('value_score', 0), reverse=True)
    elif sort_by == "Channel":
        messages = sorted(messages, key=lambda x: x.get('channel_username', ''))
    
    st.markdown("---")
    
    # Display messages
    if not messages:
        st.info("No messages found. Adjust your filters or run the Telegram scraper.")
    else:
        # Initialize session state for selected messages
        if 'selected_messages' not in st.session_state:
            st.session_state.selected_messages = set()
        
        # Bulk actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"✅ Select All ({len(messages)})"):
                st.session_state.selected_messages = set([m['id'] for m in messages])
                st.rerun()
        with col2:
            if st.button("❌ Clear Selection"):
                st.session_state.selected_messages = set()
                st.rerun()
        with col3:
            selected_count = len(st.session_state.selected_messages)
            if selected_count > 0:
                if st.button(f"🌐 Translate Selected ({selected_count})"):
                    with st.spinner(f"Translating {selected_count} messages..."):
                        progress_bar = st.progress(0)
                        for i, msg_id in enumerate(st.session_state.selected_messages):
                            msg = next((m for m in messages if m['id'] == msg_id), None)
                            if msg and not msg.get('content_en'):
                                translate_message(msg_id, msg['content'])
                            progress_bar.progress((i + 1) / selected_count)
                        st.success(f"✅ Translated {selected_count} messages!")
                        st.rerun()
        
        st.markdown("---")
        
        # Display messages as cards
        for idx, msg in enumerate(messages):
            msg_id = msg['id']
            is_selected = msg_id in st.session_state.selected_messages
            # Create unique key suffix
            unique_suffix = f"{idx}_{str(msg_id)[:8]}"
            
            # Card container
            with st.container():
                col_checkbox, col_content = st.columns([0.05, 0.95])
                
                with col_checkbox:
                    if st.checkbox("", value=is_selected, key=f"check_{unique_suffix}"):
                        st.session_state.selected_messages.add(msg_id)
                    else:
                        st.session_state.selected_messages.discard(msg_id)
                
                with col_content:
                    # Header
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        channel = msg.get('channel_username', 'Unknown')
                        st.markdown(f"### @{channel}")
                    with col2:
                        score = msg.get('value_score', 0)
                        score_color = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
                        st.markdown(f"**{score_color} Score: {score}/10**")
                    with col3:
                        date = msg.get('date', '')[:10]
                        st.markdown(f"📅 {date}")
                    
                    # Badges
                    badges = []
                    if msg.get('is_alpha'):
                        badges.append("🔥 Alpha")
                    if msg.get('is_airdrop'):
                        badges.append("💰 Airdrop")
                    if msg.get('is_whitelist'):
                        badges.append("📝 Whitelist")
                    
                    category = msg.get('category', 'General')
                    badges.append(f"📂 {category}")
                    
                    st.markdown(" ".join([f"`{b}`" for b in badges]))
                    
                    # AI Summary
                    summary = msg.get('ai_summary', '')
                    if summary:
                        st.markdown(f"**💡 Summary:** {summary[:200]}...")
                    
                    # Content tabs
                    tabs = ["🇷🇺 Russian", "🇬🇧 English", "Actions"]
                    tab1, tab2, tab3 = st.tabs(tabs)
                    
                    with tab1:
                        content = msg.get('content', '')
                        st.text_area("Russian Content", content, height=150, key=f"ru_{unique_suffix}", disabled=True)
                    
                    with tab2:
                        content_en = msg.get('content_en', '')
                        if content_en:
                            st.text_area("English Translation", content_en, height=150, key=f"en_{unique_suffix}", disabled=True)
                        else:
                            st.info("Not translated yet")
                            if st.button("🌐 Translate Now", key=f"translate_{unique_suffix}"):
                                with st.spinner("Translating..."):
                                    translation = translate_message(msg_id, msg['content'])
                                    st.success("✅ Translated!")
                                    st.rerun()
                    
                    with tab3:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("📝 Send to Rewriter", key=f"rewrite_{unique_suffix}"):
                                st.session_state.rewriter_content = msg.get('content_en') or msg.get('content')
                                st.success("✅ Sent to Rewriter tab!")
                        with col2:
                            if st.button("💾 Save as Bookmark", key=f"save_{unique_suffix}"):
                                st.info("Bookmark feature coming soon!")
                        with col3:
                            if st.button("🔗 View Channel", key=f"channel_{unique_suffix}"):
                                st.markdown(f"https://t.me/{channel}")
                
                st.markdown("---")


if __name__ == "__main__":
    render_telegram_tab()
