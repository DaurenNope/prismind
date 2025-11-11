"""
AI Profile Wizard Tab

Beautiful, conversational interface for creating profiles with AI assistance.
This is the "sellable feature" that makes profile setup accessible to non-technical users.
"""

import streamlit as st
import asyncio
from pathlib import Path
import json
from src.services.profile_wizard import ProfileWizard, WizardState
from src.services.rewrite_angle_suggester import RewriteAngleSuggester


def render_profile_wizard_tab():
    """Render the AI Profile Wizard interface"""

    st.header("🧙 AI Profile Wizard")
    st.markdown("Let AI guide you through creating the perfect social media profile in just 10 minutes.")

    # Initialize wizard state
    if 'wizard_state' not in st.session_state:
        st.session_state.wizard_state = WizardState()
        st.session_state.wizard_messages = []
        st.session_state.wizard_active = False

    state = st.session_state.wizard_state

    # Welcome screen or active wizard
    if not st.session_state.wizard_active:
        render_wizard_welcome()
    else:
        render_wizard_conversation(state)


def render_wizard_welcome():
    """Render the wizard welcome/start screen"""

    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px; border-radius: 15px; text-align: center; margin: 20px 0;">
        <h2 style="color: white; margin: 0;">✨ Create Your Profile with AI</h2>
        <p style="color: rgba(255,255,255,0.9); font-size: 18px; margin: 20px 0;">
            I'll ask you a few simple questions about your project, and generate a complete
            social media profile configuration automatically.
        </p>
        <p style="color: rgba(255,255,255,0.8); font-size: 16px;">
            ⏱️ Takes about 10 minutes • 💬 Conversational • 🎯 No technical knowledge needed
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # What you'll get
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📝 Voice & Style
        - Custom voice guidelines
        - Tone preferences
        - Example-based learning
        - Natural language
        """)

    with col2:
        st.markdown("""
        ### 🎯 Content Topics
        - 50-100 topic ideas
        - Niche-specific
        - Auto-generated
        - Ready to use
        """)

    with col3:
        st.markdown("""
        ### 🚀 Platform Setup
        - Multi-platform support
        - Posting frequencies
        - Format preferences
        - Reply strategies
        """)

    st.divider()

    # Start button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Start Wizard", type="primary", use_container_width=True):
            st.session_state.wizard_active = True
            st.session_state.wizard_messages = [{
                "role": "assistant",
                "content": "Hi! I'm here to help you set up your social media profile. Let's start with the basics.\n\n**What's your project about? Tell me what you're building.**"
            }]
            st.rerun()


def render_wizard_conversation(state: WizardState):
    """Render the conversational wizard interface"""

    # Progress indicator
    render_progress_bar(state.step)

    st.divider()

    # Chat history
    for msg in st.session_state.wizard_messages:
        if msg['role'] == 'assistant':
            with st.chat_message("assistant", avatar="🧙"):
                st.markdown(msg['content'])
        else:
            with st.chat_message("user"):
                st.markdown(msg['content'])

    # Input area
    st.divider()

    col1, col2 = st.columns([5, 1])

    with col1:
        user_input = st.text_area(
            "Your response:",
            height=100,
            key=f"wizard_input_{len(st.session_state.wizard_messages)}",
            placeholder="Type your answer here..."
        )

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing

        if st.button("Send", type="primary", use_container_width=True):
            if user_input.strip():
                asyncio.run(process_wizard_input(user_input, state))
                st.rerun()

        if st.button("Cancel", use_container_width=True):
            st.session_state.wizard_active = False
            st.session_state.wizard_state = WizardState()
            st.session_state.wizard_messages = []
            st.rerun()

    # Show extracted data (collapsible)
    with st.expander("🔍 Extracted Data (Debug)"):
        st.json(state.__dict__)


def render_progress_bar(step: int):
    """Render a visual progress bar for the wizard steps"""

    steps = [
        {"num": 1, "label": "Project Info"},
        {"num": 2, "label": "Voice & Style"},
        {"num": 3, "label": "Platforms"},
        {"num": 4, "label": "Engagement"},
        {"num": 5, "label": "Generate"}
    ]

    cols = st.columns(len(steps))

    for i, step_info in enumerate(steps):
        with cols[i]:
            if step_info["num"] < step:
                # Completed
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 40px; height: 40px; border-radius: 50%;
                                background: #10b981; color: white;
                                display: inline-flex; align-items: center; justify-content: center;
                                font-weight: bold; margin-bottom: 5px;">
                        ✓
                    </div>
                    <div style="font-size: 12px; color: #10b981; font-weight: 600;">
                        {step_info["label"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif step_info["num"] == step:
                # Current
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 40px; height: 40px; border-radius: 50%;
                                background: #3b82f6; color: white;
                                display: inline-flex; align-items: center; justify-content: center;
                                font-weight: bold; margin-bottom: 5px;">
                        {step_info["num"]}
                    </div>
                    <div style="font-size: 12px; color: #3b82f6; font-weight: 600;">
                        {step_info["label"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Pending
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 40px; height: 40px; border-radius: 50%;
                                background: #e5e7eb; color: #9ca3af;
                                display: inline-flex; align-items: center; justify-content: center;
                                font-weight: bold; margin-bottom: 5px;">
                        {step_info["num"]}
                    </div>
                    <div style="font-size: 12px; color: #9ca3af;">
                        {step_info["label"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)


async def process_wizard_input(user_input: str, state: WizardState):
    """Process user input and update wizard state"""

    # Add user message to history
    st.session_state.wizard_messages.append({
        "role": "user",
        "content": user_input
    })

    # Show thinking indicator
    with st.spinner("🤔 Thinking..."):
        wizard = ProfileWizard()

        # Special handling for each step
        if state.step == 1:
            await handle_step_1(user_input, state, wizard)
        elif state.step == 2:
            await handle_step_2(user_input, state, wizard)
        elif state.step == 3:
            await handle_step_3(user_input, state, wizard)
        elif state.step == 4:
            await handle_step_4(user_input, state, wizard)

        # Check if all steps are complete
        if state.step > 4:
            # Generate the final profile config
            await generate_final_profile(state, wizard)


async def handle_step_1(user_input: str, state: WizardState, wizard: ProfileWizard):
    """Handle step 1: Project information"""

    # Simple state tracking for multi-question step
    if not state.project_description:
        state.project_description = user_input
        response = "Great! Now, **who are you trying to reach? Describe your target audience.**"
    elif not state.target_audience:
        state.target_audience = user_input
        response = "Perfect! Last question for this section: **What makes you different? What's your unique angle or value proposition?**"
    elif not state.unique_value:
        state.unique_value = user_input
        # Extract project name
        state.project_name = extract_project_name(state.project_description)
        state.step = 2
        response = """Awesome! I've got a good sense of your project.

