#!/usr/bin/env python3

import os
import sys
import subprocess

def main():
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(current_dir, 'src')
    
    # Add the src directory to the Python path
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    # Set the working directory to the src directory
    os.chdir(src_dir)
    
    # Import the app module
    from web import app
    
    # Run the Streamlit app
    subprocess.run(["streamlit", "run", "web/app.py"])

if __name__ == "__main__":
    main()
