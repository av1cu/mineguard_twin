import streamlit as st
import sys
import os

# Add parent directory to path to enable imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from frontend.mine_map import render_page

if __name__ == "__main__":
    st.set_page_config(page_title="Digital Twin Map", layout="wide")
    render_page()
