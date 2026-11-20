"""Adaptador de pruebas: archivos locales, sin conexión ni escritura en GitHub."""
from pathlib import Path
import hashlib
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
        contenido = st.session_state.get('_archivos_prueba', {}).get(path, p.read_bytes() if p.is_file() else b'')
        return {'ok': bool(contenido), 'content_bytes': contenido,
                'sha': hashlib.sha256(contenido).hexdigest()}

    def upload_bytes_file(self, **kwargs):
        if not st.session_state.get('_permitir_guardado_prueba'):
            raise AssertionError('Esta prueba no permite escrituras externas')
        if 'expected_sha' in kwargs:
            assert kwargs['expected_sha'] == self.download_file_bytes(kwargs['path'])['sha']
        st.session_state.setdefault('_archivos_prueba', {})[kwargs['path']] = kwargs['content_bytes']
        return {'ok': True, 'commit': 'solo-memoria-local'}

    def list_commits_for_path(self, path, per_page=10):
        return {'ok': True, 'commits': []}

home.GitHubSync = GitHubLocal
home.get_github_config = lambda: dict(ok=True, token='local', repo='local', branch='local')
st.set_page_config(layout='wide')
home.render_home()
