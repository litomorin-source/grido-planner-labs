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

    st.markdown("### Objetivo de esta versión")
    st.info(
        "Labs 0.1 solo verifica que la app pueda leer los Secrets y conectarse a GitHub. "
        "No modifica archivos todavía."
    )

    st.markdown("---")
    st.subheader("Estado del sistema")

    config = get_github_config()

    status_line(config["ok"], "Secrets encontrados")

    if not config["ok"]:
        st.warning("Faltan estos Secrets en Streamlit:")
        for item in config["missing"]:
            st.code(item)
        st.stop()

    st.write("Repositorio configurado:")
    st.code(config["repo"])

    st.write("Rama configurada:")
    st.code(config["branch"])

    if st.button("Probar conexión GitHub", type="primary", use_container_width=True):
        github = GitHubSync(
            token=config["token"],
            repo=config["repo"],
            branch=config["branch"],
        )

        with st.spinner("Conectando con GitHub..."):
            result = github.verify()

        repo = result.get("repo")
        branch = result.get("branch")

        status_line(repo["ok"], "Repositorio accesible", repo.get("message", ""))

        if repo["ok"]:
            st.write("Branch default del repo:")
            st.code(repo.get("default_branch"))

        if branch:
            status_line(branch["ok"], "Rama encontrada", branch.get("message", ""))
            if branch["ok"]:
                st.write("Último commit detectado:")
                st.code(branch.get("commit_sha"))

        if result["ok"]:
            st.balloons()
            st.success("GitHub Sync base funcionando. Labs 0.1 aprobado.")
        else:
            st.error("La conexión todavía no está lista. Revisá repo, branch o permisos del token.")

    st.markdown("---")
    st.caption("Próximo paso: Labs 0.2 — subir un archivo test.txt a GitHub con commit automático.")
