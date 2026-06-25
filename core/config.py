import streamlit as st

REQUIRED_SECRETS = ["GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_BRANCH"]

def get_github_config():
    missing = [key for key in REQUIRED_SECRETS if key not in st.secrets]
    if missing:
        return {"ok": False, "missing": missing, "token": None, "repo": None, "branch": None}
    return {
        "ok": True,
        "missing": [],
        "token": st.secrets["GITHUB_TOKEN"],
        "repo": st.secrets["GITHUB_REPO"],
        "branch": st.secrets["GITHUB_BRANCH"],
    }
