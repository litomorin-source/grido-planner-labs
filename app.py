import streamlit as st

from ui.home import render_home

st.set_page_config(
    page_title="GridoPlanner Labs",
    page_icon="🍦",
    layout="wide",
)

render_home()
