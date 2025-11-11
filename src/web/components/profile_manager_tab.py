"""
Profile Manager Tab

UI for managing profile configurations for the content pipeline.
Allows creating, editing, and testing profile configs from the web interface.
"""

import streamlit as st
import json
from pathlib import Path
from src.services.profile_content_pipeline import ProfileContentPipeline, list_available_profiles

def render_profile_manager_tab():
    """Render the Profile Manager tab"""

    st.header("⚙️ Profile Manager")
    st.markdown("Configure content pipeline settings for each profile/persona")

    # Load available profiles
    profiles = list_available_profiles()

    if not profiles:
        profile_options = []
    else:
        profile_options = [p['profile_key'] for p in profiles]

    # Header with Create button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### Your Profiles")
    with col2:
        if st.button("➕ Create New Profile", type="primary"):
            st.session_state.creating_new_profile = True
            st.rerun()

    st.divider()

    # Main area: Show new profile form OR profile editor
    if st.session_state.get('creating_new_profile', False):
        render_new_profile_form()
    elif profiles:
        # Show existing profiles in a nice grid
        if profiles:
            st.markdown("**Existing Profiles:**")
            cols = st.columns(3)
            for idx, profile in enumerate(profiles):
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"**{profile['display_name']}**")
                        st.caption(f"{profile['profile_key']}")
                        st.caption(f"Platforms: {', '.join(profile['enabled_platforms'])}")

        st.divider()

        selected_profile = st.selectbox(
            "Select Profile to Edit",
            options=profile_options,
            format_func=lambda key: next(
                (p['display_name'] for p in profiles if p['profile_key'] == key),
                key
            )
        )

        if selected_profile:
            render_profile_editor(selected_profile)
    else:
        st.info("No profiles found. Click '➕ Create New Profile' above to get started.")


def render_profile_editor(profile_key: str):
    """Render the profile editor interface"""

    try:
        pipeline = ProfileContentPipeline(profile_key)
        config = pipeline.config
    except Exception as e:
        st.error(f"Error loading profile: {e}")
        return

    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Basic Info",
        "🌐 Platforms",
        "📝 Prompts",
        "🔀 Content Routing",
        "🧪 Test Pipeline"
    ])

    with tab1:
        render_basic_info_section(config, profile_key)

    with tab2:
        render_platforms_section(config, profile_key)

    with tab3:
        render_prompts_section(config, profile_key)

    with tab4:
        render_routing_section(config, profile_key)

    with tab5:
        render_test_section(pipeline)


def render_basic_info_section(config: dict, profile_key: str):
    """Render basic profile information section"""

    st.subheader("Basic Information")

    col1, col2 = st.columns(2)

    with col1:
        display_name = st.text_input(
            "Display Name",
            value=config.get('display_name', ''),
            key=f"{profile_key}_display_name"
        )

    with col2:
        key_input = st.text_input(
            "Profile Key",
            value=config.get('profile_key', ''),
            disabled=True,
            help="Cannot be changed after creation"
        )

    description = st.text_area(
        "Description",
        value=config.get('description', ''),
        key=f"{profile_key}_description",
        height=100
    )

    st.divider()

    st.subheader("Voice Guidelines")

    general_voice = st.text_area(
        "General Voice/Style",
        value=config.get('voice_guidelines', {}).get('general', ''),
        key=f"{profile_key}_voice_general",
        height=100,
        help="Overall voice and style guidelines"
    )

    col1, col2 = st.columns(2)

    with col1:
        russian_voice = st.text_area(
            "Russian Voice",
            value=config.get('voice_guidelines', {}).get('russian', ''),
            key=f"{profile_key}_voice_russian",
            height=80
        )

    with col2:
        english_voice = st.text_area(
            "English Voice",
            value=config.get('voice_guidelines', {}).get('english', ''),
            key=f"{profile_key}_voice_english",
            height=80
        )

    if st.button("💾 Save Basic Info", key=f"{profile_key}_save_basic"):
        updated_config = config.copy()
        updated_config['display_name'] = display_name
        updated_config['description'] = description
        updated_config['voice_guidelines'] = {
            'general': general_voice,
            'russian': russian_voice,
            'english': english_voice
        }
        save_profile_config(profile_key, updated_config)
        st.success("✅ Saved!")


