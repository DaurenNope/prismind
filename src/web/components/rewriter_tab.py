"""
Content Rewriter Tab - Rewrite content with different personas
"""

import streamlit as st
import json
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.services.content_rewriter import ContentRewriter
from src.supabase_manager import SupabaseManager


def render_rewriter_tab():
    """Render the content rewriter tab"""
    
    st.title("🎭 Content Rewriter")
    st.markdown("Transform content into different personas and styles")
    
    # Initialize services
    rewriter = ContentRewriter()
    supabase = SupabaseManager()
    
    # Tabs for different rewriter functions
    rewriter_mode = st.tabs(["✍️ Rewrite Posts", "📊 Queue Management", "⚙️ Personas"])
    
    # REWRITE POSTS TAB
    with rewriter_mode[0]:
        st.subheader("✍️ Rewrite Content")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            source_persona = st.selectbox(
                "Source Persona (optional)",
                ["All", "technical", "builder", "trendsetter"],
                help="Filter by content source persona"
            )
        
        with col2:
            category_filter = st.selectbox(
                "Category (optional)",
                ["All", "Technology", "Business", "Learning", "Innovation", "Tools"],
                help="Filter by content category"
            )
        
        with col3:
            min_value_score = st.slider(
                "Min Value Score",
                0, 10, 7,
                help="Only rewrite high-quality content"
            )
        
        st.markdown("---")
        
        # Target personas
        st.write("**Select Target Personas:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rewrite_technical = st.checkbox("🔧 Technical Expert", value=True)
            if rewrite_technical:
                st.caption("Deep technical analysis for engineers")
        
        with col2:
            rewrite_builder = st.checkbox("🚀 Startup Builder", value=True)
            if rewrite_builder:
                st.caption("Actionable insights for founders")
        
        with col3:
            rewrite_trendsetter = st.checkbox("🔥 Tech Trendsetter", value=False)
            if rewrite_trendsetter:
                st.caption("Hot takes for tech enthusiasts")
        
        st.markdown("---")
        
        # Batch settings
        col1, col2 = st.columns(2)
        
        with col1:
            batch_size = st.number_input(
                "Batch Size",
                min_value=1,
                max_value=50,
                value=10,
                help="Number of posts to rewrite in this batch"
            )
        
        with col2:
            st.write("")
            st.write("")
            skip_rewrites = st.checkbox(
                "Skip already rewritten",
                value=True,
                help="Skip posts that already have rewrites"
            )
        
        # Preview what will be rewritten
        if st.button("🔍 Preview Batch", type="secondary"):
            with st.spinner("Loading posts..."):
                # Build query
                query = supabase.client.table('posts')\
                    .select('id, content, author, category, value_score, metadata, created_at')\
                    .eq('is_saved', True)\
                    .gte('value_score', min_value_score)\
                    .order('created_at', desc=True)\
                    .limit(batch_size)
                
                # Apply filters
                if category_filter != "All":
                    query = query.eq('category', category_filter)
                
                posts = query.execute()
                
                if posts.data:
                    st.success(f"Found {len(posts.data)} posts to rewrite")
                    
                    # Show preview
                    with st.expander("📄 Preview Posts"):
                        for i, post in enumerate(posts.data[:5], 1):
                            st.write(f"**{i}. {post.get('author', 'Unknown')}** - Score: {post.get('value_score', 0)}/10")
                            st.write(post.get('content', '')[:150] + '...')
                            st.caption(f"Category: {post.get('category', 'N/A')}")
                            st.markdown("---")
                        
                        if len(posts.data) > 5:
                            st.info(f"...and {len(posts.data) - 5} more posts")
                else:
                    st.warning("No posts found matching the filters")
        
        st.markdown("---")
        
        # Rewrite button
        if st.button("🎭 Start Rewriting", type="primary"):
            # Collect target personas
            target_personas = []
            if rewrite_technical:
                target_personas.append('technical')
            if rewrite_builder:
                target_personas.append('builder')
            if rewrite_trendsetter:
                target_personas.append('trendsetter')
            
            if not target_personas:
                st.error("Please select at least one target persona")
            else:
                with st.spinner(f"Rewriting {batch_size} posts into {len(target_personas)} personas..."):
                    # Build query
                    query = supabase.client.table('posts')\
                        .select('*')\
                        .eq('is_saved', True)\
                        .gte('value_score', min_value_score)\
                        .order('created_at', desc=True)\
                        .limit(batch_size)
                    
                    if category_filter != "All":
                        query = query.eq('category', category_filter)
                    
                    posts = query.execute()
                    
                    if not posts.data:
                        st.warning("No posts found to rewrite")
                    else:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        total_posts = len(posts.data)
                        rewrites_created = 0
                        errors = 0
                        
                        for i, post in enumerate(posts.data):
                            status_text.text(f"Processing {i+1}/{total_posts}: {post.get('author', 'Unknown')}")
                            
                            content = post.get('content', '')
                            post_id = post.get('id')
                            
                            # Get original metadata
                            metadata = {}
                            if post.get('metadata'):
                                try:
                                    metadata = json.loads(post['metadata'])
                                except:
                                    pass
                            
                            # Rewrite for each persona
                            for persona in target_personas:
                                try:
                                    # Check if already rewritten
                                    if skip_rewrites:
                                        existing = supabase.client.table('rewritten_posts')\
                                            .select('id')\
                                            .eq('original_post_id', post_id)\
                                            .eq('persona', persona)\
                                            .execute()
                                        
                                        if existing.data:
                                            continue
                                    
                                    # Rewrite
                                    rewritten = rewriter.rewrite_for_persona(
                                        content=content,
                                        persona=persona,
                                        original_context={
                                            'author': post.get('author'),
                                            'category': post.get('category'),
                                            'tags': post.get('smart_tags', [])
                                        }
                                    )
                                    
                                    # Save rewritten content
                                    rewrite_data = {
                                        'original_post_id': post_id,
                                        'persona': persona,
                                        'content': rewritten,
                                        'target_niche': metadata.get('target_niche', ''),
                                        'status': 'ready',
                                        'metadata': json.dumps({
                                            'original_author': post.get('author'),
                                            'original_category': post.get('category'),
                                            'value_score': post.get('value_score'),
                                            'source_platform': post.get('platform')
                                        })
                                    }
                                    
                                    supabase.client.table('rewritten_posts').insert(rewrite_data).execute()
                                    rewrites_created += 1
                                
                                except Exception as e:
                                    errors += 1
                                    st.error(f"Error rewriting post {post_id} for {persona}: {e}")
                            
                            progress_bar.progress((i + 1) / total_posts)
                        
                        status_text.empty()
                        progress_bar.empty()
                        
                        st.success(f"✅ Created {rewrites_created} rewrites from {total_posts} posts")
                        
                        if errors:
                            st.warning(f"⚠️ {errors} errors occurred")
    
    # QUEUE MANAGEMENT TAB
    with rewriter_mode[1]:
        st.subheader("📊 Rewrite Queue")
        
        # Get statistics
        total_rewrites = supabase.client.table('rewritten_posts').select('id', count='exact').execute()
        ready_rewrites = supabase.client.table('rewritten_posts').select('id', count='exact').eq('status', 'ready').execute()
        posted_rewrites = supabase.client.table('rewritten_posts').select('id', count='exact').eq('status', 'posted').execute()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Rewrites", total_rewrites.count if hasattr(total_rewrites, 'count') else 0)
        with col2:
            st.metric("Ready to Post", ready_rewrites.count if hasattr(ready_rewrites, 'count') else 0)
        with col3:
            st.metric("Posted", posted_rewrites.count if hasattr(posted_rewrites, 'count') else 0)
        
        st.markdown("---")
        
        # Filter by persona
        persona_filter = st.selectbox(
            "Filter by Persona",
            ["All", "technical", "builder", "trendsetter"]
        )
        
        # Load rewrites
        query = supabase.client.table('rewritten_posts')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(20)
        
        if persona_filter != "All":
            query = query.eq('persona', persona_filter)
        
        rewrites = query.execute()
        
        if rewrites.data:
            st.write(f"**Showing {len(rewrites.data)} rewrites:**")
            
            for rewrite in rewrites.data:
                persona_emoji = {'technical': '🔧', 'builder': '🚀', 'trendsetter': '🔥'}.get(rewrite['persona'], '🎭')
                status_emoji = {'ready': '✅', 'posted': '📤', 'scheduled': '⏰'}.get(rewrite.get('status', 'ready'), '❓')
                
                with st.expander(f"{persona_emoji} {rewrite['persona'].title()} - {status_emoji} {rewrite.get('status', 'ready').title()}"):
                    st.write(rewrite['content'])
                    st.caption(f"Created: {rewrite.get('created_at', 'N/A')}")
                    st.caption(f"Target: {rewrite.get('target_niche', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Delete", key=f"del_{rewrite['id']}"):
                            supabase.client.table('rewritten_posts').delete().eq('id', rewrite['id']).execute()
                            st.rerun()
                    with col2:
                        if rewrite.get('status') != 'posted':
                            if st.button("✅ Mark Posted", key=f"post_{rewrite['id']}"):
                                supabase.client.table('rewritten_posts').update({'status': 'posted'}).eq('id', rewrite['id']).execute()
                                st.rerun()
        else:
            st.info("No rewrites found")
    
    # PERSONAS TAB
    with rewriter_mode[2]:
        st.subheader("⚙️ Persona Configuration")
        
        personas = {
            'technical': {
                'emoji': '🔧',
                'name': 'Technical Expert',
                'niche': 'AI/ML Engineers, Developers',
                'style': 'Deep technical analysis, code examples, architecture discussions',
                'tone': 'Professional, detailed, precise'
            },
            'builder': {
                'emoji': '🚀',
                'name': 'Startup Builder',
                'niche': 'Entrepreneurs, Founders, Product Managers',
                'style': 'Actionable insights, business value, growth strategies',
                'tone': 'Practical, motivational, results-focused'
            },
            'trendsetter': {
                'emoji': '🔥',
                'name': 'Tech Trendsetter',
                'niche': 'Tech Enthusiasts, Early Adopters, Innovators',
                'style': 'What\'s hot, future trends, bold predictions',
                'tone': 'Energetic, forward-thinking, conversational'
            }
        }
        
        for persona_key, persona_info in personas.items():
            with st.expander(f"{persona_info['emoji']} {persona_info['name']}"):
                st.write(f"**Target Niche:** {persona_info['niche']}")
                st.write(f"**Writing Style:** {persona_info['style']}")
                st.write(f"**Tone:** {persona_info['tone']}")
                
                # Get stats for this persona
                persona_rewrites = supabase.client.table('rewritten_posts')\
                    .select('id', count='exact')\
                    .eq('persona', persona_key)\
                    .execute()
                
                st.metric("Total Rewrites", persona_rewrites.count if hasattr(persona_rewrites, 'count') else 0)


if __name__ == "__main__":
    render_rewriter_tab()
