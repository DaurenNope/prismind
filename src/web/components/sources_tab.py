"""
Sources Tab - Manage content sources (Telegram channels, RSS, etc.) by persona
"""

import streamlit as st
import asyncio
from typing import Dict, List
import json
from pathlib import Path


def load_sources_config() -> Dict:
    """Load sources configuration"""
    config_file = Path('config/content_sources.json')
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default configuration
    return {
        'telegram_channels': {
            'technical': [],
            'builder': [],
            'trendsetter': []
        },
        'rss_feeds': {
            'technical': [],
            'builder': [],
            'trendsetter': []
        }
    }


def save_sources_config(config: Dict):
    """Save sources configuration"""
    config_file = Path('config/content_sources.json')
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def get_persona_metadata(persona_key: str) -> Dict:
    """Get persona metadata including target niche and style"""
    personas_meta = {
        'technical': {
            'emoji': '🔧',
            'name': 'Technical Expert',
            'niche': 'AI/ML Engineers, Developers',
            'style': 'Deep technical analysis, code examples',
            'topics': ['AI', 'Machine Learning', 'Development', 'APIs', 'Infrastructure']
        },
        'builder': {
            'emoji': '🚀',
            'name': 'Startup Builder',
            'niche': 'Entrepreneurs, Founders',
            'style': 'Actionable insights, business value',
            'topics': ['Startups', 'Product', 'Growth', 'Fundraising', 'Strategy']
        },
        'trendsetter': {
            'emoji': '🔥',
            'name': 'Tech Trendsetter',
            'niche': 'Tech Enthusiasts, Early Adopters',
            'style': 'What\'s hot, future trends, hot takes',
            'topics': ['Trends', 'News', 'Crypto', 'Future Tech', 'Innovation']
        }
    }
    return personas_meta.get(persona_key, {})