def render_platforms_section(config: dict, profile_key: str):
    """Render platforms configuration section"""

    st.subheader("Platform Settings")

    platforms_config = config.get('platforms', {})

    # Available platforms
    available_platforms = ['twitter', 'threads', 'telegram', 'instagram', 'linkedin']

    for platform in available_platforms:
        with st.expander(f"📱 {platform.title()}", expanded=platform in platforms_config):
            platform_settings = platforms_config.get(platform, {})

            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                enabled = st.checkbox(
                    "Enabled",
                    value=platform_settings.get('enabled', False),
                    key=f"{profile_key}_{platform}_enabled"
                )

            with col2:
                language = st.selectbox(
                    "Language",
                    options=['en', 'ru'],
                    index=0 if platform_settings.get('language', 'en') == 'en' else 1,
                    key=f"{profile_key}_{platform}_language"
                )

            with col3:
                frequency = st.selectbox(
                    "Post Frequency",
                    options=['daily', '2-3x_daily', '3x_weekly', 'weekly'],
                    index=['daily', '2-3x_daily', '3x_weekly', 'weekly'].index(
                        platform_settings.get('post_frequency', 'daily')
                    ) if platform_settings.get('post_frequency') in ['daily', '2-3x_daily', '3x_weekly', 'weekly'] else 0,
                    key=f"{profile_key}_{platform}_frequency"
                )

            st.markdown("**Content Types**")
            content_types_input = st.text_input(
                "Supported content types (comma-separated)",
                value=', '.join(platform_settings.get('content_types', [])),
                key=f"{profile_key}_{platform}_content_types",
                help="e.g., tech_news, tool_review, breaking_news"
            )

            st.markdown("**Format Preferences**")
            format_prefs = platform_settings.get('format_preferences', {})

            col1, col2 = st.columns(2)

            with col1:
                max_length = st.number_input(
                    "Max Length",
                    value=format_prefs.get('max_length', 500),
                    min_value=100,
                    max_value=4096,
                    key=f"{profile_key}_{platform}_max_length"
                )

                use_emojis = st.checkbox(
                    "Use Emojis",
                    value=format_prefs.get('use_emojis', False),
                    key=f"{profile_key}_{platform}_use_emojis"
                )

            with col2:
                use_markdown = st.checkbox(
                    "Use Markdown",
                    value=format_prefs.get('use_markdown', False),
                    key=f"{profile_key}_{platform}_use_markdown"
                )

                use_hashtags = st.checkbox(
                    "Use Hashtags",
                    value=format_prefs.get('use_hashtags', False),
                    key=f"{profile_key}_{platform}_use_hashtags"
                )

    if st.button("💾 Save Platform Settings", key=f"{profile_key}_save_platforms"):
        st.info("Platform settings saved! (Save functionality to be implemented)")


def render_prompts_section(config: dict, profile_key: str):
    """Render prompt templates section"""

    st.subheader("Prompt Templates")

    st.markdown("""
    Prompt templates use placeholders that get filled with actual content:
    - `{profile_name}` - Profile display name
    - `{source_content}` - Original post content
    - `{category}` - Content category
    - `{topics}` - Topics list
    - `{voice_russian}` / `{voice_english}` - Voice guidelines
    """)

    prompt_templates = config.get('prompt_templates', {})

    if not prompt_templates:
        st.info("No prompt templates defined. Add your first template below.")

    # Group by platform
    templates_by_platform = {}
    for template_key in prompt_templates.keys():
        platform = template_key.split('_')[0]
        if platform not in templates_by_platform:
            templates_by_platform[platform] = []
        templates_by_platform[platform].append(template_key)

    for platform, template_keys in templates_by_platform.items():
        with st.expander(f"📝 {platform.title()} Templates ({len(template_keys)})", expanded=False):
            for template_key in template_keys:
                st.markdown(f"**`{template_key}`**")
                template_content = st.text_area(
                    "Template",
                    value=prompt_templates[template_key],
                    height=200,
                    key=f"{profile_key}_prompt_{template_key}",
                    label_visibility="collapsed"
                )

    st.divider()

    st.markdown("**Add New Template**")
    col1, col2, col3 = st.columns(3)

    with col1:
        new_platform = st.selectbox("Platform", options=['twitter', 'threads', 'telegram'], key=f"{profile_key}_new_prompt_platform")

    with col2:
        new_language = st.selectbox("Language", options=['en', 'ru'], key=f"{profile_key}_new_prompt_language")

    with col3:
        new_content_type = st.text_input("Content Type", placeholder="tech_news", key=f"{profile_key}_new_prompt_type")

    new_template = st.text_area(
        "Prompt Template",
        height=250,
        placeholder="You are {profile_name}...",
        key=f"{profile_key}_new_prompt_content"
    )

    if st.button("➕ Add Template", key=f"{profile_key}_add_prompt"):
        if new_content_type and new_template:
            template_key = f"{new_platform}_{new_language}_{new_content_type}"
            st.success(f"✅ Added template: {template_key}")
        else:
            st.error("Please fill in all fields")