Now let's define your voice and style. **How do you want to sound?**

Pick any that resonate with you:
- 🎯 Technical
- 💬 Casual
- 👔 Professional
- ⚡ Edgy
- 📊 Data-driven
- 📖 Storyteller
- 😄 Memey
- 🎓 Serious

You can pick multiple! Just list them out."""
    else:
        state.step = 2
        response = "Let's move on to voice and style!"

    st.session_state.wizard_messages.append({
        "role": "assistant",
        "content": response
    })


async def handle_step_2(user_input: str, state: WizardState, wizard: ProfileWizard):
    """Handle step 2: Voice & style"""

    if not state.tone_tags:
        # Extract tone tags from user input
        available_tones = ["technical", "casual", "professional", "edgy",
                          "data-driven", "storyteller", "memey", "serious"]
        state.tone_tags = [tone for tone in available_tones if tone.lower() in user_input.lower()]

        response = """Got it! Now, **share 2-3 example posts you like from other accounts.**

You can paste URLs or just the text of posts that match the vibe you're going for."""

    elif len(state.example_posts) < 2:
        state.example_posts.append(user_input)

        if len(state.example_posts) >= 2:
            response = """Perfect! Last question: **What should you NEVER sound like?**

Think: corporate jargon, hype language, overly formal tone, etc."""
        else:
            response = "Great example! Share one or two more if you have them."

    else:
        # Extract things to avoid
        state.avoid_phrases = [phrase.strip() for phrase in user_input.split(',')]
        state.voice_description = f"Voice should be {', '.join(state.tone_tags)}. Avoid {', '.join(state.avoid_phrases)}."

        # Transition to angle suggestion step
        response = """Excellent! I've got your voice locked in.

🔍 **Now let me analyze your collected posts and suggest the best rewrite angles for you...**

This will take about 10 seconds."""

        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": response
        })

        # Trigger angle analysis
        await show_angle_suggestions(state)

        # Move to platforms step
        state.step = 3


