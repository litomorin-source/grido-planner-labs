from datetime import datetime
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import get_github_config
from core.github_sync import GitHubSync
from core.validators import validar_maestro, validar_carrito
from core.version import APP_VERSION

from motor import (
    procesar_archivos,
    procesar_costo_stock,
    validar_stock,
    validar_sabores,
    validar_data,
)

MAESTRO_GITHUB_PATH = "data/Maestro_Productos_Grido.xlsx"
CARRITO_GITHUB_PATH = "data/Modelo_de_Carrito.xlsx"


def formato_moneda_ar(valor):
    try:
        valor = int(float(valor))
    except Exception:
        valor = 0
    signo = "-" if valor < 0 else ""
    entero_txt = f"{abs(valor):,}".replace(",", ".")
    return f"$ {signo}{entero_txt}"


def status_line(ok: bool, label: str, detail: str = ""):
    if ok:
        st.success(f"✅ {label}" + (f" — {detail}" if detail else ""))
    else:
        st.error(f"❌ {label}" + (f" — {detail}" if detail else ""))


def short_sha(sha):
    return sha[:7] if sha else "-"


def format_size(size_bytes):
    if size_bytes is None:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def detectar_grupos_powerbi(file_path):
    try:
        df = pd.read_excel(file_path)
        if df.shape[1] < 13:
            return [], "El archivo tiene menos columnas de las esperadas."
        df.columns = [
            "Categoria", "SubCategoria", "Grupo", "Producto",
            "PL_Cant", "PL_Fact", "PL_Kilos", "PL_Porc",
            "Promo_Cant", "Promo_Fact", "Promo_Kilos", "Promo_Porc",
            "Total_Cantidad", "Total_Fact", "Total_Kilos", "Total_Porc"
        ]
        df = df.iloc[1:].copy()
        for c in ["Categoria", "SubCategoria", "Grupo"]:
            df[c] = df[c].ffill()
        mask = (
            ((df["Categoria"] == "Heladería") & (df["SubCategoria"] == "Impulsivos"))
            | ((df["Categoria"] == "Congelados") & (df["Grupo"].isin(["Congelados Multimarca", "Frizzio"])))
        )
        df = df[mask & df["Producto"].notna() & (~df["Producto"].astype(str).str.lower().eq("total"))].copy()
        return sorted([str(g) for g in df["Grupo"].dropna().unique()]), ""
    except Exception as e:
        return [], f"No pude leer los grupos del Power BI. Error: {e}"


def estado_archivo(label, ok, msg, detalles=None, warning=None):
    if ok:
        st.success(f"✅ {label} OK")
        if warning:
            st.warning(warning)
        if detalles:
            with st.expander(f"Ver detalles de {label}", expanded=False):
                for item in detalles:
                    st.write(f"- {item}")
    else:
        st.error(f"❌ {label}: {msg}")
        if detalles:
            with st.expander("Ver detalle del error", expanded=True):
                st.write(detalles)


def descargar_base_github(github, tmp):
    maestro_download = github.download_file_bytes(MAESTRO_GITHUB_PATH)
    carrito_download = github.download_file_bytes(CARRITO_GITHUB_PATH)
    if not maestro_download["ok"]:
        return False, maestro_download.get("message", "Error descargando Maestro"), None, None
    if not carrito_download["ok"]:
        return False, carrito_download.get("message", "Error descargando Carrito"), None, None
    maestro_path = tmp / "Maestro_Productos_Grido.xlsx"
    carrito_path = tmp / "Modelo_de_Carrito.xlsx"
    maestro_path.write_bytes(maestro_download["content_bytes"])
    carrito_path.write_bytes(carrito_download["content_bytes"])
    ok_m, err_m, _ = validar_maestro(maestro_path)
    if not ok_m:
        return False, "El Maestro de GitHub no pasó validación: " + " | ".join(err_m), None, None
    ok_c, err_c, _ = validar_carrito(carrito_path)
    if not ok_c:
        return False, "El Carrito de GitHub no pasó validación: " + " | ".join(err_c), None, None
    return True, "Base GitHub OK", maestro_path, carrito_path