def render_sources_tab():
    """Render the sources management tab"""
    
    st.title("📡 Content Sources")
    st.markdown("Manage content sources for each persona")
    
    # Load configuration
    config = load_sources_config()
    
    # Persona selector with metadata
    personas = {
        'technical': get_persona_metadata('technical'),
        'builder': get_persona_metadata('builder'),
        'trendsetter': get_persona_metadata('trendsetter')
    }
    
    selected_persona = st.selectbox(
        "Select Persona",
        options=list(personas.keys()),
        format_func=lambda x: f"{personas[x]['emoji']} {personas[x]['name']}"
    )
    
    # Show persona details
    persona_meta = personas[selected_persona]
    st.info(f"**Target Niche:** {persona_meta['niche']}  \n**Writing Style:** {persona_meta['style']}")
    
    st.markdown("---")
    
    # Tabs for different source types
    source_type = st.tabs(["📱 Telegram Channels", "📰 RSS Feeds", "⚙️ Settings"])
    
    # TELEGRAM CHANNELS TAB
    with source_type[0]:
        st.subheader(f"📱 Telegram Channels for {personas[selected_persona]['name']}")
        
        # Current channels
        telegram_channels = config['telegram_channels'].get(selected_persona, [])
        
        if telegram_channels:
            st.write(f"**{len(telegram_channels)} channels configured:**")
            
            # Display channels with delete option
            channels_to_remove = []
            for i, channel_data in enumerate(telegram_channels):
                # Support both string (old) and dict (new) format
                if isinstance(channel_data, str):
                    channel = channel_data
                    niche = persona_meta['niche']  # Use persona's default niche
                else:
                    channel = channel_data.get('username', channel_data.get('channel', ''))
                    niche = channel_data.get('niche', persona_meta['niche'])
                
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.write(f"[@{channel}](https://t.me/{channel})")
                with col2:
                    st.caption(f"🎯 {niche}")
                with col3:
                    st.write(f"✅ Active")
                with col4:
                    if st.button("🗑️", key=f"del_tg_{selected_persona}_{i}"):
                        channels_to_remove.append(channel_data)
            
            # Remove channels
            if channels_to_remove:
                for ch in channels_to_remove:
                    telegram_channels.remove(ch)
                config['telegram_channels'][selected_persona] = telegram_channels
                save_sources_config(config)
                st.rerun()
        else:
            st.info(f"No Telegram channels configured for {personas[selected_persona]['name']} yet.")
        
        # Add new channel
        st.markdown("---")
        st.write("**Add New Channel:**")
        
        col1, col2 = st.columns([2, 2])
        with col1:
            new_channel = st.text_input(
                "Channel username (without @)",
                placeholder="openai",
                key=f"new_tg_{selected_persona}"
            )
        with col2:
            new_channel_niche = st.text_input(
                "Target Niche (optional)",
                placeholder=persona_meta['niche'],
                key=f"new_tg_niche_{selected_persona}",
                help="Who is this channel's content for? Leave empty to use persona default."
            )
        
        if st.button("➕ Add Channel", key=f"add_tg_{selected_persona}"):
            if new_channel:
                # Check if already exists
                existing = [ch if isinstance(ch, str) else ch.get('username', ch.get('channel', '')) for ch in telegram_channels]
                
                if new_channel.strip() not in existing:
                    # Add with niche metadata
                    channel_data = {
                        'username': new_channel.strip(),
                        'niche': new_channel_niche.strip() if new_channel_niche.strip() else persona_meta['niche'],
                        'persona': selected_persona
                    }
                    telegram_channels.append(channel_data)
                    config['telegram_channels'][selected_persona] = telegram_channels
                    save_sources_config(config)
                    st.success(f"Added @{new_channel} targeting {channel_data['niche']}")
                    st.rerun()
                else:
                    st.warning("Channel already added")
        
        # Suggested channels
        st.markdown("---")
        st.write("**💡 Suggested Channels:**")
        
        suggestions = {
            'technical': [
                ('openai', 'OpenAI announcements'),
                ('anthropic', 'Anthropic/Claude updates'),
                ('huggingface', 'HuggingFace models'),
                ('aiexplained', 'AI Explained'),
            ],
            'builder': [
                ('ycombinator', 'Y Combinator'),
                ('producthunt', 'Product Hunt'),
                ('indiehackers', 'Indie Hackers'),
                ('durov', 'Pavel Durov'),
            ],
            'trendsetter': [
                ('yoheinakajima', 'Yohei Nakajima'),
                ('aiexplained', 'AI Explained'),
                ('whale_alert', 'Whale Alert'),
                ('breaking', 'Breaking News'),
            ]
        }
        
        persona_suggestions = suggestions.get(selected_persona, [])
        
        cols = st.columns(2)
        for i, (channel, desc) in enumerate(persona_suggestions):
            existing = [ch if isinstance(ch, str) else ch.get('username', ch.get('channel', '')) for ch in telegram_channels]
            
            with cols[i % 2]:
                if channel not in existing:
                    if st.button(f"➕ @{channel}", key=f"suggest_tg_{selected_persona}_{channel}"):
                        channel_data = {
                            'username': channel,
                            'niche': persona_meta['niche'],
                            'persona': selected_persona
                        }
                        telegram_channels.append(channel_data)
                        config['telegram_channels'][selected_persona] = telegram_channels
                        save_sources_config(config)
                        st.rerun()
                    st.caption(desc)
                else:
                    st.write(f"✅ @{channel}")
                    st.caption(desc)
    
    # RSS FEEDS TAB
    with source_type[1]:
        st.subheader(f"📰 RSS Feeds for {personas[selected_persona]['name']}")
        
        rss_feeds = config['rss_feeds'].get(selected_persona, [])
        
        if rss_feeds:
            st.write(f"**{len(rss_feeds)} feeds configured:**")
            
            feeds_to_remove = []
            for i, feed in enumerate(rss_feeds):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"{feed.get('name', 'Unnamed')}")
                    st.caption(feed.get('url', '')[:50] + '...')
                with col2:
                    st.write(f"✅ Active")
                with col3:
                    if st.button("🗑️", key=f"del_rss_{selected_persona}_{i}"):
                        feeds_to_remove.append(feed)
            
            if feeds_to_remove:
                for feed in feeds_to_remove:
                    rss_feeds.remove(feed)
                config['rss_feeds'][selected_persona] = rss_feeds
                save_sources_config(config)
                st.rerun()
        else:
            st.info(f"No RSS feeds configured for {personas[selected_persona]['name']} yet.")
        
        # Add new feed
        st.markdown("---")
        st.write("**Add New RSS Feed:**")
        
        feed_name = st.text_input(
            "Feed Name",
            placeholder="TechCrunch",
            key=f"new_rss_name_{selected_persona}"
        )
        feed_url = st.text_input(
            "Feed URL",
            placeholder="https://techcrunch.com/feed/",
            key=f"new_rss_url_{selected_persona}"
        )
        
        if st.button("➕ Add Feed", key=f"add_rss_{selected_persona}"):
            if feed_name and feed_url:
                rss_feeds.append({'name': feed_name, 'url': feed_url})
                config['rss_feeds'][selected_persona] = rss_feeds
                save_sources_config(config)
                st.success(f"Added {feed_name}")
                st.rerun()
    
    # SETTINGS TAB
    with source_type[2]:
        st.subheader("⚙️ Collection Settings")
        
        st.write("**Telegram Settings:**")
        
        # Check if Telegram is configured
        import os
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        
        if api_id and api_hash:
            st.success("✅ Telegram API credentials configured")
            
            # Collection settings
            col1, col2 = st.columns(2)
            with col1:
                messages_per_channel = st.number_input(
                    "Messages per channel",
                    min_value=10,
                    max_value=200,
                    value=50,
                    step=10
                )
            with col2:
                days_back = st.number_input(
                    "Days back",
                    min_value=1,
                    max_value=30,
                    value=7,
                    step=1
                )
            
            st.markdown("---")
            
            # Manual collection button
            if st.button("🔄 Collect Now", type="primary"):
                with st.spinner("Collecting from all channels..."):
                    try:
                        # Run collection
                        from src.core.extraction.telegram_channel_extractor import TelegramChannelExtractor
                        from src.supabase_manager import SupabaseManager
                        
                        async def collect():
                            extractor = TelegramChannelExtractor()
                            supabase = SupabaseManager()
                            
                            await extractor.connect()
                            
                            # Build channel list with persona/niche mapping
                            channel_map = {}  # channel -> {persona, niche}
                            all_channels = []
                            
                            for persona_key, persona_channels in config['telegram_channels'].items():
                                for channel_data in persona_channels:
                                    if isinstance(channel_data, str):
                                        channel = channel_data
                                        niche = get_persona_metadata(persona_key)['niche']
                                    else:
                                        channel = channel_data.get('username', channel_data.get('channel', ''))
                                        niche = channel_data.get('niche', get_persona_metadata(persona_key)['niche'])
                                    
                                    if channel not in channel_map:
                                        all_channels.append(channel)
                                        channel_map[channel] = {
                                            'persona': persona_key,
                                            'niche': niche
                                        }
                            
                            results = await extractor.scrape_channels(
                                all_channels,
                                limit_per_channel=messages_per_channel,
                                days_back=days_back
                            )
                            
                            await extractor.disconnect()
                            
                            # Save to database with niche metadata
                            saved = 0
                            for channel, messages in results.items():
                                channel_meta = channel_map.get(channel, {})
                                
                                for msg in messages:
                                    try:
                                        # Check if exists
                                        existing = supabase.client.table('posts')\
                                            .select('id')\
                                            .eq('post_id', msg['id'])\
                                            .execute()
                                        
                                        if not existing.data:
                                            post_data = {
                                                'post_id': msg['id'],
                                                'platform': 'telegram',
                                                'content': msg['text'],
                                                'url': msg['url'],
                                                'author': channel,
                                                'author_handle': f"@{channel}",
                                                'created_at': msg['date'].isoformat(),
                                                'is_saved': True,
                                                # Add niche metadata for rewriter
                                                'metadata': json.dumps({
                                                    'source_persona': channel_meta.get('persona'),
                                                    'target_niche': channel_meta.get('niche'),
                                                    'source_type': 'telegram_channel'
                                                })
                                            }
                                            
                                            supabase.client.table('posts').insert(post_data).execute()
                                            saved += 1
                                    except:
                                        pass
                            
                            return saved, sum(len(msgs) for msgs in results.values())
                        
                        saved, total = asyncio.run(collect())
                        
                        st.success(f"✅ Collected {total} messages, saved {saved} new posts!")
                    
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        else:
            st.warning("⚠️ Telegram API not configured")
            st.write("**Setup Instructions:**")
            st.write("1. Go to https://my.telegram.org/apps")
            st.write("2. Create an app and get credentials")
            st.write("3. Add to `.env`:")
            st.code("""
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
            """)
        
        st.markdown("---")
        
        st.write("**Schedule:**")
        st.info("💡 Tip: Set up a cron job to collect automatically")
        st.code("0 */4 * * * cd /path/to/prismind && .venv311/bin/python collect_telegram_channels.py")
    
    # Bottom stats
    st.markdown("---")
    st.subheader("📊 Sources Summary")
    
    col1, col2, col3 = st.columns(3)
    
    for i, (persona_key, persona_info) in enumerate(personas.items()):
        tg_count = len(config['telegram_channels'].get(persona_key, []))
        rss_count = len(config['rss_feeds'].get(persona_key, []))
        
        with [col1, col2, col3][i]:
            st.metric(
                f"{persona_info['emoji']} {persona_info['name']}",
                f"{tg_count + rss_count}",
                f"{tg_count} Telegram, {rss_count} RSS"
            )


if __name__ == "__main__":
    render_sources_tab()