async def handle_step_3(user_input: str, state: WizardState, wizard: ProfileWizard):
    """Handle step 3: Platforms & content"""

    if not state.platforms:
        # Extract platforms
        available_platforms = ["twitter", "threads", "linkedin", "telegram", "instagram"]
        state.platforms = [p for p in available_platforms if p.lower() in user_input.lower()]

        if not state.platforms:
            response = "I didn't catch which platforms you want to use. Please list them: Twitter, Threads, LinkedIn, Telegram, or Instagram."
        else:
            # Ask about frequency for first platform
            response = f"""Great! You selected: {', '.join([p.title() for p in state.platforms])}

**How often do you want to post on {state.platforms[0].title()}?**

Options:
- Daily
- 2-3x daily
- Few times a week
- Weekly"""

    elif len(state.platform_frequencies) < len(state.platforms):
        # Record frequency for current platform
        current_idx = len(state.platform_frequencies)
        state.platform_frequencies[state.platforms[current_idx]] = user_input

        if current_idx + 1 < len(state.platforms):
            # Ask about next platform
            next_platform = state.platforms[current_idx + 1]
            response = f"Got it! **How about {next_platform.title()}? How often there?**"
        else:
            # All frequencies collected, ask about topics
            response = f"""Perfect! Now, **what topics should I write about for you?**

Based on your project ({state.project_description}), I can generate 50-100 topic ideas.

But first, give me 5-10 topics to get started. Just list them out."""

    elif not state.content_topics:
        # Extract initial topics
        topics = [t.strip() for t in user_input.replace('\n', ',').split(',') if t.strip()]
        state.content_topics = topics
        state.step = 4

        response = """Awesome! I'll expand those into a full content calendar.

Final step! **Do you want to automatically reply to relevant conversations in your niche?**

This helps with engagement and growing your audience. Yes or no?"""

    st.session_state.wizard_messages.append({
        "role": "assistant",
        "content": response
    })


async def handle_step_4(user_input: str, state: WizardState, wizard: ProfileWizard):
    """Handle step 4: Engagement strategy"""

    state.auto_reply = "yes" in user_input.lower()

    if state.auto_reply and not state.reply_strategy:
        response = """Great! **What types of posts should I reply to?**

For example:
- Questions about [your topic]
- Discussions about [competitors]
- People asking for recommendations
- Industry news and trends

Describe what's relevant for your niche."""

        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": response
        })

    else:
        if state.auto_reply and user_input:
            state.reply_strategy = user_input

        state.step = 5

        # Show generating message
        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": "🎉 **Perfect! I have everything I need.**\n\nGenerating your complete profile configuration... This will take about 30 seconds."
        })


async def generate_final_profile(state: WizardState, wizard: ProfileWizard):
    """Generate the final profile configuration and save it"""

    try:
        # Generate config using AI
        config = await wizard.generate_profile_config(state)

        # Save to file
        profile_key = config['profile_key']
        config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'profiles' / f'{profile_key}.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # Success message with summary
        success_msg = f"""✅ **Profile Created Successfully!**

**Profile:** {config['display_name']} (`{profile_key}`)

**Platforms:** {', '.join([p.title() for p in state.platforms])}

**Voice:** {', '.join(state.tone_tags)}

**Content Topics:** {len(config.get('content_topics', []))} topics generated

**Prompt Templates:** {len(config.get('prompt_templates', {}))} templates created

---

Your profile is ready to use! You can:
- Edit it in the **Profile Manager** tab
- Start collecting content
- Test rewrites in the **Rewriter Lab**
- Begin publishing!

Would you like to create another profile or start using this one?"""

        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": success_msg
        })

        # Show config preview
        with st.expander("📄 View Generated Configuration"):
            st.json(config)

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Another Profile", use_container_width=True):
                st.session_state.wizard_active = False
                st.session_state.wizard_state = WizardState()
                st.session_state.wizard_messages = []
                st.rerun()

        with col2:
            if st.button("Go to Profile Manager", type="primary", use_container_width=True):
                st.session_state.wizard_active = False
                st.rerun()

    except Exception as e:
        error_msg = f"""❌ **Oops! Something went wrong.**

Error: {str(e)}

Don't worry - your answers are saved. You can try again or create the profile manually in the Profile Manager."""

        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": error_msg
        })

        st.error(str(e))


