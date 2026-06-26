from datetime import datetime
import tempfile
from pathlib import Path

import streamlit as st

from core.config import get_github_config
from core.github_sync import GitHubSync
from core.validators import validar_maestro
from core.version import APP_VERSION

MAESTRO_GITHUB_PATH = "data/Maestro_Productos_Grido.xlsx"

def status_line(ok: bool, label: str, detail: str = ""):
    if ok:
        st.success(f"✅ {label}" + (f" — {detail}" if detail else ""))
    else:
        st.error(f"❌ {label}" + (f" — {detail}" if detail else ""))

def render_home():
    st.title("🍦 GridoPlanner Labs")
    st.caption(APP_VERSION)

    st.info("Labs 0.3.0 permite validar y actualizar el Maestro en GitHub con commit automático.")

    config = get_github_config()
    status_line(config["ok"], "Secrets encontrados")

    if not config["ok"]:
        st.warning("Faltan estos Secrets:")
        for item in config["missing"]:
            st.code(item)
        st.stop()

    github = GitHubSync(config["token"], config["repo"], config["branch"])

    with st.expander("Estado GitHub", expanded=False):
        st.write("Repositorio:")
        st.code(config["repo"])
        st.write("Rama:")
        st.code(config["branch"])

        if st.button("Probar conexión GitHub", use_container_width=True):
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

    st.markdown("---")
    st.subheader("Actualizar Maestro")

    st.caption(f"Destino en GitHub: `{MAESTRO_GITHUB_PATH}`")

    maestro_file = st.file_uploader(
        "Subir Maestro_Productos_Grido.xlsx",
        type=["xlsx"],
        help="Debe tener las hojas Productos, Aliases, Exclusiones y Configuración.",
    )

    if maestro_file:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "Maestro_Productos_Grido.xlsx"
            file_bytes = maestro_file.getvalue()
            tmp_path.write_bytes(file_bytes)

            ok, errores, advertencias = validar_maestro(tmp_path)

            if ok:
                st.success("Maestro validado correctamente.")

                if advertencias:
                    with st.expander("Advertencias", expanded=False):
                        for adv in advertencias:
                            st.warning(adv)

                col1, col2 = st.columns(2)
                col1.metric("Tamaño archivo", f"{len(file_bytes) / 1024:.1f} KB")
                col2.metric("Destino", MAESTRO_GITHUB_PATH)

                if st.button("Guardar Maestro en GitHub", type="primary", use_container_width=True):
                    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    commit_message = f"Labs 0.3.0 - actualizar Maestro ({timestamp})"

                    with st.spinner("Subiendo Maestro a GitHub..."):
                        result = github.upload_bytes_file(
                            path=MAESTRO_GITHUB_PATH,
                            content_bytes=file_bytes,
                            commit_message=commit_message,
                        )

                    if result["ok"]:
                        st.success("Maestro guardado en GitHub correctamente.")
                        st.write("Commit:")
                        st.code(result.get("commit"))
                        if result.get("html_url"):
                            st.link_button("Ver commit en GitHub", result["html_url"], use_container_width=True)
                    else:
                        st.error(result["message"])
                        st.code(result.get("details", ""))

            else:
                st.error("El Maestro no pasó la validación.")
                for err in errores:
                    st.error(err)\n