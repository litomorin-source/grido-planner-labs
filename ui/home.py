from datetime import datetime
import streamlit as st

from core.config import get_github_config
from core.github_sync import GitHubSync
from core.version import APP_VERSION

def status_line(ok: bool, label: str, detail: str = ""):
    if ok:
        st.success(f"✅ {label}" + (f" — {detail}" if detail else ""))
    else:
        st.error(f"❌ {label}" + (f" — {detail}" if detail else ""))

def render_home():
    st.title("🍦 GridoPlanner Labs")
    st.caption(APP_VERSION)

    st.info("Labs 0.2 verifica conexión con GitHub y prueba escritura creando/actualizando `data/test.txt`.")

    config = get_github_config()
    status_line(config["ok"], "Secrets encontrados")

    if not config["ok"]:
        st.warning("Faltan estos Secrets:")
        for item in config["missing"]:
            st.code(item)
        st.stop()

    st.write("Repositorio:")
    st.code(config["repo"])
    st.write("Rama:")
    st.code(config["branch"])

    github = GitHubSync(config["token"], config["repo"], config["branch"])

    st.markdown("---")
    st.subheader("1. Probar conexión")

    if st.button("Probar conexión GitHub", type="primary", use_container_width=True):
        with st.spinner("Conectando..."):
            result = github.verify()

        repo = result.get("repo")
        branch = result.get("branch")

        status_line(repo["ok"], "Repositorio accesible", repo.get("message", ""))
        if branch:
            status_line(branch["ok"], "Rama encontrada", branch.get("message", ""))
            if branch.get("ok"):
                st.write("Último commit:")
                st.code(branch.get("commit_sha"))

        if result["ok"]:
            st.success("GitHub Sync base funcionando.")
            st.balloons()

    st.markdown("---")
    st.subheader("2. Probar escritura")

    if st.button("Subir archivo de prueba a GitHub", use_container_width=True):
        contenido = (
            "GridoPlanner Labs - prueba de escritura GitHub\\n"
            f"Fecha/hora UTC: {datetime.utcnow().isoformat()}\\n"
        )

        with st.spinner("Subiendo data/test.txt..."):
            upload_result = github.upload_text_file(
                path="data/test.txt",
                content=contenido,
                commit_message="Labs 0.2 - actualizar archivo de prueba",
            )

        if upload_result["ok"]:
            st.success("Archivo de prueba subido correctamente.")
            st.write("Commit:")
            st.code(upload_result.get("commit"))
            st.balloons()
        else:
            st.error(upload_result["message"])
            st.code(upload_result.get("details", ""))
