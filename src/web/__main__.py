"""
Main entry point for the Streamlit web application.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set the STREAMLIT_SERVER environment variable to enable the app to run
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "true"

# Import the app after setting up the path
from src.web.app import main

if __name__ == "__main__":
    main()


