"""
Telegram Channels Manager - Add/Remove Channels from UI
"""

import streamlit as st
from pathlib import Path


def render_telegram_channels_manager():
    """Render Telegram channel management UI"""
    
    st.subheader("🇷🇺 Telegram Channels Manager")
    
    # Check credentials
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    telegram_api_id = os.getenv('TELEGRAM_API_ID')
    telegram_api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # Load current channels
    channels_file = Path('config/telegram_channels.txt')
    
    def load_channels():
        """Load channels from config file"""
        if not channels_file.exists():
            return []
        
        channels = []
        with open(channels_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    channels.append(line)
        return channels
    
    def save_channels(channels):
        """Save channels to config file"""
        channels_file.parent.mkdir(exist_ok=True)
        with open(channels_file, 'w') as f:
            f.write("# Telegram Channels for Collection\n")
            f.write("# Add one channel username per line (without @)\n\n")
            for channel in channels:
                f.write(f"{channel}\n")
    
    # Check auth status
    if not telegram_api_id or not telegram_api_hash:
        st.error("❌ Telegram API credentials not configured")
        st.markdown("""
        ### Setup Required
        
        1. Visit https://my.telegram.org/apps
        2. Create an app to get API ID and API Hash
        3. Add to your `.env` file:
        ```
        TELEGRAM_API_ID=your_api_id
        TELEGRAM_API_HASH=your_api_hash
        TELEGRAM_PHONE=+your_phone_number
        ```
        4. Restart Streamlit
        """)
        return
    
    st.success("✅ Telegram API credentials configured")
    
    # Load current channels
    current_channels = load_channels()
    
    # Stats
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Configured Channels", len(current_channels))
    with col2:
        st.metric("Status", "Ready" if current_channels else "No channels")
    
    st.markdown("---")
    
    # Display current channels
    st.subheader("📋 Current Channels")
    
    if current_channels:
        # Create a form for removing channels
        channels_to_remove = []
        
        for i, channel in enumerate(current_channels):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"@{channel}")
            with col2:
                if st.button("🗑️", key=f"remove_{i}", help=f"Remove @{channel}"):
                    channels_to_remove.append(channel)
        
        # Remove channels
        if channels_to_remove:
            for channel in channels_to_remove:
                current_channels.remove(channel)
            save_channels(current_channels)
            st.success(f"✅ Removed {len(channels_to_remove)} channel(s)")
            st.rerun()
    else:
        st.info("No channels configured yet. Add your first channel below!")
    
    st.markdown("---")
    
    # Add new channel
    st.subheader("➕ Add New Channel")
    
    with st.form("add_channel_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            new_channel = st.text_input(
                "Channel Username",
                placeholder="channel_name (without @)",
                help="Enter the channel username without @ symbol"
            )
        
        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            add_button = st.form_submit_button("Add Channel", type="primary")
        
        if add_button:
            if new_channel:
                # Clean the input
                new_channel = new_channel.strip().replace('@', '')
                
                if new_channel in current_channels:
                    st.warning(f"⚠️ Channel @{new_channel} already exists")
                else:
                    current_channels.append(new_channel)
                    save_channels(current_channels)
                    st.success(f"✅ Added @{new_channel}")
                    st.rerun()
            else:
                st.error("❌ Please enter a channel username")
    
    st.markdown("---")
    
    # Bulk add
    with st.expander("📝 Bulk Add Channels"):
        st.markdown("Add multiple channels at once (one per line)")
        bulk_channels = st.text_area(
            "Channel List",
            placeholder="channel1\nchannel2\nchannel3",
            height=150
        )
        
        if st.button("Add All Channels"):
            if bulk_channels:
                lines = bulk_channels.strip().split('\n')
                added = 0
                
                for line in lines:
                    channel = line.strip().replace('@', '')
                    if channel and channel not in current_channels:
                        current_channels.append(channel)
                        added += 1
                
                if added > 0:
                    save_channels(current_channels)
                    st.success(f"✅ Added {added} channel(s)")
                    st.rerun()
                else:
                    st.info("No new channels to add")
    
    st.markdown("---")
    
    # Collection button
    st.subheader("🔄 Collect from Channels")
    
    if current_channels:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            limit = st.number_input(
                "Messages per channel",
                min_value=1,
                max_value=100,
                value=10,
                help="Number of recent messages to collect from each channel"
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("📥 Collect Now", type="primary"):
                st.info("🚧 Telegram collection integration coming soon!")
                st.markdown("""
                For now, you can collect via CLI:
                ```python
                from src.core.extraction.telegram_channel_extractor import TelegramChannelExtractor
                
                extractor = TelegramChannelExtractor()
                await extractor.collect_from_channels()
                ```
                """)
    else:
        st.warning("⚠️ Add channels first before collecting")
    
    # Tips
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - **Channel names**: Use the username (e.g., `cryptoforto`, not `@cryptoforto`)
    - **Public channels**: Can collect without joining
    - **Private channels**: Must be a member to collect
    - **First collection**: Will require phone verification
    """)
