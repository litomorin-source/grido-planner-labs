from datetime import datetime
import tempfile
from pathlib import Path

import streamlit as st

from core.config import get_github_config
from core.github_sync import GitHubSync
from core.validators import validar_maestro, validar_carrito
from core.version import APP_VERSION

MAESTRO_GITHUB_PATH = "data/Maestro_Productos_Grido.xlsx"
CARRITO_GITHUB_PATH = "data/Modelo_de_Carrito.xlsx"

def status_line(ok: bool, label: str, detail: str = ""):
    if ok:
        st.success(f"✅ {label}" + (f" — {detail}" if detail else ""))
    else:
        st.error(f"❌ {label}" + (f" — {detail}" if detail else ""))

def subir_archivo_validado(label, uploader_label, destino, validator, filename, github):
    st.subheader(label)
    st.caption(f"Destino en GitHub: `{destino}`")

    uploaded_file = st.file_uploader(
        uploader_label,
        type=["xlsx"],
        key=destino,
    )

    if not uploaded_file:
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        file_bytes = uploaded_file.getvalue()
        tmp_path.write_bytes(file_bytes)

        ok, errores, advertencias = validator(tmp_path)

        if not ok:
            st.error("El archivo no pasó la validación.")
            for err in errores:
                st.error(err)
            return

        st.success("Archivo validado correctamente.")

        if advertencias:
            with st.expander("Advertencias", expanded=False):
                for adv in advertencias:
                    st.warning(adv)

        col1, col2 = st.columns(2)
        col1.metric("Tamaño archivo", f"{len(file_bytes) / 1024:.1f} KB")
        col2.metric("Destino", destino)

        if st.button(f"Guardar {label} en GitHub", type="primary", use_container_width=True, key=f"btn_{destino}"):
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            commit_message = f"Labs 0.4.0 - actualizar {label} ({timestamp})"

            with st.spinner(f"Subiendo {label} a GitHub..."):
                result = github.upload_bytes_file(
                    path=destino,
                    content_bytes=file_bytes,
                    commit_message=commit_message,
                )

            if result["ok"]:
                st.success(f"{label} guardado en GitHub correctamente.")
                st.write("Commit:")
                st.code(result.get("commit"))
                if result.get("html_url"):
                    st.link_button("Ver commit en GitHub", result["html_url"], use_container_width=True)
            else:
                st.error(result["message"])
                st.code(result.get("details", ""))

def render_home():
    st.title("🍦 GridoPlanner Labs")
    st.caption(APP_VERSION)
    st.info("Labs 0.4.0: actualizar Maestro y Carrito en GitHub con validación y commit automático.")

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
    subir_archivo_validado(
        label="Maestro",
        uploader_label="Subir Maestro_Productos_Grido.xlsx",
        destino=MAESTRO_GITHUB_PATH,
        validator=validar_maestro,
        filename="Maestro_Productos_Grido.xlsx",
        github=github,
    )

    st.markdown("---")
    subir_archivo_validado(
        label="Carrito",
        uploader_label="Subir Modelo_de_Carrito.xlsx",
        destino=CARRITO_GITHUB_PATH,
        validator=validar_carrito,
        filename="Modelo_de_Carrito.xlsx",
        github=github,
    )