def render_routing_section(config: dict, profile_key: str):
    """Render content routing section"""

    st.subheader("Content Routing Rules")

    st.markdown("""
    Define which platforms to use based on time sensitivity.
    Content will be routed to platforms in priority order.
    """)

    routing_config = config.get('content_routing', {})

    time_windows = ['same-day', '24-72h', 'this-week', 'evergreen']

    for window in time_windows:
        with st.expander(f"⏰ {window.title()}", expanded=True):
            window_config = routing_config.get(window, {})

            platforms = st.multiselect(
                "Platforms",
                options=['twitter', 'threads', 'telegram', 'instagram', 'linkedin'],
                default=window_config.get('platforms', []),
                key=f"{profile_key}_routing_{window}_platforms",
                help="Select platforms in priority order"
            )

            if platforms:
                st.caption(f"Priority order: {' → '.join(platforms)}")

    if st.button("💾 Save Routing Rules", key=f"{profile_key}_save_routing"):
        st.info("Routing rules saved! (Save functionality to be implemented)")


def render_test_section(pipeline: ProfileContentPipeline):
    """Render pipeline testing section"""

    st.subheader("Test Pipeline")

    # Pipeline summary
    summary = pipeline.get_pipeline_summary()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Profile", summary['profile_name'])

    with col2:
        st.metric("Enabled Platforms", len(summary['enabled_platforms']))

    with col3:
        st.metric("Prompt Templates", summary['total_prompt_templates'])

    st.divider()

    st.markdown("**Test Content Routing**")

    test_window = st.selectbox(
        "Time Sensitivity",
        options=['same-day', '24-72h', 'this-week', 'evergreen']
    )

    if st.button("🧪 Test Routing"):
        platforms = pipeline.route_content(test_window)
        st.success(f"✅ {test_window} content routes to: {' → '.join(platforms)}")

    st.divider()

    st.markdown("**Test Prompt Selection**")

    col1, col2 = st.columns(2)

    with col1:
        test_platform = st.selectbox("Platform", options=pipeline.get_enabled_platforms())

    with col2:
        content_types = pipeline.get_content_types_for_platform(test_platform)
        test_content_type = st.selectbox("Content Type", options=content_types if content_types else ["No types defined"])

    if st.button("🧪 Test Prompt Selection"):
        if content_types:
            template = pipeline.select_prompt_template(test_platform, test_content_type)
            if template:
                st.success("✅ Prompt template found!")
                with st.expander("View Template"):
                    st.code(template[:500] + "..." if len(template) > 500 else template)
            else:
                st.error("❌ No template found for this combination")
        else:
            st.warning("No content types defined for this platform")


def render_new_profile_form():
    """Render form for creating a new profile"""

    st.divider()
    st.subheader("➕ Create New Profile")

    col1, col2 = st.columns(2)

    with col1:
        new_profile_key = st.text_input(
            "Profile Key",
            placeholder="e.g., johndoe",
            help="Lowercase, no spaces, used in filenames"
        )

    with col2:
        new_display_name = st.text_input(
            "Display Name",
            placeholder="e.g., John Doe"
        )

    new_description = st.text_area(
        "Description",
        placeholder="Brief description of this profile's focus and style"
    )

    col1, col2 = st.columns(2)

    if col1.button("✅ Create Profile"):
        if new_profile_key and new_display_name:
            # Create minimal config
            new_config = {
                "profile_key": new_profile_key,
                "display_name": new_display_name,
                "description": new_description,
                "platforms": {},
                "content_routing": {},
                "source_preferences": {},
                "voice_guidelines": {},
                "prompt_templates": {}
            }

            save_profile_config(new_profile_key, new_config)
            st.success(f"✅ Created profile: {new_display_name}")
            st.session_state.creating_new_profile = False
            st.rerun()
        else:
            st.error("Please fill in Profile Key and Display Name")

    if col2.button("❌ Cancel"):
        st.session_state.creating_new_profile = False
        st.rerun()


def save_profile_config(profile_key: str, config: dict):
    """Save profile configuration to JSON file"""
    config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'profiles' / f'{profile_key}.json'

    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
