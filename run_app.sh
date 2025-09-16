#!/bin/bash

# Add the src directory to PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"

# Run the Streamlit app
cd src/web
python -m streamlit run app.py