def extract_project_name(description: str) -> str:
    """Extract a short project name from description"""
    # Simple extraction: take first few words
    words = description.split()[:3]
    return ' '.join(words)


async def show_angle_suggestions(state: WizardState):
    """Analyze collected posts and show suggested rewrite angles"""

    try:
        suggester = RewriteAngleSuggester()

        # Analyze posts and get angle suggestions
        analysis = await suggester.suggest_angles_for_profile(
            profile_description=state.project_description,
            target_audience=state.target_audience,
            tone_tags=state.tone_tags,
            sample_size=20
        )

        if analysis.get('error') and not analysis.get('no_posts_available'):
            # Analysis completely failed
            message = f"""⚠️ I couldn't analyze your content right now.

That's okay! We'll proceed with the setup and you can refine later.

**Let's set up your platforms now.** Which platforms do you want to use?

Options:
- Twitter
- Threads
- LinkedIn
- Telegram
- Instagram

Just list the ones you want."""

        elif analysis.get('no_posts_available'):
            # No posts, but we generated generic angles
            angles = analysis.get('recommended_angles', [])
            strategy = analysis.get('content_strategy', [])
            voice_tips = analysis.get('voice_suggestions', [])

            if angles:
                angles_text = "\n".join([
                    f"**{i+1}. {angle['angle']}** (Fit Score: {angle['score']:.0%})\n"
                    f"   {angle['description']}\n"
                    f"   💡 *{angle.get('when_to_use', '')}*"
                    for i, angle in enumerate(angles[:5])
                ])

                strategy_text = "\n".join([f"• {s}" for s in strategy[:4]])
                tips_text = "\n".join([f"• {tip}" for tip in voice_tips[:3]])

                message = f"""💡 **You don't have posts collected yet, but here's what I recommend based on your profile:**

📐 **Best Rewrite Angles for You:**

{angles_text}

📋 **Content Strategy (what to collect):**
{strategy_text or "Start collecting content from your niche"}

🎯 **Voice Tips:**
{tips_text}

**Ready to continue?** Type "continue" or "next" to set up your platforms."""
            else:
                # Fallback if generic generation also failed
                message = """Let's set up your platforms. **Which platforms do you want to use?**

Options:
- Twitter
- Threads
- LinkedIn
- Telegram
- Instagram

Just list the ones you want."""

        else:
            # Build a nice message with suggestions
            angles = analysis.get('recommended_angles', [])
            gaps = analysis.get('content_gaps', [])
            voice_tips = analysis.get('voice_suggestions', [])

            angles_text = "\n".join([
                f"**{i+1}. {angle['angle']}** (Score: {angle['score']:.0%})\n"
                f"   {angle['description']}\n"
                f"   💡 *{angle.get('when_to_use', '')}*"
                for i, angle in enumerate(angles[:5])
            ])

            gaps_text = "\n".join([f"• {gap}" for gap in gaps[:3]])
            tips_text = "\n".join([f"• {tip}" for tip in voice_tips[:3]])

            message = f"""✨ **Based on your collected posts, here are the best rewrite angles for you:**

{angles_text}

📊 **Content Gaps I Found:**
{gaps_text or "None - you have good coverage!"}

🎯 **Voice Tips:**
{tips_text}

**Ready to continue?** Type "continue" or "next" to move on to platform setup."""

        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": message
        })

        # Store angle suggestions in state for later use
        if 'angle_suggestions' not in st.session_state:
            st.session_state.angle_suggestions = analysis

    except Exception as e:
        # Silently fail and continue
        message = """Let's continue with platform setup. **Which platforms do you want to use?**

Options:
- Twitter
- Threads
- LinkedIn
- Telegram
- Instagram

Just list the ones you want."""

        st.session_state.wizard_messages.append({
            "role": "assistant",
            "content": message
        })
