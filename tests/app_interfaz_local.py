"""Adaptador de pruebas: archivos locales, sin conexión ni escritura en GitHub."""
from pathlib import Path
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ui import home

class GitHubLocal:
    def __init__(self, *args):
        pass

    def get_file_info(self, path):
        p = ROOT / path
        return {'ok': True, 'exists': p.is_file(), 'commit': {}, 'sha': 'local'}

    def download_file_bytes(self, path):
        p = ROOT / path
        return {'ok': p.is_file(), 'content_bytes': p.read_bytes() if p.is_file() else b''}

    def upload_bytes_file(self, **kwargs):
        raise AssertionError('Esta prueba no permite escrituras externas')

home.GitHubSync = GitHubLocal
home.get_github_config = lambda: dict(ok=True, token='local', repo='local', branch='local')
st.set_page_config(layout='wide')
home.render_home()
