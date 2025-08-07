#!/usr/bin/env python3
"""
PrisMind Dashboard - Modern Social Media Style
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import ast
import sys
import os

# Add the project root to the path so we can import scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_connection():
    return sqlite3.connect('data/prismind.db')

def get_category_counts():
    """Get counts for all categories"""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
    tables = cursor.fetchall()
    
    counts = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        category_name = table_name.replace('_bookmarks', '').replace('_', ' ').title()
        counts[category_name] = count
    
    conn.close()
    return counts

def get_available_categories():
    """Get list of available categories with their table names"""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
    tables = cursor.fetchall()
    
    categories = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        if count > 0:  # Only include categories with posts
            category_name = table_name.replace('_bookmarks', '').replace('_', ' ').title()
            categories[category_name] = table_name
    
    conn.close()
    return categories

def get_manual_review_posts():
    """Get posts that need manual review"""
    conn = get_database_connection()
    query = """
        SELECT post_id, platform, author, content, url, created_at, value_score,
               ai_summary, key_concepts, smart_tags, tech_score, business_score, research_score
        FROM manual_review_bookmarks
        ORDER BY value_score DESC, created_at DESC
    """
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        conn.close()
        return pd.DataFrame()

def get_posts_from_category(category: str, limit: int = 50):
    """Get posts from a specific category with full data"""
    conn = get_database_connection()
    table_name = f"{category.lower().replace(' ', '_')}_bookmarks"
    
    try:
        df = pd.read_sql_query(f"""
            SELECT post_id, platform, author, content, url, created_at, value_score,
                   ai_summary, key_concepts, smart_tags, tags
            FROM {table_name}
            ORDER BY COALESCE(value_score, 0) DESC, created_at DESC
            LIMIT {limit}
        """, conn)
        conn.close()
        return df
    except Exception as e:
        # Try alternative table names if the first one fails
        alternative_names = [
            f"{category.lower().replace(' ', '_')}_bookmarks",
            f"{category.lower()}_bookmarks",
            f"{category}_bookmarks"
        ]
        
        for alt_name in alternative_names:
            try:
                df = pd.read_sql_query(f"""
                    SELECT post_id, platform, author, content, url, created_at, value_score,
                           ai_summary, key_concepts, smart_tags, tags
                    FROM {alt_name}
                    ORDER BY COALESCE(value_score, 0) DESC, created_at DESC
                    LIMIT {limit}
                """, conn)
                conn.close()
                return df
            except:
                continue
        
        conn.close()
        return pd.DataFrame()

def move_post_to_category(post_id: str, target_category: str):
    """Move a post to a different category"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Get post data from manual review
        cursor.execute("""
            SELECT post_id, platform, author, content, url, created_at, value_score,
                   ai_summary, key_concepts, smart_tags
            FROM manual_review_bookmarks
            WHERE post_id = ?
        """, (post_id,))
        
        post_data = cursor.fetchone()
        if post_data:
            # Insert into target category
            target_table = f"{target_category.lower().replace(' ', '_')}_bookmarks"
            cursor.execute(f"""
                INSERT INTO {target_table} 
                (post_id, platform, author, content, url, created_at, value_score,
                 ai_summary, key_concepts, smart_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, post_data)
            
            # Remove from manual review
            cursor.execute("DELETE FROM manual_review_bookmarks WHERE post_id = ?", (post_id,))
            
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        conn.close()
        return False

def format_content(content, max_length=150):
    """Format content for display"""
    if len(content) > max_length:
        return content[:max_length] + "..."
    return content

def get_comments_for_post(post_id):
    """Get comments for a specific post"""
    try:
        # Check if we have comment data in the output directory
        comment_file = f"output/data/comments/{post_id}_comments.json"
        if os.path.exists(comment_file):
            with open(comment_file, 'r') as f:
                import json
                comments_data = json.load(f)
                return comments_data.get('comments', [])[:5]  # Return top 5 comments
        return []
    except Exception as e:
        return []

def create_streamlit_card(post, is_review=False):
    """Create a beautiful, modern card with platform-specific styling"""
    
    # Platform-specific styling with more prominent colors
    platform_config = {
        'twitter': {
            'icon': '🐦', 
            'bg_color': '#E3F2FD', 
            'border_color': '#1DA1F2', 
            'text_color': '#1DA1F2',
            'header_bg': '#1DA1F2'
        },
        'reddit': {
            'icon': '📱', 
            'bg_color': '#FFEBEE', 
            'border_color': '#FF4500', 
            'text_color': '#FF4500',
            'header_bg': '#FF4500'
        },
        'threads': {
            'icon': '🧵', 
            'bg_color': '#F5F5F5', 
            'border_color': '#000000', 
            'text_color': '#000000',
            'header_bg': '#000000'
        },
        'linkedin': {
            'icon': '💼', 
            'bg_color': '#E3F2FD', 
            'border_color': '#0077B5', 
            'text_color': '#0077B5',
            'header_bg': '#0077B5'
        }
    }
    
    platform = post['platform'].lower()
    platform_info = platform_config.get(platform, {
        'icon': '📱', 
        'bg_color': '#FFFFFF',  # Changed to pure white for better visibility
        'border_color': '#666666', 
        'text_color': '#333333',  # Darker text for better contrast
        'header_bg': '#666666'
    })
    
    # Score styling
    score = post['value_score'] if pd.notna(post['value_score']) else None
    if score is None:
        score_emoji = "❓"
        score_color = "#999999"
        score_display = "N/A"
    elif score >= 8.0:
        score_emoji = "🔥"
        score_color = "#00AA88"  # Darker green for better visibility
        score_display = f"{score:.1f}"
    elif score >= 6.0:
        score_emoji = "⭐"
        score_color = "#FF9900"  # Darker orange for better visibility
        score_display = f"{score:.1f}"
    else:
        score_emoji = "📝"
        score_color = "#CC0000"  # Darker red for better visibility
        score_display = f"{score:.1f}"
    
    # Create card with platform-specific styling
    with st.container():
        # Use Streamlit components to bypass theme
        try:
            import streamlit.components.v1 as components
            
            # Create the card HTML with forced styling
            card_html = f"""
            <style>
            .platform-card-{platform} {{
                background: {platform_info['bg_color']} !important;
                border-radius: 12px !important;
                padding: 20px !important;
                margin: 12px 0 !important;
                border: 2px solid {platform_info['border_color']} !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
                position: relative !important;
                overflow: hidden !important;
                transition: all 0.3s ease !important;
                color: #000000 !important;
            }}
            </style>
            <div class="platform-card-{platform}" style="
                background: {platform_info['bg_color']} !important;
                border-radius: 12px;
                padding: 20px;
                margin: 12px 0;
                border: 2px solid {platform_info['border_color']};
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
                color: #000000 !important;
            ">
            """
            
            # Add the card content
            card_html += f"""
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="
                            width: 40px; height: 40px; 
                            border-radius: 50%; 
                            background: {platform_info['header_bg']}; 
                            display: flex; align-items: center; justify-content: center; 
                            color: white; font-weight: bold; font-size: 16px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        ">
                            {post['author'][:1].upper() if post['author'] else "U"}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 16px; color: #000000; margin-bottom: 2px;">{post['author'] if post['author'] else "Unknown Author"}</div>
                            <div style="font-size: 13px; color: {platform_info['text_color']}; font-weight: 500;">{platform_info['icon']} {post['platform'].title()}</div>
                        </div>
                    </div>
                    <div style="
                        background: {score_color}20; 
                        color: {score_color}; 
                        border: 1px solid {score_color}60; 
                        border-radius: 20px; 
                        padding: 6px 12px; 
                        font-weight: 700; 
                        font-size: 14px; 
                        display: flex; 
                        align-items: center; 
                        gap: 4px;
                    ">
                        {score_emoji} {score_display}
                    </div>
                </div>
                
                <div style="margin: 15px 0; font-size: 15px; line-height: 1.5; color: #000000; font-weight: 400;">
                    {format_content(post['content'], 200)}
                </div>
            """
            
            # Add category if available
            if 'category' in post and pd.notna(post['category']):
                card_html += f"""
                <div style="
                    background: {platform_info['text_color']}20; 
                    color: {platform_info['text_color']}; 
                    border: 1px solid {platform_info['text_color']}40; 
                    border-radius: 8px; 
                    padding: 4px 10px; 
                    font-size: 12px; 
                    font-weight: 600; 
                    display: inline-block; 
                    margin-bottom: 12px;
                ">
                    🏷️ {post['category']}
                </div>
                """
            
            # Add tags
            tags_display = []
            if pd.notna(post.get('concepts')):
                concepts = post['concepts']
                if isinstance(concepts, str):
                    try:
                        concepts_list = ast.literal_eval(concepts)
                        tags_display.extend(concepts_list[:4])
                    except:
                        tags_display.append(concepts)
                else:
                    tags_display.append(str(concepts))
            
            if tags_display:
                card_html += '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0;">'
                for tag in tags_display:
                    card_html += f"""
                    <div style="
                        background: {platform_info['text_color']}15; 
                        color: {platform_info['text_color']}; 
                        border: 1px solid {platform_info['text_color']}30; 
                        border-radius: 6px; 
                        padding: 4px 10px; 
                        font-size: 12px; 
                        font-weight: 500;
                    ">
                        {tag}
                    </div>
                    """
                card_html += '</div>'
            
            card_html += '</div>'
            
            # Render using components
            components.html(card_html, height=300, scrolling=False)
            
        except Exception as e:
            # Fallback to regular markdown if components fail
            fallback_html = f"""
            <div style="
                background: {platform_info['bg_color']} !important;
                border-radius: 12px;
                padding: 20px;
                margin: 12px 0;
                border: 1px solid {platform_info['border_color']}40;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
                color: #000000 !important;
            ">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="
                            width: 40px; height: 40px; 
                            border-radius: 50%; 
                            background: {platform_info['header_bg']}; 
                            display: flex; align-items: center; justify-content: center; 
                            color: white; font-weight: bold; font-size: 16px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        ">
                            {post['author'][:1].upper() if post['author'] else "U"}
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 16px; color: #000000; margin-bottom: 2px;">{post['author'] if post['author'] else "Unknown Author"}</div>
                            <div style="font-size: 13px; color: {platform_info['text_color']}; font-weight: 500;">{platform_info['icon']} {post['platform'].title()}</div>
                        </div>
                    </div>
                    <div style="
                        background: {score_color}20; 
                        color: {score_color}; 
                        border: 1px solid {score_color}60; 
                        border-radius: 20px; 
                        padding: 6px 12px; 
                        font-weight: 700; 
                        font-size: 14px; 
                        display: flex; 
                        align-items: center; 
                        gap: 4px;
                    ">
                        {score_emoji} {score_display}
                    </div>
                </div>
                
                <div style="margin: 15px 0; font-size: 15px; line-height: 1.5; color: #000000; font-weight: 400;">
                    {format_content(post['content'], 200)}
                </div>
            """
            
            # Add tags to fallback version too
            tags_display = []
            if pd.notna(post.get('concepts')):
                concepts = post['concepts']
                if isinstance(concepts, str):
                    try:
                        concepts_list = ast.literal_eval(concepts)
                        tags_display.extend(concepts_list[:4])
                    except:
                        tags_display.append(concepts)
                else:
                    tags_display.append(str(concepts))
            
            if tags_display:
                fallback_html += '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0;">'
                for tag in tags_display:
                    fallback_html += f"""
                    <div style="
                        background: {platform_info['text_color']}15; 
                        color: {platform_info['text_color']}; 
                        border: 1px solid {platform_info['text_color']}30; 
                        border-radius: 6px; 
                        padding: 4px 10px; 
                        font-size: 12px; 
                        font-weight: 500;
                    ">
                        {tag}
                    </div>
                    """
                fallback_html += '</div>'
            
            fallback_html += '</div>'
            
            st.markdown(fallback_html, unsafe_allow_html=True)
        
        # Add action buttons using native Streamlit
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔗 Open", key=f"open_{post.get('id', post.get('post_id', 'unknown'))}"):
                import webbrowser
                webbrowser.open(post['url'])
        with col2:
            if st.button("📖 Full", key=f"full_{post.get('id', post.get('post_id', 'unknown'))}"):
                # Create a full-width container for the content
                st.markdown("---")
                st.markdown(f"### 📖 Full Content")
                st.markdown(f"**Author:** {post['author']} | **Platform:** {post['platform'].title()} | **Score:** {score_display}")
                st.markdown("---")
                st.markdown(post['content'])
                st.markdown("---")
        with col3:
            if st.button("💬 Comments", key=f"comments_{post.get('id', post.get('post_id', 'unknown'))}"):
                comments = get_comments_for_post(post.get('id', post.get('post_id', '')))
                if comments:
                    st.markdown("**Comments:**")
                    for comment in comments:
                        st.markdown(f"- {comment}")
                else:
                    st.info("Comments only available for Reddit posts")

def main():
    st.set_page_config(
        page_title="PrisMind",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Clean header
    st.title("🧠 PrisMind")
    st.caption("Your AI-powered knowledge base")
    
    # Get data
    counts = get_category_counts()
    
    # Simple sidebar
    st.sidebar.title("Navigation")
    
    # Quick stats
    total_posts = sum(counts.values())
    st.sidebar.metric("Total Posts", total_posts)
    
    # Navigation
    page = st.sidebar.radio(
        "Pages",
        ["🏠 Feed", "⚠️ Review", "📊 Browse", "🔍 Search"],
        label_visibility="collapsed"
    )
    
    if page == "🏠 Feed":
        show_feed(counts)
    elif page == "⚠️ Review":
        show_manual_review()
    elif page == "📊 Browse":
        show_browse_categories(counts)
    elif page == "🔍 Search":
        show_advanced_search(counts)

def show_feed(counts):
    """Show clean, filtered feed"""
    
    # Get available categories
    available_categories = get_available_categories()
    
    # Simple filters
    st.sidebar.markdown("### Filters")
    
    # Filter columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Category filter
        category_options = ["All"] + list(available_categories.keys())
        selected_category = st.sidebar.selectbox("Category", category_options)
    
    with col2:
        # Platform filter
        platform_options = ["All", "Twitter", "Reddit", "Threads"]
        selected_platform = st.sidebar.selectbox("Platform", platform_options)
    
    with col3:
        # Score filter
        min_score = st.sidebar.slider("Min Score", 0.0, 10.0, 0.0, 0.5)
    
    with col4:
        # Search
        search_term = st.sidebar.text_input("Search", placeholder="Search content...")
    
    # Get posts based on selected category
    if selected_category == "All":
        # Get posts from all categories
        all_posts = []
        for category_name, table_name in available_categories.items():
            category_key = table_name.replace('_bookmarks', '')
            posts = get_posts_from_category(category_key, 10)  # Reduced to avoid too many posts
            if not posts.empty:
                # Add category column for tracking
                posts['category'] = category_name
                all_posts.append(posts)
        
        if all_posts:
            posts_df = pd.concat(all_posts, ignore_index=True)
        else:
            posts_df = pd.DataFrame()
    else:
        # Get posts from specific category
        table_name = available_categories[selected_category]
        category_key = table_name.replace('_bookmarks', '')
        posts_df = get_posts_from_category(category_key, 200)  # Increased limit significantly
        if not posts_df.empty:
            posts_df['category'] = selected_category
    
    # Debug: Show what we got (only if needed)
    if st.sidebar.checkbox("Show Debug Info", value=False):
        st.sidebar.markdown("### Debug Info")
        st.sidebar.write(f"Category: {selected_category}")
        st.sidebar.write(f"Posts found: {len(posts_df) if not posts_df.empty else 0}")
        if not posts_df.empty:
            st.sidebar.write(f"Platforms: {list(posts_df['platform'].unique())}")
            st.sidebar.write(f"Score range: {posts_df['value_score'].min():.1f} - {posts_df['value_score'].max():.1f}")
    
    # Apply filters
    if not posts_df.empty:
        # Platform filter
        if selected_platform != "All":
            posts_df = posts_df[posts_df['platform'].str.lower() == selected_platform.lower()]
        
        # Score filter - handle NULL values
        if min_score > 0:
            # Only filter by score if min_score > 0, and handle NULL values
            posts_df = posts_df[(posts_df['value_score'] >= min_score) | (posts_df['value_score'].isna())]
        
        # Search filter
        if search_term:
            posts_df = posts_df[posts_df['content'].str.contains(search_term, case=False, na=False)]
        
        # Sort by score (put NULL values at the end)
        posts_df = posts_df.sort_values('value_score', ascending=False, na_position='last')
        
            # Display results with better info
        if not posts_df.empty:
            st.markdown(f"### 📊 {len(posts_df)} Posts Found")
            
            # Show category info if filtering by specific category
            if selected_category != "All":
                st.info(f"Showing posts from: **{selected_category}**")
            
            # Show filter info
            filter_info = []
            if selected_platform != "All":
                filter_info.append(f"Platform: {selected_platform}")
            if min_score > 0:
                filter_info.append(f"Min Score: {min_score}")
            if search_term:
                filter_info.append(f"Search: '{search_term}'")
            
            if filter_info:
                st.caption(f"Filters: {' | '.join(filter_info)}")
            
            # Display posts
            for idx, post in posts_df.head(20).iterrows():
                create_streamlit_card(post)
            
            # Show more info if there are more posts
            if len(posts_df) > 20:
                st.info(f"Showing first 20 of {len(posts_df)} posts. Use filters to narrow down results.")
        else:
            st.info("No posts match your filters")
    else:
        st.info("No posts found in selected category")

def show_manual_review():
    """Show manual review section with modern cards"""
    st.markdown("### ⚠️ Manual Review")
    st.markdown("Posts that need your attention and categorization")
    
    df = get_manual_review_posts()
    
    if df.empty:
        st.success("🎉 No posts need manual review!")
        return
    
    st.write(f"Showing {len(df)} posts that need review")
    
    # Advanced filters
    st.markdown("#### 🔍 Advanced Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        platform_filter = st.selectbox("Platform", ["All"] + list(df['platform'].unique()))
    with col2:
        score_filter = st.selectbox("Sort by", ["Value Score", "Tech Score", "Business Score", "Research Score"])
    with col3:
        search_term = st.text_input("Search content", "")
    with col4:
        min_score = st.slider("Min Value Score", 0.0, 10.0, 0.0, 0.5)
    
    # Apply filters
    filtered_df = df.copy()
    
    if platform_filter != "All":
        filtered_df = filtered_df[filtered_df['platform'] == platform_filter]
    
    if search_term:
        filtered_df = filtered_df[filtered_df['content'].str.contains(search_term, case=False, na=False)]
    
    filtered_df = filtered_df[filtered_df['value_score'] >= min_score]
    
    if score_filter == "Value Score":
        filtered_df = filtered_df.sort_values('value_score', ascending=False)
    elif score_filter == "Tech Score":
        filtered_df = filtered_df.sort_values('tech_score', ascending=False)
    elif score_filter == "Business Score":
        filtered_df = filtered_df.sort_values('business_score', ascending=False)
    elif score_filter == "Research Score":
        filtered_df = filtered_df.sort_values('research_score', ascending=False)
    
    st.write(f"Showing {len(filtered_df)} posts")
    
    # Display posts as modern cards
    for idx, row in filtered_df.iterrows():
        create_streamlit_card(row, is_review=True)
        
        # Categorization buttons
        st.markdown("**Move to Category:**")
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            if st.button("🖥️ Tech", key=f"tech_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'tech'):
                    st.success("Moved to Tech!")
                    st.rerun()
                else:
                    st.error("Failed to move post")
        
        with col_b:
            if st.button("💼 Business", key=f"bus_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'business'):
                    st.success("Moved to Business!")
                    st.rerun()
                else:
                    st.error("Failed to move post")
        
        with col_c:
            if st.button("🔬 Research", key=f"res_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'research'):
                    st.success("Moved to Research!")
                    st.rerun()
                else:
                    st.error("Failed to move post")
        
        with col_d:
            if st.button("🛠️ Tools", key=f"tools_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'tools_to_try'):
                    st.success("Moved to Tools!")
                    st.rerun()
                else:
                    st.error("Failed to move post")

def show_browse_categories(counts):
    """Show category browsing with modern cards"""
    st.markdown("### 📊 Browse by Category")
    
    # Group categories logically
    categories = {
        "Learning & Skills": ["Step By Step Tutorials", "Video Tutorials", "Code Examples", "Best Practices"],
        "Tools & Resources": ["Tools To Try", "Ai Tools", "Development Tools", "Productivity Tools"],
        "Business & Growth": ["Marketing Strategies", "Startup Advice", "Monetization Guides"],
        "Quick Wins": ["Quick Tips", "Time Savers", "Money Savers"]
    }
    
    selected_group = st.selectbox("Choose a category group:", list(categories.keys()))
    
    if selected_group:
        group_categories = categories[selected_group]
        available_categories = [cat for cat in group_categories if cat in counts and counts[cat] > 0]
        
        if available_categories:
            selected_category = st.selectbox("Choose a specific category:", available_categories)
            
            if selected_category:
                posts = get_posts_from_category(selected_category, limit=20)
                if not posts.empty:
                    st.markdown(f"**{selected_category} ({len(posts)} posts)**")
                    
                    # Advanced filters
                    st.markdown("#### 🔍 Filters")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        platform_filter = st.selectbox("Platform", ["All"] + list(posts['platform'].unique()), key="cat_platform")
                    with col2:
                        search_term = st.text_input("Search content", key="cat_search")
                    with col3:
                        min_score = st.slider("Min Value Score", 0.0, 10.0, 0.0, 0.5, key="cat_score")
                    
                    # Apply filters
                    filtered_posts = posts.copy()
                    if platform_filter != "All":
                        filtered_posts = filtered_posts[filtered_posts['platform'] == platform_filter]
                    if search_term:
                        filtered_posts = filtered_posts[filtered_posts['content'].str.contains(search_term, case=False, na=False)]
                    
                    # Score filter - handle NULL values
                    if min_score > 0:
                        filtered_posts = filtered_posts[(filtered_posts['value_score'] >= min_score) | (filtered_posts['value_score'].isna())]
                    
                    # Display as modern cards
                    st.markdown(f"**Showing {len(filtered_posts)} of {len(posts)} posts**")
                    for _, post in filtered_posts.iterrows():
                        create_streamlit_card(post)

def show_advanced_search(counts):
    """Show advanced search functionality"""
    st.markdown("### 🔍 Advanced Search")
    
    # Search across all categories
    search_term = st.text_input("Search across all content:", placeholder="Enter keywords...")
    
    # Advanced search options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_in = st.multiselect(
            "Search in:",
            ["Content", "AI Summary", "Key Concepts", "Smart Tags"],
            default=["Content", "AI Summary"]
        )
    
    with col2:
        min_score = st.slider("Minimum Value Score", 0.0, 10.0, 0.0, 0.5)
    
    with col3:
        platforms = st.multiselect(
            "Platforms:",
            ["Twitter", "Reddit", "Threads"],
            default=["Twitter", "Reddit", "Threads"]
        )
    
    if search_term:
        # Search in all tables
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
        tables = cursor.fetchall()
        
        all_results = []
        for table in tables:
            table_name = table[0]
            try:
                # Build search conditions
                search_conditions = []
                if "Content" in search_in:
                    search_conditions.append("content LIKE ?")
                if "AI Summary" in search_in:
                    search_conditions.append("ai_summary LIKE ?")
                if "Key Concepts" in search_in:
                    search_conditions.append("key_concepts LIKE ?")
                if "Smart Tags" in search_in:
                    search_conditions.append("smart_tags LIKE ?")
                
                if search_conditions:
                    where_clause = " OR ".join(search_conditions)
                    query = f"""
                        SELECT post_id, platform, author, content, url, value_score, ai_summary, key_concepts, smart_tags
                        FROM {table_name}
                        WHERE ({where_clause}) AND value_score >= ? AND platform IN ({','.join(['?'] * len(platforms))})
                        ORDER BY value_score DESC
                        LIMIT 10
                    """
                    
                    params = [f'%{search_term}%'] * len(search_conditions) + [min_score] + platforms
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    for result in results:
                        all_results.append({
                            'table': table_name,
                            'post_id': result[0],
                            'platform': result[1],
                            'author': result[2],
                            'content': result[3],
                            'url': result[4],
                            'value_score': result[5],
                            'ai_summary': result[6],
                            'key_concepts': result[7],
                            'smart_tags': result[8]
                        })
            except:
                continue
        
        conn.close()
        
        if all_results:
            st.write(f"Found {len(all_results)} results")
            
            # Sort by value score
            all_results.sort(key=lambda x: x['value_score'], reverse=True)
            
            # Display as modern cards
            for result in all_results:
                create_streamlit_card(result)
        else:
            st.info("No results found")

if __name__ == "__main__":
    main()