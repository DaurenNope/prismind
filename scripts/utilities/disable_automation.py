#!/usr/bin/env python3
"""
Disable the automation system that's causing unwanted collections
"""

# Read the file
with open("src/web/app.py", "r") as f:
    content = f.read()

# Replace the automation startup section
old_section = """    # Start autoposter worker if enabled (only once per session)
    if "publisher_worker_started" not in st.session_state:
        st.session_state.publisher_worker_started = False

        if (
            os.getenv("AUTO_PUBLISHER_ENABLED", "true").lower() in ("true", "1", "yes")
            and not st.session_state.publisher_worker_started
        ):
            try:
                get_publisher_worker().start()
                st.session_state.publisher_worker_started = True
                # Log to console (Streamlit doesn't show this in UI, but it will appear in terminal)
                import logging

                logging.basicConfig(level=logging.INFO)
                logging.info("🚀 Publisher worker started automatically")
            except Exception as e:
                logging.error(f"Failed to start publisher worker: {e}")
"""

new_section = """    # Start autoposter worker if enabled (DISABLED - causing unwanted collections)
    # The automation system was causing unwanted background collections
    # This is now disabled to prevent automatic collection triggers
    if "publisher_worker_started" not in st.session_state:
        st.session_state.publisher_worker_started = False"""

# Replace the section
content = content.replace(old_section, new_section)

# Write back
with open("src/web/app.py", "w") as f:
    f.write(content)

print("✅ Disabled automation system to prevent unwanted collections")