def render_centro_datos(github):
    st.header("Centro de Datos")
    if st.button("Actualizar estado", use_container_width=True):
        st.session_state["data_status"] = {
            "maestro": github.get_file_info(MAESTRO_GITHUB_PATH),
            "carrito": github.get_file_info(CARRITO_GITHUB_PATH),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    if "data_status" not in st.session_state:
        st.session_state["data_status"] = {
            "maestro": github.get_file_info(MAESTRO_GITHUB_PATH),
            "carrito": github.get_file_info(CARRITO_GITHUB_PATH),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    st.caption(f"Consulta UTC: {st.session_state['data_status']['timestamp']}")
    for nombre, key in [("Maestro", "maestro"), ("Carrito", "carrito")]:
        info = st.session_state["data_status"][key]
        st.subheader(nombre)
        if not info["ok"]:
            st.error(info["message"])
            continue
        if not info["exists"]:
            st.warning("Archivo no encontrado en GitHub.")
            continue
        col1, col2, col3 = st.columns(3)
        col1.metric("Estado", "Cargado")
        col2.metric("Tamaño", format_size(info.get("size")))
        col3.metric("SHA", short_sha(info.get("sha")))
        commit = info.get("commit") or {}
        if commit.get("ok") and commit.get("exists"):
            st.caption(f"Última actualización: {commit.get('author_date')}")
            st.code(commit.get("message") or "-")
        if info.get("html_url"):
            st.link_button(f"Ver {nombre} en GitHub", info["html_url"], use_container_width=True)
        st.markdown("---")


def subir_archivo_validado(label, uploader_label, destino, validator, filename, github):
    st.subheader(label)
    st.caption(f"Destino en GitHub: `{destino}`")
    uploaded_file = st.file_uploader(uploader_label, type=["xlsx"], key=destino)
    if not uploaded_file:
        return
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        file_bytes = uploaded_file.getvalue()
        tmp_path.write_bytes(file_bytes)
        ok, errores, _ = validator(tmp_path)
        if not ok:
            st.error("El archivo no pasó la validación.")
            for err in errores:
                st.error(err)
            return
        st.success("Archivo validado correctamente.")
        col1, col2 = st.columns(2)
        col1.metric("Tamaño archivo", f"{len(file_bytes) / 1024:.1f} KB")
        col2.metric("Destino", destino)
        if st.button(f"Guardar {label} en GitHub", type="primary", use_container_width=True, key=f"btn_{destino}"):
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            commit_message = f"Labs 0.7.0 - actualizar {label} ({timestamp})"
            with st.spinner(f"Subiendo {label} a GitHub..."):
                result = github.upload_bytes_file(path=destino, content_bytes=file_bytes, commit_message=commit_message)
            if result["ok"]:
                st.success(f"{label} guardado en GitHub correctamente.")
                st.write("Commit:")
                st.code(result.get("commit"))
                st.session_state.pop("data_status", None)
                if result.get("html_url"):
                    st.link_button("Ver commit en GitHub", result["html_url"], use_container_width=True)
            else:
                st.error(result["message"])
                st.code(result.get("details", ""))


def _ventas_col(pedido):
    for col in pedido.columns:
        if str(col).startswith("Ventas "):
            return col
    return None


def render_diagnostico_pedido(result):
    pedido = result["pedido"].copy()
    sin_clasificar = result.get("sin_clasificar")
    posibles_faltantes = result.get("posibles_faltantes")
    stock_negativo = result.get("stock_negativo")
    ventas_col = _ventas_col(pedido)

    st.markdown("---")
    st.header("Diagnóstico previo del pedido")

    total_packs = int(pd.to_numeric(pedido.get("Packs a Comprar", 0), errors="coerce").fillna(0).sum())
    valor_stock_total = result.get("valor_stock_total", 0)
    valor_pedido_total = result.get("valor_pedido_total", 0)

    ventas_sin_stock = pedido.iloc[0:0].copy()
    stock_sin_ventas = pedido.iloc[0:0].copy()

    if ventas_col:
        ventas_num = pd.to_numeric(pedido[ventas_col], errors="coerce").fillna(0)
        stock_num = pd.to_numeric(pedido["Stock"], errors="coerce").fillna(0)
        ventas_sin_stock = pedido[(ventas_num > 0) & (stock_num <= 0)].copy()
        stock_sin_ventas = pedido[(stock_num > 0) & (ventas_num == 0)].copy()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Productos detectados", len(pedido))
    m2.metric("Packs sugeridos", total_packs)
    m3.metric("Valor pedido", formato_moneda_ar(valor_pedido_total))
    m4.metric("Valor stock", formato_moneda_ar(valor_stock_total))

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Stock negativo", len(stock_negativo) if stock_negativo is not None else 0)
    a2.metric("Sin clasificar", len(sin_clasificar) if sin_clasificar is not None else 0)
    a3.metric("Posibles faltantes", len(posibles_faltantes) if posibles_faltantes is not None else 0)
    a4.metric("Ventas sin stock", len(ventas_sin_stock))

    if valor_pedido_total and valor_stock_total:
        relacion = float(valor_pedido_total) / max(float(valor_stock_total), 1)
        if relacion > 1:
            st.warning(f"El pedido sugerido supera el valor del stock actual. Relación pedido/stock: {relacion:.2f}. Revisar período y parámetros.")
        elif relacion > 0.6:
            st.info(f"El pedido sugerido representa {relacion:.2f} del valor del stock actual.")

    if stock_negativo is not None and len(stock_negativo) > 0:
        st.error("Hay stock negativo. Revisar inventario o descarga antes de confirmar el pedido.")

    if sin_clasificar is not None and len(sin_clasificar) > 0:
        st.warning("Hay productos sin clasificar. Puede faltar actualizar el Maestro.")

    if posibles_faltantes is not None and len(posibles_faltantes) > 0:
        st.warning("Hay posibles faltantes: productos sin ventas y con stock bajo.")

    tabs = st.tabs(["Top reposición", "Menor cobertura", "Ventas sin stock", "Stock sin ventas", "Alertas"])

    with tabs[0]:
        top_repo = pedido.copy()
        top_repo["__packs"] = pd.to_numeric(top_repo.get("Packs a Comprar", 0), errors="coerce").fillna(0)
        top_repo = top_repo.sort_values("__packs", ascending=False).head(20)
        cols = ["Grupo", "Producto", "Stock", ventas_col, "Venta Semanal", "Semanas Stock", "Packs a Comprar", "Valor Pedido Sugerido", "Código Compra", "Producto Compra"]
        cols = [c for c in cols if c and c in top_repo.columns]
        st.dataframe(top_repo[cols], use_container_width=True)

    with tabs[1]:
        cobertura = pedido.copy()
        cobertura["__semanas"] = pd.to_numeric(cobertura.get("Semanas Stock", None), errors="coerce")
        cobertura = cobertura[cobertura["__semanas"].notna()].sort_values("__semanas", ascending=True).head(20)
        cols = ["Grupo", "Producto", "Stock", ventas_col, "Venta Semanal", "Semanas Stock", "Packs a Comprar", "Valor Pedido Sugerido"]
        cols = [c for c in cols if c and c in cobertura.columns]
        st.dataframe(cobertura[cols], use_container_width=True)

    with tabs[2]:
        if len(ventas_sin_stock) == 0:
            st.success("No se detectaron productos con ventas y stock cero/negativo.")
        else:
            cols = ["Grupo", "Producto", "Stock", ventas_col, "Venta Semanal", "Packs a Comprar", "Código Compra", "Producto Compra"]
            cols = [c for c in cols if c and c in ventas_sin_stock.columns]
            st.dataframe(ventas_sin_stock[cols], use_container_width=True)

    with tabs[3]:
        if len(stock_sin_ventas) == 0:
            st.success("No se detectaron productos con stock y ventas cero.")
        else:
            cols = ["Grupo", "Producto", "Stock", ventas_col, "Semanas Stock", "Observación", "Código Compra", "Producto Compra"]
            cols = [c for c in cols if c and c in stock_sin_ventas.columns]
            st.dataframe(stock_sin_ventas[cols].head(100), use_container_width=True)

    with tabs[4]:
        hay_alertas = False
        if stock_negativo is not None and len(stock_negativo) > 0:
            hay_alertas = True
            with st.expander("Stock negativo", expanded=True):
                st.dataframe(stock_negativo, use_container_width=True)

        if posibles_faltantes is not None and len(posibles_faltantes) > 0:
            hay_alertas = True
            with st.expander("Posibles faltantes", expanded=True):
                st.dataframe(posibles_faltantes, use_container_width=True)

        if sin_clasificar is not None and len(sin_clasificar) > 0:
            hay_alertas = True
            with st.expander("Sin clasificar", expanded=True):
                st.dataframe(sin_clasificar, use_container_width=True)

        if not hay_alertas:
            st.success("No se detectaron alertas principales.")


def render_generar_pedido(github):
    st.header("Generar pedido")
    st.caption("Subí Stock, Sabores y Power BI. El Maestro y el Carrito vigentes se toman automáticamente.")
    col1, col2, col3 = st.columns(3)
    with col1:
        stock_file = st.file_uploader("1. Archivo de STOCK", type=["csv"])
    with col2:
        sabores_file = st.file_uploader("2. Ventas de SABORES", type=["xlsx"])
    with col3:
        data_file = st.file_uploader("3. Ventas Power BI", type=["xlsx"])

    st.subheader("Configuración")
    cfg1, cfg2, cfg3 = st.columns(3)
    with cfg1:
        semanas_objetivo = st.number_input("Semanas objetivo", min_value=0.5, max_value=12.0, value=4.0, step=0.5)
    with cfg2:
        tiempo_reposicion = st.number_input("Tiempo de reposición", min_value=0.0, max_value=8.0, value=1.0, step=0.5)
    with cfg3:
        dias_analizados = st.number_input("Días analizados", min_value=1, max_value=60, value=14, step=1)

    st.markdown("---")
    st.subheader("Estado de archivos")
    ready = True
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        paths = {}
        with st.spinner("Cargando Maestro y Carrito vigentes..."):
            base_ok, base_msg, maestro_path, carrito_path = descargar_base_github(github, tmp)
        if base_ok:
            st.success("✅ Maestro y Carrito vigentes OK")
        else:
            st.error(base_msg)
            st.stop()

        if stock_file:
            p = tmp / "stock.csv"
            p.write_bytes(stock_file.getvalue())
            ok, msg = validar_stock(p)
            estado_archivo("Stock", ok, msg)
            ready = ready and ok
            paths["stock"] = p
        else:
            ready = False
            st.info("📄 Stock: pendiente")

        if sabores_file:
            p = tmp / "cajas_por_sabor.xlsx"
            p.write_bytes(sabores_file.getvalue())
            ok, msg = validar_sabores(p)
            estado_archivo("Sabores", ok, msg)
            ready = ready and ok
            paths["sabores"] = p
        else:
            ready = False
            st.info("📄 Sabores: pendiente")

        if data_file:
            p = tmp / "data.xlsx"
            p.write_bytes(data_file.getvalue())
            ok, msg = validar_data(p)
            grupos, grupo_error = detectar_grupos_powerbi(p)
            detalles = []
            if grupos:
                detalles.append("Grupos detectados en la exportación:")
                detalles.extend(grupos)
            if grupo_error:
                detalles.append(grupo_error)
            warning = "Revisá que estén todos los grupos esperados. Si no desplegaste el '+', el pedido puede quedar incompleto."
            estado_archivo("Power BI", ok, msg, detalles=detalles if detalles else None, warning=warning if ok else None)
            ready = ready and ok
            paths["data"] = p
        else:
            ready = False
            st.info("📄 Power BI: pendiente")

        st.markdown("---")
        if "stock" in paths:
            st.subheader("Informe costo stock")
            if st.button("GENERAR INFORME COSTO STOCK", use_container_width=True):
                output_stock = tmp / "Informe_Costo_Stock.xlsx"
                try:
                    result_stock = procesar_costo_stock(
                        stock_file=paths["stock"],
                        maestro_file=maestro_path,
                        output_file=output_stock,
                        carrito_file=carrito_path,
                    )
                    st.success("Informe de costo de stock generado correctamente.")
                    st.metric("Valor stock actual", formato_moneda_ar(result_stock.get("valor_stock_total", 0)))
                    if result_stock.get("categoria") is not None:
                        with st.expander("Ver valorización por categoría", expanded=False):
                            st.dataframe(result_stock["categoria"], use_container_width=True)
                    st.download_button(
                        "DESCARGAR INFORME COSTO STOCK",
                        data=output_stock.read_bytes(),
                        file_name="Informe_Costo_Stock.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error("Ocurrió un error al generar el informe de costo stock.")
                    st.exception(e)

        if not ready:
            st.info("Cuando los 3 archivos estén en OK, se habilita la generación del pedido.")
            st.stop()

        st.success("✅ Todo listo para generar el pedido.")
        if st.button("ANALIZAR Y GENERAR PEDIDO", type="primary", use_container_width=True):
            output = tmp / "Pedido_Final.xlsx"
            try:
                result = procesar_archivos(
                    stock_file=paths["stock"],
                    sabores_file=paths["sabores"],
                    data_file=paths["data"],
                    maestro_file=maestro_path,
                    output_file=output,
                    overrides={
                        "Semanas objetivo": semanas_objetivo,
                        "Tiempo de reposición": tiempo_reposicion,
                        "Días analizados": dias_analizados,
                    },
                    carrito_file=carrito_path,
                )
                pedido = result["pedido"]
                sin_clasificar = result["sin_clasificar"]
                posibles_faltantes = result.get("posibles_faltantes")
                stock_negativo = result.get("stock_negativo")
                st.success("Pedido analizado correctamente.")
                render_diagnostico_pedido(result)

                st.markdown("---")
                st.header("Resumen final")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Productos en pedido", len(pedido))
                m2.metric("Stock negativo", len(stock_negativo) if stock_negativo is not None else 0)
                m3.metric("Sin clasificar", len(sin_clasificar))
                m4.metric("Posibles faltantes", len(posibles_faltantes) if posibles_faltantes is not None else 0)
                m5.metric("Packs sugeridos", int(pedido["Packs a Comprar"].fillna(0).sum()))
                v1, v2 = st.columns(2)
                v1.metric("Valor stock actual", formato_moneda_ar(result.get("valor_stock_total", 0)))
                v2.metric("Valor pedido sugerido", formato_moneda_ar(result.get("valor_pedido_total", 0)))
                if result.get("valorizacion_categoria") is not None:
                    with st.expander("Ver valorización por categoría", expanded=False):
                        st.dataframe(result["valorizacion_categoria"], use_container_width=True)
                if result.get("valorizacion_producto") is not None:
                    with st.expander("Ver valorización por producto", expanded=False):
                        st.dataframe(result["valorizacion_producto"], use_container_width=True)
                if stock_negativo is not None and len(stock_negativo) > 0:
                    st.error("⚠️ Se detectaron productos con stock negativo.")
                if posibles_faltantes is not None and len(posibles_faltantes) > 0:
                    st.warning("Se detectaron posibles faltantes.")
                if len(sin_clasificar) > 0:
                    st.warning("Hay productos sin clasificar.")
                st.download_button(
                    "DESCARGAR PEDIDO FINAL",
                    data=output.read_bytes(),
                    file_name="Pedido_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
                with st.expander("Ver vista previa del pedido", expanded=False):
                    st.dataframe(pedido.head(100), use_container_width=True)
                if stock_negativo is not None and len(stock_negativo) > 0:
                    with st.expander("Ver stock negativo", expanded=True):
                        st.dataframe(stock_negativo, use_container_width=True)
                if posibles_faltantes is not None and len(posibles_faltantes) > 0:
                    with st.expander("Ver posibles faltantes", expanded=True):
                        st.dataframe(posibles_faltantes, use_container_width=True)
                if len(sin_clasificar) > 0:
                    with st.expander("Ver productos sin clasificar", expanded=True):
                        st.dataframe(sin_clasificar, use_container_width=True)
            except Exception as e:
                st.error("Ocurrió un error al generar el pedido.")
                st.exception(e)


def render_actualizar_archivos(github):
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


ADMIN_PIN = "2468"

def render_home():
    st.title("🍦 GridoPlanner Labs")
    st.caption(APP_VERSION)

    modo = st.sidebar.radio("Modo", ["Usuario", "Administrador"])
    st.sidebar.markdown("---")
    st.sidebar.info(f"Versión {APP_VERSION}")

    config = get_github_config()

    if not config["ok"]:
        st.error("Faltan Secrets de GitHub.")
        for item in config["missing"]:
            st.code(item)
        st.stop()

    github = GitHubSync(config["token"], config["repo"], config["branch"])

    if modo == "Usuario":
        render_generar_pedido(github)
        return

    st.header("Administrador")
    pin = st.text_input("PIN de administrador", type="password")

    if pin != ADMIN_PIN:
        st.warning("Ingresá el PIN correcto para administrar archivos.")
        st.stop()

    st.success("PIN correcto.")

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

    tab1, tab2 = st.tabs(["Centro de Datos", "Actualizar archivos"])

    with tab1:
        render_centro_datos(github)

    with tab2:
        render_actualizar_archivos(github)
