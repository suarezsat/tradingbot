"""Aplicacion Streamlit para varias versiones del backtester Forex."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from backtesting import Backtest

try:
    from almacen_backtests import guardar_backtest_lote, listar_backtests_guardados
    from almacen_estrategias import (
        eliminar_estrategia_personalizada,
        guardar_estrategia_personalizada,
        listar_estrategias_personalizadas,
    )
    from estrategias import CONFIGURACION_ESTRATEGIAS, ESTRATEGIAS_CLASICAS
    from metricas import (
        calcular_metricas_resumen,
        calcular_serie_drawdown,
        extraer_curva_equity,
        extraer_trades,
        formatear_duracion,
        formatear_numero,
        preparar_tabla_operaciones,
    )
    from procesador_datos import (
        CSVFormatoError,
        FuenteArchivo,
        cargar_fuente_ohlcv,
        expandir_fuente_archivo,
        inferir_tamano_pip,
        leer_fuente_local,
    )
except ImportError:
    from .almacen_backtests import guardar_backtest_lote, listar_backtests_guardados
    from .almacen_estrategias import (
        eliminar_estrategia_personalizada,
        guardar_estrategia_personalizada,
        listar_estrategias_personalizadas,
    )
    from .estrategias import CONFIGURACION_ESTRATEGIAS, ESTRATEGIAS_CLASICAS
    from .metricas import (
        calcular_metricas_resumen,
        calcular_serie_drawdown,
        extraer_curva_equity,
        extraer_trades,
        formatear_duracion,
        formatear_numero,
        preparar_tabla_operaciones,
    )
    from .procesador_datos import (
        CSVFormatoError,
        FuenteArchivo,
        cargar_fuente_ohlcv,
        expandir_fuente_archivo,
        inferir_tamano_pip,
        leer_fuente_local,
    )


RUTA_APP = Path(__file__).resolve().parent
RUTA_CAPTURAS = RUTA_APP / "assets" / "capturas"
APALANCAMIENTO_POR_DEFECTO = 30.0
EXTENSIONES_CARPETA = {".csv", ".zip"}
DIRECTORIOS_EXCLUIDOS_BIBLIOTECA = {
    ".git",
    ".playwright-cli",
    ".streamlit",
    ".venv",
    "__pycache__",
    "env",
    "node_modules",
    "venv",
}
SESIONES_TRADING = {
    "Sin filtro": (-1, -1),
    "Londres (08:00 - 17:00 UTC)": (8, 17),
    "Nueva York (13:00 - 22:00 UTC)": (13, 22),
    "Asiatica (00:00 - 09:00 UTC)": (0, 9),
}
VERSIONES_APP = {
    "1.0": {
        "titulo": "Version 1.0",
        "subtitulo": "Modo clasico de un solo archivo y tres estrategias base.",
        "descripcion": "La primera version funcional: subida manual, tres estrategias y un flujo directo de backtesting.",
    },
    "1.1": {
        "titulo": "Version 1.1",
        "subtitulo": "Version estable actual con biblioteca local, ZIP y lotes multiarchivo.",
        "descripcion": "Mantiene la interfaz que ya te gusta con Inicio, Nuevo backtest y Guardados.",
    },
    "1.3": {
        "titulo": "Version 1.3",
        "subtitulo": "Edicion avanzada con trading manual y estrategias personalizadas.",
        "descripcion": "Amplia la 1.1 con lector de graficas para manual, mas estrategias y constructor guardable.",
    },
}


def obtener_carpeta_datos_predeterminada() -> Path:
    """Sugiere una carpeta local de datos segun el entorno."""
    candidatas = [
        Path.home() / "OneDrive" / "Documentos" / "DataParaBot",
        Path.home() / "Documentos" / "DataParaBot",
        RUTA_APP,
    ]

    for ruta in candidatas:
        if ruta.exists():
            return ruta

    return RUTA_APP


def inicializar_estado():
    """Inicializa valores persistentes de la sesion."""
    valores_por_defecto = {
        "version_activa": None,
        "carpeta_datos": str(obtener_carpeta_datos_predeterminada()),
        "vista_v11": "Inicio",
        "vista_v13": "Inicio",
        "resultado_lote_v11": None,
        "resultado_lote_v13": None,
        "nombre_lote_guardado_v11": "",
        "nombre_lote_guardado_v13": "",
        "mensaje_guardado_v11": None,
        "mensaje_guardado_v13": None,
        "manual_v13": None,
    }

    for clave, valor in valores_por_defecto.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def slugify(texto: str) -> str:
    """Genera una clave estable para widgets."""
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", texto.lower()).strip("-")
    return limpio or "item"


def acortar_texto(texto: str, limite: int = 28) -> str:
    """Acorta textos largos para etiquetas y leyendas."""
    if len(texto) <= limite:
        return texto
    return f"{texto[: limite - 3]}..."


def cambiar_version(version: str | None):
    """Cambia la version activa de la aplicacion."""
    st.session_state["version_activa"] = version
    st.rerun()


def cambiar_vista(clave_estado: str, vista: str):
    """Cambia de vista dentro de una version."""
    st.session_state[clave_estado] = vista
    st.rerun()


def render_selector_version():
    """Muestra el selector inicial de versiones."""
    st.title("Backtester de estrategias Forex")
    st.write(
        "Selecciona con que version quieres entrar. La 1.1 es la estable actual, la 1.0 recupera el flujo clasico y la 1.3 añade herramientas avanzadas."
    )

    columnas = st.columns(3)
    for columna, version in zip(columnas, VERSIONES_APP):
        meta = VERSIONES_APP[version]
        with columna:
            st.subheader(meta["titulo"])
            st.caption(meta["subtitulo"])
            st.write(meta["descripcion"])
            if st.button(f"Abrir {version}", use_container_width=True, type="primary" if version == "1.1" else "secondary"):
                cambiar_version(version)

    st.info(
        "Puedes cambiar de version en cualquier momento desde la barra lateral sin perder el resto de archivos ni backtests guardados."
    )


def render_sidebar_version():
    """Renderiza el selector rapido de version en la barra lateral."""
    version = st.session_state["version_activa"]

    with st.sidebar:
        st.header(f"Version {version}")
        st.caption(VERSIONES_APP[version]["subtitulo"])
        if st.button("Cambiar version", use_container_width=True):
            cambiar_version(None)


def render_navegacion(views: list[str], clave_estado: str):
    """Dibuja la navegacion principal dentro de la version."""
    columnas = st.columns(len(views))
    vista_actual = st.session_state[clave_estado]

    for columna, vista in zip(columnas, views):
        tipo = "primary" if vista_actual == vista else "secondary"
        if columna.button(vista, use_container_width=True, type=tipo, key=f"{clave_estado}_{slugify(vista)}"):
            cambiar_vista(clave_estado, vista)


def render_sidebar_resumen(archivos_locales: list[dict[str, object]], guardados: list[dict[str, object]], resultado_actual: dict[str, object] | None = None):
    """Barra lateral de apoyo para las vistas no operativas."""
    with st.sidebar:
        st.markdown("---")
        st.header("Resumen")
        st.metric("Archivos en biblioteca", len(archivos_locales))
        st.metric("Backtests guardados", len(guardados))
        if resultado_actual:
            st.caption("Ultimo lote ejecutado")
            st.write(resultado_actual["estrategia"])
            st.caption(resultado_actual["timestamp"])


def obtener_catalogo_base(nombres_estrategia: list[str] | None = None) -> dict[str, dict[str, object]]:
    """Devuelve el catalogo base de estrategias integradas."""
    nombres = nombres_estrategia or list(CONFIGURACION_ESTRATEGIAS.keys())
    catalogo = {}
    for nombre in nombres:
        configuracion = CONFIGURACION_ESTRATEGIAS[nombre]
        defaults = {parametro.clave: parametro.valor_defecto for parametro in configuracion["parametros"]}
        catalogo[nombre] = {
            **configuracion,
            "nombre_visible": nombre,
            "origen": "Integrada",
            "parametros_defecto": defaults,
            "descripcion_visible": configuracion["descripcion"],
        }
    return catalogo


def obtener_catalogo_avanzado() -> dict[str, dict[str, object]]:
    """Combina estrategias integradas y guardadas para la version 1.3."""
    catalogo = obtener_catalogo_base()
    for item in listar_estrategias_personalizadas():
        plantilla = item.get("plantilla_base")
        if plantilla not in CONFIGURACION_ESTRATEGIAS:
            continue

        base = CONFIGURACION_ESTRATEGIAS[plantilla]
        defaults = {
            parametro.clave: item.get("parametros", {}).get(parametro.clave, parametro.valor_defecto)
            for parametro in base["parametros"]
        }
        nombre_visible = f"Guardada: {item['nombre']}"
        catalogo[nombre_visible] = {
            **base,
            "nombre_visible": nombre_visible,
            "origen": "Guardada",
            "parametros_defecto": defaults,
            "descripcion_visible": item.get("descripcion") or base["descripcion"],
            "meta_guardada": item,
        }
    return catalogo


def construir_parametros_estrategia(
    nombre_estrategia: str,
    catalogo: dict[str, dict[str, object]],
    key_prefix: str = "",
) -> dict[str, float]:
    """Dibuja los controles de la estrategia elegida y devuelve sus valores."""
    configuracion = catalogo[nombre_estrategia]
    parametros = {}
    defaults = configuracion.get("parametros_defecto", {})

    st.markdown(f"**{nombre_estrategia}**")
    st.caption(configuracion["descripcion_visible"])

    for parametro in configuracion["parametros"]:
        valor_defecto = defaults.get(parametro.clave, parametro.valor_defecto)
        clave_widget = f"{key_prefix}_{nombre_estrategia}_{parametro.clave}"

        if parametro.tipo == "int":
            valor = st.number_input(
                parametro.etiqueta,
                min_value=int(parametro.valor_min),
                max_value=int(parametro.valor_max),
                value=int(valor_defecto),
                step=int(parametro.paso),
                help=parametro.ayuda,
                key=clave_widget,
            )
            parametros[parametro.clave] = int(valor)
        else:
            valor = st.number_input(
                parametro.etiqueta,
                min_value=float(parametro.valor_min),
                max_value=float(parametro.valor_max),
                value=float(valor_defecto),
                step=float(parametro.paso),
                help=parametro.ayuda,
                key=clave_widget,
            )
            parametros[parametro.clave] = float(valor)

    return parametros


def ejecutar_backtest(datos: pd.DataFrame, clase_estrategia, parametros: dict[str, float]):
    """Lanza el motor de backtesting con los parametros elegidos."""
    motor = Backtest(
        datos,
        clase_estrategia,
        cash=float(parametros["capital_inicial"]),
        commission=0.0,
        margin=1 / float(parametros["leverage"]),
        trade_on_close=False,
        hedging=False,
        exclusive_orders=False,
        finalize_trades=True,
    )

    parametros_run = {k: v for k, v in parametros.items() if k not in {"capital_inicial", "leverage"}}
    return motor.run(**parametros_run)


def crear_grafico_velas(datos: pd.DataFrame, trades: pd.DataFrame, velas_a_mostrar: int) -> go.Figure:
    """Grafico de velas con entradas y salidas de las operaciones."""
    datos_visibles = datos.tail(velas_a_mostrar)

    figura = go.Figure()
    figura.add_trace(
        go.Candlestick(
            x=datos_visibles.index,
            open=datos_visibles["Open"],
            high=datos_visibles["High"],
            low=datos_visibles["Low"],
            close=datos_visibles["Close"],
            name="Precio",
        )
    )

    if not trades.empty:
        trades_visibles = trades[trades["EntryTime"] >= datos_visibles.index.min()].copy()
        entradas_largas = trades_visibles[trades_visibles["Size"] > 0]
        entradas_cortas = trades_visibles[trades_visibles["Size"] < 0]

        if not entradas_largas.empty:
            figura.add_trace(
                go.Scatter(
                    x=entradas_largas["EntryTime"],
                    y=entradas_largas["EntryPrice"],
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=11, color="#1c8f58"),
                    name="Entrada larga",
                )
            )

        if not entradas_cortas.empty:
            figura.add_trace(
                go.Scatter(
                    x=entradas_cortas["EntryTime"],
                    y=entradas_cortas["EntryPrice"],
                    mode="markers",
                    marker=dict(symbol="triangle-down", size=11, color="#c94f3d"),
                    name="Entrada corta",
                )
            )

        figura.add_trace(
            go.Scatter(
                x=trades_visibles["ExitTime"],
                y=trades_visibles["ExitPrice"],
                mode="markers",
                marker=dict(symbol="x", size=9, color="#225ea8"),
                name="Salida",
            )
        )

    figura.update_layout(
        title="Grafico de velas con entradas y salidas",
        xaxis_title="Fecha",
        yaxis_title="Precio",
        height=620,
        xaxis_rangeslider_visible=False,
        legend_title_text="Eventos",
    )
    return figura


def crear_grafico_velas_manual(
    datos_visibles: pd.DataFrame,
    trades: pd.DataFrame,
    trade_abierto: dict[str, object] | None,
) -> go.Figure:
    """Grafico del modo manual mostrando solo el historico visible."""
    figura = go.Figure()
    figura.add_trace(
        go.Candlestick(
            x=datos_visibles.index,
            open=datos_visibles["Open"],
            high=datos_visibles["High"],
            low=datos_visibles["Low"],
            close=datos_visibles["Close"],
            name="Precio",
        )
    )

    if not trades.empty:
        figura.add_trace(
            go.Scatter(
                x=trades["EntryTime"],
                y=trades["EntryPrice"],
                mode="markers",
                marker=dict(symbol="triangle-up", size=10, color="#1c8f58"),
                name="Entradas",
            )
        )
        figura.add_trace(
            go.Scatter(
                x=trades["ExitTime"],
                y=trades["ExitPrice"],
                mode="markers",
                marker=dict(symbol="x", size=9, color="#225ea8"),
                name="Salidas",
            )
        )

    if trade_abierto:
        figura.add_trace(
            go.Scatter(
                x=[trade_abierto["entry_time"]],
                y=[trade_abierto["entry_price"]],
                mode="markers",
                marker=dict(symbol="diamond", size=11, color="#d08c00"),
                name="Operacion abierta",
            )
        )

    figura.update_layout(
        title="Lector de graficas - modo manual",
        xaxis_title="Fecha",
        yaxis_title="Precio",
        height=640,
        xaxis_rangeslider_visible=False,
    )
    return figura


def crear_grafico_equity(curva_equity: pd.DataFrame) -> go.Figure:
    """Grafico de evolucion del capital."""
    figura = go.Figure(
        data=[
            go.Scatter(
                x=curva_equity.index,
                y=curva_equity["Equity"],
                mode="lines",
                name="Equity",
                line=dict(color="#225ea8", width=2),
            )
        ]
    )
    figura.update_layout(
        title="Curva de equity",
        xaxis_title="Fecha",
        yaxis_title="Capital",
        height=360,
    )
    return figura


def crear_grafico_drawdown(drawdown: pd.Series) -> go.Figure:
    """Grafico del drawdown porcentual."""
    figura = go.Figure(
        data=[
            go.Scatter(
                x=drawdown.index,
                y=drawdown.values,
                mode="lines",
                fill="tozeroy",
                name="Drawdown",
                line=dict(color="#c94f3d", width=2),
            )
        ]
    )
    figura.update_layout(
        title="Drawdown",
        xaxis_title="Fecha",
        yaxis_title="Drawdown (%)",
        height=360,
    )
    return figura


def crear_histograma_operaciones(trades: pd.DataFrame) -> go.Figure:
    """Distribucion de resultados por operacion."""
    figura = px.histogram(
        trades,
        x="PnL",
        nbins=min(max(len(trades), 10), 50),
        title="Distribucion de resultados por operacion",
        color_discrete_sequence=["#b6853f"],
    )
    figura.update_layout(
        xaxis_title="Resultado por operacion",
        yaxis_title="Frecuencia",
        height=360,
        bargap=0.08,
    )
    return figura


def crear_grafico_barras(tabla: pd.DataFrame, columna: str, titulo: str) -> go.Figure:
    """Genera un grafico de barras comparativo por archivo."""
    figura = px.bar(
        tabla,
        x="Archivo",
        y=columna,
        title=titulo,
        color=columna,
        color_continuous_scale="Brwnyl",
    )
    figura.update_layout(height=360, coloraxis_showscale=False)
    return figura


def crear_grafico_equity_comparada(resultados_exitosos: list[dict[str, object]]) -> go.Figure:
    """Compara la equity de varios archivos normalizada a porcentaje."""
    figura = go.Figure()

    for resultado in resultados_exitosos:
        equity = resultado["equity"]
        if equity.empty:
            continue

        serie = equity["Equity"].astype(float)
        normalizada = ((serie / serie.iloc[0]) - 1) * 100

        figura.add_trace(
            go.Scatter(
                x=equity.index,
                y=normalizada.values,
                mode="lines",
                name=acortar_texto(resultado["nombre_dataset"], 26),
            )
        )

    figura.update_layout(
        title="Comparativa de equity normalizada",
        xaxis_title="Fecha",
        yaxis_title="Rendimiento acumulado (%)",
        height=420,
    )
    return figura


def mostrar_metricas(metricas: dict[str, object]):
    """Muestra las metricas principales en una cuadricula compacta."""
    fila_1 = st.columns(5)
    fila_1[0].metric("Rentabilidad total", formatear_numero(metricas["rentabilidad_total"], "%"))
    fila_1[1].metric("Total operaciones", f"{metricas['total_operaciones']}")
    fila_1[2].metric("Win rate", formatear_numero(metricas["win_rate"], "%"))
    fila_1[3].metric("Ratio R/R real", formatear_numero(metricas["ratio_rr_real"]))
    fila_1[4].metric("Drawdown maximo", formatear_numero(metricas["drawdown_maximo"], "%"))

    fila_2 = st.columns(5)
    fila_2[0].metric("Sharpe Ratio", formatear_numero(metricas["sharpe_ratio"]))
    fila_2[1].metric("Profit Factor", formatear_numero(metricas["profit_factor"]))
    fila_2[2].metric("Mejor operacion", formatear_numero(metricas["mejor_operacion"], " $"))
    fila_2[3].metric("Peor operacion", formatear_numero(metricas["peor_operacion"], " $"))
    fila_2[4].metric("Duracion media", formatear_duracion(metricas["duracion_media"]))


def preparar_resumen_motor(stats) -> pd.DataFrame:
    """Convierte el resumen del motor a una tabla amigable."""
    filas = []
    for clave, valor in stats.items():
        if str(clave).startswith("_"):
            continue
        if isinstance(valor, float):
            valor = round(valor, 6)
        filas.append({"Metrica": str(clave), "Valor": str(valor)})
    return pd.DataFrame(filas)


def preparar_fila_guardado(resultado: dict[str, object]) -> dict[str, object]:
    """Extrae un resumen ligero del resultado para persistirlo."""
    if resultado.get("error"):
        return {
            "archivo": resultado["nombre_dataset"],
            "origen": resultado["origen"],
            "ruta": resultado.get("ruta"),
            "error": resultado["error"],
        }

    return {
        "archivo": resultado["nombre_dataset"],
        "origen": resultado["origen"],
        "ruta": resultado.get("ruta"),
        "formato": resultado["formato"],
        "velas": resultado["velas"],
        "inicio": resultado["inicio"],
        "fin": resultado["fin"],
        "pip_size": resultado["pip_size"],
        "metricas": resultado["metricas"],
    }


def construir_tabla_comparativa(resultados: list[dict[str, object]]) -> pd.DataFrame:
    """Construye la tabla resumen del lote."""
    filas = []

    for resultado in resultados:
        if resultado.get("error"):
            continue

        metricas = resultado["metricas"]
        filas.append(
            {
                "Archivo": resultado["nombre_dataset"],
                "Formato": resultado["formato"],
                "Velas": resultado["velas"],
                "Desde": resultado["inicio"],
                "Hasta": resultado["fin"],
                "Rentabilidad total (%)": metricas["rentabilidad_total"],
                "Operaciones": metricas["total_operaciones"],
                "Win rate (%)": metricas["win_rate"],
                "Ratio R/R real": metricas["ratio_rr_real"],
                "Drawdown maximo (%)": metricas["drawdown_maximo"],
                "Sharpe Ratio": metricas["sharpe_ratio"],
                "Profit Factor": metricas["profit_factor"],
                "Mejor operacion ($)": metricas["mejor_operacion"],
                "Peor operacion ($)": metricas["peor_operacion"],
                "Duracion media": formatear_duracion(metricas["duracion_media"]),
            }
        )

    return pd.DataFrame(filas)


def calcular_resumen_global(resultados: list[dict[str, object]]) -> dict[str, object]:
    """Resume un lote completo de backtests."""
    exitosos = [resultado for resultado in resultados if not resultado.get("error")]
    fallidos = [resultado for resultado in resultados if resultado.get("error")]

    if not exitosos:
        return {
            "archivos_totales": len(resultados),
            "archivos_exitosos": 0,
            "archivos_fallidos": len(fallidos),
            "operaciones_totales": 0,
            "rentabilidad_media": None,
            "win_rate_medio": None,
            "mejor_archivo": "N/D",
            "peor_drawdown": None,
        }

    tabla = construir_tabla_comparativa(exitosos)
    indice_mejor = tabla["Rentabilidad total (%)"].idxmax()
    mejor_archivo = tabla.loc[indice_mejor, "Archivo"]

    return {
        "archivos_totales": len(resultados),
        "archivos_exitosos": len(exitosos),
        "archivos_fallidos": len(fallidos),
        "operaciones_totales": int(tabla["Operaciones"].sum()),
        "rentabilidad_media": float(tabla["Rentabilidad total (%)"].mean()),
        "win_rate_medio": float(tabla["Win rate (%)"].mean()),
        "mejor_archivo": mejor_archivo,
        "peor_drawdown": float(tabla["Drawdown maximo (%)"].min()),
    }


@st.cache_data(show_spinner=False, ttl=5)
def listar_archivos_locales(carpeta: str) -> tuple[list[dict[str, object]], str | None]:
    """Busca archivos CSV y ZIP dentro de una carpeta."""
    ruta = Path(carpeta).expanduser()

    if not ruta.exists():
        return [], "La carpeta indicada no existe todavia."

    if not ruta.is_dir():
        return [], "La ruta indicada no es una carpeta."

    archivos = []
    for archivo in sorted(ruta.rglob("*")):
        if not archivo.is_file():
            continue

        relativo_path = archivo.relative_to(ruta)
        if any(parte in DIRECTORIOS_EXCLUIDOS_BIBLIOTECA for parte in relativo_path.parts[:-1]):
            continue

        extension = archivo.suffix.lower()
        if extension not in EXTENSIONES_CARPETA:
            continue

        tamano_mb = archivo.stat().st_size / (1024 * 1024)
        relativo = relativo_path.as_posix()
        etiqueta = f"{relativo}  |  {extension.replace('.', '').upper()}  |  {tamano_mb:.2f} MB"

        archivos.append(
            {
                "ruta": str(archivo),
                "relativo": relativo,
                "extension": extension,
                "tamano_mb": tamano_mb,
                "etiqueta": etiqueta,
            }
        )

    return archivos, None


def recopilar_fuentes(rutas_locales: list[str], archivos_subidos) -> tuple[list[FuenteArchivo], list[dict[str, str]]]:
    """Convierte selecciones locales y subidas en una lista comun de fuentes."""
    fuentes = []
    errores = []
    claves_vistas = set()

    for ruta in rutas_locales:
        try:
            fuente = leer_fuente_local(ruta)
            expandidas = expandir_fuente_archivo(fuente)
            for item in expandidas:
                clave = item.ruta or f"{item.origen}:{item.nombre}:{len(item.contenido)}"
                if clave not in claves_vistas:
                    fuentes.append(item)
                    claves_vistas.add(clave)
        except CSVFormatoError as exc:
            errores.append({"archivo": Path(ruta).name, "detalle": str(exc)})

    for archivo in archivos_subidos or []:
        try:
            fuente = FuenteArchivo(
                nombre=archivo.name,
                contenido=archivo.getvalue(),
                origen="Subida manual",
            )
            expandidas = expandir_fuente_archivo(fuente)
            for item in expandidas:
                clave = item.ruta or f"{item.origen}:{item.nombre}:{len(item.contenido)}"
                if clave not in claves_vistas:
                    fuentes.append(item)
                    claves_vistas.add(clave)
        except CSVFormatoError as exc:
            errores.append({"archivo": archivo.name, "detalle": str(exc)})

    return fuentes, errores


def ejecutar_lote_backtests(
    fuentes: list[FuenteArchivo],
    clase_estrategia,
    parametros_base: dict[str, object],
) -> list[dict[str, object]]:
    """Procesa multiples fuentes y devuelve sus resultados individuales."""
    resultados = []
    progreso = st.progress(0.0)
    estado = st.empty()

    for indice, fuente in enumerate(fuentes, start=1):
        estado.info(f"Procesando {indice}/{len(fuentes)}: {fuente.nombre}")
        try:
            datos, formato = cargar_fuente_ohlcv(fuente)
            pip_size = inferir_tamano_pip(datos)

            parametros = {
                **parametros_base,
                "pip_size": float(pip_size),
            }

            stats = ejecutar_backtest(datos, clase_estrategia, parametros)
            trades = extraer_trades(stats)
            curva_equity = extraer_curva_equity(stats)
            drawdown = calcular_serie_drawdown(curva_equity)

            resultados.append(
                {
                    "nombre_dataset": fuente.nombre,
                    "origen": fuente.origen,
                    "ruta": fuente.ruta,
                    "formato": formato,
                    "pip_size": float(pip_size),
                    "velas": len(datos),
                    "inicio": datos.index.min(),
                    "fin": datos.index.max(),
                    "datos": datos,
                    "metricas": calcular_metricas_resumen(stats),
                    "trades": trades,
                    "equity": curva_equity,
                    "drawdown": drawdown,
                    "resumen_motor": preparar_resumen_motor(stats),
                    "error": None,
                }
            )
        except Exception as exc:
            resultados.append(
                {
                    "nombre_dataset": fuente.nombre,
                    "origen": fuente.origen,
                    "ruta": fuente.ruta,
                    "error": str(exc),
                }
            )

        progreso.progress(indice / len(fuentes))

    progreso.empty()
    estado.empty()
    return resultados


def render_inicio_general(archivos_locales: list[dict[str, object]], error_carpeta: str | None, guardados: list[dict[str, object]], version: str):
    """Pantalla de inicio compartida por 1.1 y 1.3."""
    st.header("Inicio")
    st.write(VERSIONES_APP[version]["descripcion"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Archivos detectados en biblioteca", len(archivos_locales))
    col2.metric("Backtests guardados", len(guardados))
    col3.metric("Version activa", version)

    st.info(
        "Las sesiones de Londres, Nueva York y Asia se aplican sobre la hora del CSV asumiendo que el archivo esta en UTC."
    )

    st.subheader("Resumen")
    st.write(
        "Puedes seleccionar archivos desde una carpeta local o subirlos manualmente. Los ZIP compatibles se expanden automaticamente y cada dataset se procesa por separado."
    )
    st.caption(f"Carpeta activa: {st.session_state['carpeta_datos']}")
    if error_carpeta:
        st.warning(error_carpeta)

    st.subheader("Capturas de pantalla")
    capturas = [
        ("Portada", RUTA_CAPTURAS / "inicio.svg", "Resumen general y accesos rapidos."),
        ("Seleccion", RUTA_CAPTURAS / "fuentes.svg", "Carga de archivos y configuracion del lote."),
        ("Resultados", RUTA_CAPTURAS / "resultados.svg", "Resultados por archivo y comparativa final."),
    ]

    columnas_capturas = st.columns(3)
    for columna, (titulo, ruta, descripcion) in zip(columnas_capturas, capturas):
        with columna:
            if ruta.exists():
                st.image(str(ruta), use_container_width=True)
            st.caption(f"{titulo}: {descripcion}")

    st.subheader("Biblioteca local")
    if error_carpeta:
        st.info("Corrige la ruta de la carpeta en Nuevo backtest para ver archivos aqui.")
    elif archivos_locales:
        preview = pd.DataFrame(archivos_locales).head(8)[["relativo", "extension", "tamano_mb"]]
        preview = preview.rename(
            columns={
                "relativo": "Archivo",
                "extension": "Tipo",
                "tamano_mb": "Tamano (MB)",
            }
        )
        preview["Tamano (MB)"] = preview["Tamano (MB)"].map(lambda valor: f"{valor:.2f}")
        st.dataframe(preview, use_container_width=True, hide_index=True)
    else:
        st.info("Todavia no hay CSV o ZIP detectados en la carpeta activa.")

    st.subheader("Backtests guardados")
    if guardados:
        filas = []
        for item in guardados[:5]:
            resumen = item.get("resumen_global", {})
            filas.append(
                {
                    "Nombre": item.get("nombre_lote", "Sin nombre"),
                    "Fecha": item.get("fecha_guardado", ""),
                    "Estrategia": item.get("estrategia", ""),
                    "Archivos": resumen.get("archivos_exitosos", 0),
                    "Operaciones": resumen.get("operaciones_totales", 0),
                    "Rentabilidad media (%)": resumen.get("rentabilidad_media"),
                }
            )
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    else:
        st.info("Aun no has guardado ningun lote de backtesting.")


def render_guardados(guardados: list[dict[str, object]]):
    """Muestra los backtests guardados en disco."""
    st.header("Guardados")
    st.write("Aqui puedes revisar los lotes guardados localmente y descargar su resumen en JSON.")

    if not guardados:
        st.info("Aun no se ha guardado ningun lote.")
        return

    for indice, item in enumerate(guardados, start=1):
        resumen = item.get("resumen_global", {})
        etiqueta = (
            f"{indice}. {item.get('nombre_lote', 'Sin nombre')} | "
            f"{item.get('fecha_guardado', '')} | "
            f"{resumen.get('archivos_exitosos', 0)} archivos"
        )

        with st.expander(etiqueta):
            metrica_cols = st.columns(4)
            metrica_cols[0].metric("Estrategia", item.get("estrategia", "N/D"))
            metrica_cols[1].metric("Operaciones", resumen.get("operaciones_totales", 0))
            metrica_cols[2].metric(
                "Rentabilidad media",
                formatear_numero(resumen.get("rentabilidad_media"), "%"),
            )
            metrica_cols[3].metric("Fallidos", resumen.get("archivos_fallidos", 0))

            archivos = item.get("archivos", [])
            if archivos:
                filas = []
                for archivo in archivos:
                    filas.append(
                        {
                            "Archivo": archivo.get("archivo"),
                            "Formato": archivo.get("formato", "N/D"),
                            "Velas": archivo.get("velas", "N/D"),
                            "Rentabilidad (%)": (archivo.get("metricas") or {}).get("rentabilidad_total"),
                            "Operaciones": (archivo.get("metricas") or {}).get("total_operaciones"),
                            "Error": archivo.get("error"),
                        }
                    )
                st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

            ruta_json = Path(item["ruta_archivo"])
            st.download_button(
                "Descargar JSON",
                data=ruta_json.read_text(encoding="utf-8"),
                file_name=ruta_json.name,
                mime="application/json",
                key=f"download_guardado_{indice}",
            )


def render_formulario_backtest(
    archivos_locales: list[dict[str, object]],
    error_carpeta: str | None,
    catalogo_estrategias: dict[str, dict[str, object]],
    key_prefix: str,
):
    """Dibuja el formulario principal de configuracion en la barra lateral."""
    with st.sidebar:
        st.markdown("---")
        st.header("Configuracion")
        st.caption("Selecciona fuentes, estrategia y gestion de riesgo.")

        st.text_input(
            "Carpeta local de datos",
            key="carpeta_datos",
            help="Aqui puedes apuntar a la carpeta donde guardas tus CSV y ZIP.",
        )

        if error_carpeta:
            st.warning(error_carpeta)
            seleccion_local = []
        else:
            opciones = [item["ruta"] for item in archivos_locales]
            mapa = {item["ruta"]: item["etiqueta"] for item in archivos_locales}
            seleccion_local = st.multiselect(
                "Selecciona archivos locales",
                options=opciones,
                format_func=lambda ruta: mapa[ruta],
                help="Puedes mezclar CSV y ZIP. Los ZIP se expanden automaticamente.",
                key=f"{key_prefix}_multiselect_local",
            )
            st.caption(f"Archivos disponibles en la biblioteca: {len(archivos_locales)}")

        archivos_subidos = st.file_uploader(
            "O sube archivos manualmente",
            type=["csv", "txt", "zip"],
            accept_multiple_files=True,
            help="Compatible con CSV/TXT OHLCV y ZIP que contengan archivos compatibles.",
            key=f"{key_prefix}_uploader",
        )

        st.markdown("---")
        estrategia_seleccionada = st.selectbox(
            "Estrategia",
            list(catalogo_estrategias.keys()),
            key=f"{key_prefix}_estrategia",
        )
        parametros_estrategia = construir_parametros_estrategia(
            estrategia_seleccionada,
            catalogo_estrategias,
            key_prefix=f"{key_prefix}_param",
        )

        st.markdown("---")
        st.markdown("**Gestion de riesgo**")
        stop_loss_pips = st.number_input(
            "Stop Loss (pips)",
            min_value=1,
            max_value=500,
            value=20,
            step=1,
            key=f"{key_prefix}_sl",
        )
        take_profit_pips = st.number_input(
            "Take Profit (pips)",
            min_value=1,
            max_value=1000,
            value=40,
            step=1,
            key=f"{key_prefix}_tp",
        )
        riesgo_por_operacion = st.number_input(
            "Riesgo por operacion (%)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            key=f"{key_prefix}_riesgo",
        )
        capital_inicial = st.number_input(
            "Capital inicial ($)",
            min_value=100.0,
            max_value=1_000_000.0,
            value=10_000.0,
            step=100.0,
            key=f"{key_prefix}_capital",
        )
        max_operaciones = st.number_input(
            "Maximo de operaciones abiertas",
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            key=f"{key_prefix}_max_ops",
        )
        sesion = st.selectbox("Horario de trading", list(SESIONES_TRADING.keys()), key=f"{key_prefix}_sesion")
        usar_trailing = st.checkbox("Activar trailing stop", value=False, key=f"{key_prefix}_trailing")
        distancia_trailing = st.number_input(
            "Distancia trailing stop (pips)",
            min_value=1,
            max_value=500,
            value=20,
            step=1,
            disabled=not usar_trailing,
            key=f"{key_prefix}_distancia_trailing",
        )

        ejecutar = st.button("Ejecutar lote de backtesting", type="primary", use_container_width=True, key=f"{key_prefix}_ejecutar")

    session_start, session_end = SESIONES_TRADING[sesion]
    parametros = {
        **parametros_estrategia,
        "stop_loss_pips": int(stop_loss_pips),
        "take_profit_pips": int(take_profit_pips),
        "risk_per_trade": float(riesgo_por_operacion),
        "max_open_trades": int(max_operaciones),
        "session_start": int(session_start),
        "session_end": int(session_end),
        "usar_trailing_stop": bool(usar_trailing),
        "trailing_stop_pips": int(distancia_trailing),
        "capital_inicial": float(capital_inicial),
        "leverage": APALANCAMIENTO_POR_DEFECTO,
    }

    return {
        "seleccion_local": seleccion_local,
        "archivos_subidos": archivos_subidos,
        "estrategia": estrategia_seleccionada,
        "parametros": parametros,
        "ejecutar": ejecutar,
        "catalogo_item": catalogo_estrategias[estrategia_seleccionada],
    }


def render_seleccion_actual(
    seleccion_local: list[str],
    archivos_subidos,
    archivos_locales: list[dict[str, object]],
):
    """Muestra en el panel principal la seleccion actual de fuentes."""
    st.subheader("Fuentes seleccionadas")

    if not seleccion_local and not archivos_subidos:
        st.info("Selecciona al menos un archivo local o sube uno manualmente desde la barra lateral.")
        return

    mapa_local = {item["ruta"]: item for item in archivos_locales}
    filas = []

    for ruta in seleccion_local:
        item = mapa_local.get(ruta)
        filas.append(
            {
                "Origen": "Carpeta local",
                "Archivo": item["relativo"] if item else Path(ruta).name,
                "Tipo": item["extension"] if item else Path(ruta).suffix.lower(),
                "Tamano (MB)": f"{item['tamano_mb']:.2f}" if item else "N/D",
            }
        )

    for archivo in archivos_subidos or []:
        tamano_mb = len(archivo.getvalue()) / (1024 * 1024)
        filas.append(
            {
                "Origen": "Subida manual",
                "Archivo": archivo.name,
                "Tipo": Path(archivo.name).suffix.lower(),
                "Tamano (MB)": f"{tamano_mb:.2f}",
            }
        )

    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)


def render_resultado_individual(resultado: dict[str, object], indice: int, key_prefix: str):
    """Renderiza una pestana individual de resultados."""
    st.caption(
        f"Origen: {resultado['origen']} | Formato: {resultado['formato']} | "
        f"Velas: {resultado['velas']:,}".replace(",", ".")
    )

    resumen_archivo = st.columns(4)
    resumen_archivo[0].metric("Desde", resultado["inicio"].strftime("%Y-%m-%d %H:%M:%S"))
    resumen_archivo[1].metric("Hasta", resultado["fin"].strftime("%Y-%m-%d %H:%M:%S"))
    resumen_archivo[2].metric("Pip inferido", f"{resultado['pip_size']}")
    resumen_archivo[3].metric("Operaciones", f"{resultado['metricas']['total_operaciones']}")

    mostrar_metricas(resultado["metricas"])

    st.markdown("---")
    clave_slider = f"{key_prefix}_slider_velas_{indice}_{slugify(resultado['nombre_dataset'])}"
    velas_disponibles = len(resultado["datos"])
    valor_defecto_velas = min(1000, velas_disponibles)
    minimo_slider = min(100, velas_disponibles)

    velas_a_mostrar = st.slider(
        "Velas a mostrar en el grafico principal",
        min_value=minimo_slider,
        max_value=velas_disponibles,
        value=max(minimo_slider, valor_defecto_velas),
        step=50 if velas_disponibles >= 150 else 1,
        key=clave_slider,
    )

    st.plotly_chart(
        crear_grafico_velas(resultado["datos"], resultado["trades"], velas_a_mostrar),
        use_container_width=True,
    )

    col_graficos_1, col_graficos_2 = st.columns(2)
    with col_graficos_1:
        if not resultado["equity"].empty:
            st.plotly_chart(crear_grafico_equity(resultado["equity"]), use_container_width=True)
        else:
            st.info("No hay curva de equity disponible para este archivo.")
    with col_graficos_2:
        if not resultado["drawdown"].empty:
            st.plotly_chart(crear_grafico_drawdown(resultado["drawdown"]), use_container_width=True)
        else:
            st.info("No hay drawdown disponible para este archivo.")

    if not resultado["trades"].empty and "PnL" in resultado["trades"].columns:
        st.plotly_chart(crear_histograma_operaciones(resultado["trades"]), use_container_width=True)
    else:
        st.info("No hubo operaciones cerradas, por lo que no se puede dibujar el histograma.")

    st.subheader("Operaciones ejecutadas")
    if not resultado["trades"].empty:
        st.dataframe(preparar_tabla_operaciones(resultado["trades"]), use_container_width=True)
    else:
        st.warning("La estrategia no genero operaciones en este archivo.")

    with st.expander("Detalle tecnico del motor de backtesting"):
        st.dataframe(resultado["resumen_motor"], use_container_width=True, hide_index=True)


def render_resumen_global(lote_actual: dict[str, object]):
    """Muestra la comparativa general del lote."""
    resultados = lote_actual["resultados"]
    exitosos = [resultado for resultado in resultados if not resultado.get("error")]
    fallidos = [resultado for resultado in resultados if resultado.get("error")]
    tabla = construir_tabla_comparativa(resultados)
    resumen = lote_actual["resumen_global"]

    fila = st.columns(6)
    fila[0].metric("Archivos procesados", resumen["archivos_totales"])
    fila[1].metric("Exitosos", resumen["archivos_exitosos"])
    fila[2].metric("Fallidos", resumen["archivos_fallidos"])
    fila[3].metric("Operaciones totales", resumen["operaciones_totales"])
    fila[4].metric("Rentabilidad media", formatear_numero(resumen["rentabilidad_media"], "%"))
    fila[5].metric("Win rate medio", formatear_numero(resumen["win_rate_medio"], "%"))

    st.caption(f"Mejor archivo del lote: {resumen['mejor_archivo']}")

    if not tabla.empty:
        st.dataframe(tabla, use_container_width=True, hide_index=True)

        if len(tabla) > 1:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(
                    crear_grafico_barras(tabla, "Rentabilidad total (%)", "Rentabilidad por archivo"),
                    use_container_width=True,
                )
            with col2:
                st.plotly_chart(
                    crear_grafico_barras(tabla, "Win rate (%)", "Win rate por archivo"),
                    use_container_width=True,
                )

            st.plotly_chart(
                crear_grafico_equity_comparada(exitosos),
                use_container_width=True,
            )

    if fallidos:
        st.warning("Algunos archivos no pudieron procesarse.")
        tabla_errores = pd.DataFrame(
            [{"Archivo": item["nombre_dataset"], "Origen": item["origen"], "Detalle": item["error"]} for item in fallidos]
        )
        st.dataframe(tabla_errores, use_container_width=True, hide_index=True)


def render_lote_actual(key_resultado: str, key_nombre: str, key_mensaje: str, key_prefix: str):
    """Muestra el lote actual ya procesado."""
    lote_actual = st.session_state.get(key_resultado)
    if not lote_actual:
        return

    st.markdown("---")
    st.subheader("Resultados del lote actual")
    st.caption(
        f"Estrategia: {lote_actual['estrategia']} | Ejecutado: {lote_actual['timestamp']}"
    )

    col_nombre, col_boton = st.columns([2.3, 1])
    with col_nombre:
        nombre_lote = st.text_input(
            "Nombre para guardar este lote",
            key=key_nombre,
        )
    with col_boton:
        st.write("")
        if st.button("Guardar lote", use_container_width=True, key=f"{key_prefix}_guardar_lote"):
            ruta = guardar_backtest_lote(
                nombre_lote or f"Lote {lote_actual['timestamp']}",
                lote_actual["estrategia"],
                lote_actual["parametros"],
                lote_actual["resumen_global"],
                [preparar_fila_guardado(item) for item in lote_actual["resultados"]],
            )
            st.session_state[key_mensaje] = f"Lote guardado en {ruta}"
            st.rerun()

    if st.session_state.get(key_mensaje):
        st.success(st.session_state[key_mensaje])

    exitosos = [item for item in lote_actual["resultados"] if not item.get("error")]
    etiquetas = ["Resumen global"] + [
        f"{indice + 1}. {acortar_texto(item['nombre_dataset'], 24)}"
        for indice, item in enumerate(exitosos)
    ]
    if any(item.get("error") for item in lote_actual["resultados"]):
        etiquetas.append("Errores")

    pestanas = st.tabs(etiquetas)

    with pestanas[0]:
        render_resumen_global(lote_actual)

    for indice, resultado in enumerate(exitosos, start=1):
        with pestanas[indice]:
            render_resultado_individual(resultado, indice, key_prefix=key_prefix)

    if len(pestanas) > len(exitosos) + 1:
        with pestanas[-1]:
            errores = [
                {
                    "Archivo": item["nombre_dataset"],
                    "Origen": item["origen"],
                    "Detalle": item["error"],
                }
                for item in lote_actual["resultados"]
                if item.get("error")
            ]
            st.dataframe(pd.DataFrame(errores), use_container_width=True, hide_index=True)


def ejecutar_y_guardar_lote(formulario: dict[str, object], key_resultado: str, key_nombre: str, key_mensaje: str):
    """Ejecuta el lote segun el formulario y lo guarda en session state."""
    fuentes, errores_fuente = recopilar_fuentes(
        formulario["seleccion_local"],
        formulario["archivos_subidos"],
    )

    if not fuentes:
        st.error("No se encontro ningun archivo valido para procesar.")
        if errores_fuente:
            st.dataframe(pd.DataFrame(errores_fuente), use_container_width=True, hide_index=True)
        return

    clase_estrategia = formulario["catalogo_item"]["clase"]
    resultados = ejecutar_lote_backtests(
        fuentes,
        clase_estrategia,
        formulario["parametros"],
    )

    for error in errores_fuente:
        resultados.append(
            {
                "nombre_dataset": error["archivo"],
                "origen": "Seleccion inicial",
                "ruta": None,
                "error": error["detalle"],
            }
        )

    marca = datetime.now().strftime("%Y-%m-%d %H:%M")
    resumen_global = calcular_resumen_global(resultados)
    st.session_state[key_resultado] = {
        "timestamp": marca,
        "estrategia": formulario["estrategia"],
        "parametros": formulario["parametros"],
        "resultados": resultados,
        "resumen_global": resumen_global,
    }
    st.session_state[key_nombre] = f"Lote {formulario['estrategia']} {marca}"
    st.session_state[key_mensaje] = None


def render_v1_0():
    """Version 1.0 clasica de la aplicacion."""
    st.header("Version 1.0")
    st.write(
        "Modo clasico de la primera app funcional: un archivo por backtest, tres estrategias base y flujo directo."
    )

    catalogo = obtener_catalogo_base(ESTRATEGIAS_CLASICAS)

    with st.sidebar:
        st.markdown("---")
        st.header("Configuracion clasica")
        archivo = st.file_uploader(
            "Sube un CSV OHLCV",
            type=["csv", "txt"],
            help="Compatible con HistData.com, Dukascopy y MetaTrader.",
            key="v10_uploader",
        )

        estrategia_seleccionada = st.selectbox(
            "Estrategia",
            list(catalogo.keys()),
            key="v10_estrategia",
        )
        parametros_estrategia = construir_parametros_estrategia(
            estrategia_seleccionada,
            catalogo,
            key_prefix="v10_param",
        )

        st.markdown("---")
        st.markdown("**Gestion de riesgo**")
        stop_loss_pips = st.number_input("Stop Loss (pips)", min_value=1, max_value=500, value=20, step=1, key="v10_sl")
        take_profit_pips = st.number_input("Take Profit (pips)", min_value=1, max_value=1000, value=40, step=1, key="v10_tp")
        riesgo_por_operacion = st.number_input("Riesgo por operacion (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="v10_riesgo")
        capital_inicial = st.number_input("Capital inicial ($)", min_value=100.0, max_value=1_000_000.0, value=10_000.0, step=100.0, key="v10_capital")
        max_operaciones = st.number_input("Maximo de operaciones abiertas", min_value=1, max_value=20, value=1, step=1, key="v10_max_ops")
        sesion = st.selectbox("Horario de trading", list(SESIONES_TRADING.keys()), key="v10_sesion")
        usar_trailing = st.checkbox("Activar trailing stop", value=False, key="v10_trailing")
        distancia_trailing = st.number_input(
            "Distancia trailing stop (pips)",
            min_value=1,
            max_value=500,
            value=20,
            step=1,
            disabled=not usar_trailing,
            key="v10_distancia_trailing",
        )

        ejecutar = st.button("Ejecutar backtest", type="primary", use_container_width=True, key="v10_ejecutar")

    if not archivo:
        st.info("Sube un archivo CSV para comenzar en la version 1.0.")
        return

    try:
        fuente = FuenteArchivo(nombre=archivo.name, contenido=archivo.getvalue(), origen="Subida manual")
        datos, formato_detectado = cargar_fuente_ohlcv(fuente)
        pip_size = inferir_tamano_pip(datos)
    except Exception as exc:
        st.error(f"No se pudo cargar el archivo: {exc}")
        return

    with st.expander("Resumen del archivo cargado", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Formato detectado", formato_detectado)
        col2.metric("Velas cargadas", f"{len(datos):,}".replace(",", "."))
        col3.metric("Desde", datos.index.min().strftime("%Y-%m-%d %H:%M:%S"))
        col4.metric("Hasta", datos.index.max().strftime("%Y-%m-%d %H:%M:%S"))
        st.caption(f"Tamano de pip inferido automaticamente: {pip_size}")
        st.dataframe(datos.tail(10), use_container_width=True)

    if not ejecutar:
        return

    session_start, session_end = SESIONES_TRADING[sesion]
    parametros = {
        **parametros_estrategia,
        "stop_loss_pips": int(stop_loss_pips),
        "take_profit_pips": int(take_profit_pips),
        "risk_per_trade": float(riesgo_por_operacion),
        "max_open_trades": int(max_operaciones),
        "session_start": int(session_start),
        "session_end": int(session_end),
        "usar_trailing_stop": bool(usar_trailing),
        "trailing_stop_pips": int(distancia_trailing),
        "pip_size": float(pip_size),
        "capital_inicial": float(capital_inicial),
        "leverage": APALANCAMIENTO_POR_DEFECTO,
    }

    try:
        with st.spinner("Ejecutando backtest..."):
            resultados = ejecutar_backtest(datos, catalogo[estrategia_seleccionada]["clase"], parametros)
    except Exception as exc:
        st.error(f"No se pudo ejecutar el backtest: {exc}")
        return

    metricas = calcular_metricas_resumen(resultados)
    trades = extraer_trades(resultados)
    curva_equity = extraer_curva_equity(resultados)
    drawdown = calcular_serie_drawdown(curva_equity)

    st.success("Backtest completado correctamente.")
    mostrar_metricas(metricas)

    st.subheader("Graficos")
    velas_disponibles = len(datos)
    valor_defecto_velas = min(1000, velas_disponibles)
    minimo_slider = min(100, velas_disponibles)
    velas_a_mostrar = st.slider(
        "Velas a mostrar en el grafico principal",
        min_value=minimo_slider,
        max_value=velas_disponibles,
        value=max(minimo_slider, valor_defecto_velas),
        step=50 if velas_disponibles >= 150 else 1,
        key="v10_slider_velas",
    )

    st.plotly_chart(crear_grafico_velas(datos, trades, velas_a_mostrar), use_container_width=True)

    col_graficos_1, col_graficos_2 = st.columns(2)
    with col_graficos_1:
        if not curva_equity.empty:
            st.plotly_chart(crear_grafico_equity(curva_equity), use_container_width=True)
    with col_graficos_2:
        if not drawdown.empty:
            st.plotly_chart(crear_grafico_drawdown(drawdown), use_container_width=True)

    if not trades.empty and "PnL" in trades.columns:
        st.plotly_chart(crear_histograma_operaciones(trades), use_container_width=True)

    st.subheader("Operaciones ejecutadas")
    if not trades.empty:
        st.dataframe(preparar_tabla_operaciones(trades), use_container_width=True)
    else:
        st.warning("La estrategia no genero operaciones con los parametros seleccionados.")


def render_v1_1(archivos_locales: list[dict[str, object]], error_carpeta: str | None, guardados: list[dict[str, object]]):
    """Version 1.1 estable."""
    vista = st.session_state["vista_v11"]
    render_navegacion(["Inicio", "Nuevo backtest", "Guardados"], "vista_v11")
    st.markdown("---")

    resultado_actual = st.session_state.get("resultado_lote_v11")
    render_sidebar_resumen(archivos_locales, guardados, resultado_actual)

    if vista == "Inicio":
        render_inicio_general(archivos_locales, error_carpeta, guardados, version="1.1")
        return

    if vista == "Guardados":
        render_guardados(guardados)
        return

    st.header("Nuevo backtest")
    st.write(
        "Version estable con la interfaz actual: configuracion en barra lateral, biblioteca local, soporte ZIP y resultados por lotes."
    )

    catalogo = obtener_catalogo_base(ESTRATEGIAS_CLASICAS)
    formulario = render_formulario_backtest(archivos_locales, error_carpeta, catalogo, key_prefix="v11")
    render_seleccion_actual(formulario["seleccion_local"], formulario["archivos_subidos"], archivos_locales)

    if formulario["ejecutar"]:
        ejecutar_y_guardar_lote(formulario, "resultado_lote_v11", "nombre_lote_guardado_v11", "mensaje_guardado_v11")

    render_lote_actual("resultado_lote_v11", "nombre_lote_guardado_v11", "mensaje_guardado_v11", "v11")


def calcular_tamano_manual(capital: float, riesgo_pct: float, stop_loss_pips: int, pip_size: float) -> int:
    """Calcula un tamano sencillo de posicion para el modo manual."""
    distancia = stop_loss_pips * pip_size
    riesgo_monetario = capital * (riesgo_pct / 100)
    if distancia <= 0 or riesgo_monetario <= 0:
        return 0
    return max(int(riesgo_monetario / distancia), 1)


def construir_trade_abierto(datos: pd.DataFrame, indice_actual: int, direccion: str, capital: float, riesgo_pct: float, stop_loss_pips: int, take_profit_pips: int, pip_size: float) -> dict[str, object] | None:
    """Crea la estructura de una operacion manual."""
    precio = float(datos["Close"].iloc[indice_actual])
    tamano = calcular_tamano_manual(capital, riesgo_pct, stop_loss_pips, pip_size)
    if tamano <= 0:
        return None

    distancia_sl = stop_loss_pips * pip_size
    distancia_tp = take_profit_pips * pip_size

    if direccion == "long":
        sl = precio - distancia_sl
        tp = precio + distancia_tp
    else:
        sl = precio + distancia_sl
        tp = precio - distancia_tp

    return {
        "direction": direccion,
        "entry_index": indice_actual,
        "entry_time": datos.index[indice_actual],
        "entry_price": precio,
        "size": tamano if direccion == "long" else -tamano,
        "sl": sl,
        "tp": tp,
        "risk_pct": riesgo_pct,
    }


def valorar_trade_abierto(trade: dict[str, object], precio_actual: float) -> float:
    """Calcula el PnL flotante de una operacion abierta."""
    if trade["direction"] == "long":
        return (precio_actual - trade["entry_price"]) * abs(trade["size"])
    return (trade["entry_price"] - precio_actual) * abs(trade["size"])


def cerrar_trade_manual(estado: dict[str, object], precio_salida: float, tiempo_salida, motivo: str):
    """Cierra una operacion manual y actualiza capital y registro."""
    trade = estado.get("trade_abierto")
    if not trade:
        return

    pnl = valorar_trade_abierto(trade, precio_salida)
    estado["capital"] += pnl
    estado["trades"].append(
        {
            "EntryTime": trade["entry_time"],
            "ExitTime": tiempo_salida,
            "EntryPrice": trade["entry_price"],
            "ExitPrice": precio_salida,
            "PnL": pnl,
            "Size": trade["size"],
            "Direction": "Larga" if trade["direction"] == "long" else "Corta",
            "Motivo": motivo,
        }
    )
    estado["trade_abierto"] = None


def registrar_equity_manual(estado: dict[str, object], tiempo, precio_actual: float):
    """Guarda un punto de equity manual incluyendo PnL flotante."""
    equity = estado["capital"]
    if estado.get("trade_abierto"):
        equity += valorar_trade_abierto(estado["trade_abierto"], precio_actual)

    estado["equity_curve"].append({"DateTime": tiempo, "Equity": equity})


def avanzar_manual(estado: dict[str, object], pasos: int = 1):
    """Avanza la reproduccion manual varias velas."""
    datos = estado["datos"]

    for _ in range(pasos):
        if estado["indice_actual"] >= len(datos) - 1:
            break

        estado["indice_actual"] += 1
        fila = datos.iloc[estado["indice_actual"]]
        tiempo = datos.index[estado["indice_actual"]]
        trade = estado.get("trade_abierto")

        if trade:
            if trade["direction"] == "long":
                hit_sl = float(fila["Low"]) <= trade["sl"]
                hit_tp = float(fila["High"]) >= trade["tp"]
                if hit_sl and hit_tp:
                    cerrar_trade_manual(estado, trade["sl"], tiempo, "Stop Loss conservador")
                elif hit_sl:
                    cerrar_trade_manual(estado, trade["sl"], tiempo, "Stop Loss")
                elif hit_tp:
                    cerrar_trade_manual(estado, trade["tp"], tiempo, "Take Profit")
            else:
                hit_sl = float(fila["High"]) >= trade["sl"]
                hit_tp = float(fila["Low"]) <= trade["tp"]
                if hit_sl and hit_tp:
                    cerrar_trade_manual(estado, trade["sl"], tiempo, "Stop Loss conservador")
                elif hit_sl:
                    cerrar_trade_manual(estado, trade["sl"], tiempo, "Stop Loss")
                elif hit_tp:
                    cerrar_trade_manual(estado, trade["tp"], tiempo, "Take Profit")

        registrar_equity_manual(estado, tiempo, float(fila["Close"]))


def preparar_sesion_manual(fuente: FuenteArchivo, capital_inicial: float, riesgo_pct: float, stop_loss_pips: int, take_profit_pips: int):
    """Crea una sesion de replay manual a partir de una fuente."""
    datos, formato = cargar_fuente_ohlcv(fuente)
    pip_size = inferir_tamano_pip(datos)
    indice_inicial = min(max(150, 50), len(datos) - 1)

    st.session_state["manual_v13"] = {
        "nombre": fuente.nombre,
        "origen": fuente.origen,
        "formato": formato,
        "datos": datos,
        "pip_size": pip_size,
        "capital_inicial": capital_inicial,
        "capital": capital_inicial,
        "riesgo_pct": riesgo_pct,
        "stop_loss_pips": stop_loss_pips,
        "take_profit_pips": take_profit_pips,
        "indice_actual": indice_inicial,
        "trade_abierto": None,
        "trades": [],
        "equity_curve": [
            {
                "DateTime": datos.index[indice_inicial],
                "Equity": capital_inicial,
            }
        ],
    }


def obtener_fuente_manual(ruta_local: str | None, archivo_subido) -> tuple[list[FuenteArchivo], list[dict[str, str]]]:
    """Resuelve la fuente del modo manual."""
    rutas = [ruta_local] if ruta_local else []
    archivos = [archivo_subido] if archivo_subido else []
    return recopilar_fuentes(rutas, archivos)


def render_trading_manual(archivos_locales: list[dict[str, object]], error_carpeta: str | None):
    """Vista de trading manual de la version 1.3."""
    st.header("Trading manual")
    st.write(
        "Reproduce el grafico vela a vela, abre operaciones manuales y revisa tu curva de equity como si estuvieras entrenando lectura de mercado."
    )

    with st.sidebar:
        st.markdown("---")
        st.header("Trading manual")

        if error_carpeta:
            st.warning(error_carpeta)
            ruta_local = None
        else:
            opciones = [item["ruta"] for item in archivos_locales]
            mapa = {item["ruta"]: item["etiqueta"] for item in archivos_locales}
            ruta_local = st.selectbox(
                "Archivo local para manual",
                options=[""] + opciones,
                format_func=lambda ruta: "Sin seleccionar" if ruta == "" else mapa[ruta],
                key="v13_manual_local",
            )
            ruta_local = ruta_local or None

        archivo_subido = st.file_uploader(
            "O sube un archivo para manual",
            type=["csv", "txt", "zip"],
            accept_multiple_files=False,
            key="v13_manual_uploader",
        )
        capital = st.number_input("Capital inicial manual ($)", min_value=100.0, max_value=1_000_000.0, value=10_000.0, step=100.0, key="v13_manual_capital")
        riesgo = st.number_input("Riesgo por operacion (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="v13_manual_riesgo")
        sl = st.number_input("Stop Loss manual (pips)", min_value=1, max_value=500, value=20, step=1, key="v13_manual_sl")
        tp = st.number_input("Take Profit manual (pips)", min_value=1, max_value=1000, value=40, step=1, key="v13_manual_tp")

        preparar = st.button("Preparar sesion manual", type="primary", use_container_width=True, key="v13_manual_preparar")

    if preparar:
        fuentes, errores = obtener_fuente_manual(ruta_local, archivo_subido)
        if errores:
            st.error(errores[0]["detalle"])
        elif not fuentes:
            st.error("Selecciona un archivo o sube uno para iniciar la sesion manual.")
        elif len(fuentes) > 1:
            st.warning("La fuente seleccionada contiene varios datasets. Usa un CSV unico o un ZIP con un solo dataset para el modo manual.")
        else:
            try:
                preparar_sesion_manual(fuentes[0], float(capital), float(riesgo), int(sl), int(tp))
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo preparar la sesion manual: {exc}")

    estado = st.session_state.get("manual_v13")
    if not estado:
        st.info("Prepara una sesion manual para empezar a reproducir el grafico.")
        return

    st.caption(
        f"Dataset: {estado['nombre']} | Formato: {estado['formato']} | Origen: {estado['origen']}"
    )

    col_estado_1, col_estado_2, col_estado_3, col_estado_4 = st.columns(4)
    col_estado_1.metric("Capital actual", formatear_numero(estado["capital"], " $"))
    col_estado_2.metric("Trade abierta", "Si" if estado.get("trade_abierto") else "No")
    col_estado_3.metric("Trades cerrados", len(estado["trades"]))
    col_estado_4.metric("Vela actual", str(estado["indice_actual"] + 1))

    fila_controles = st.columns(6)
    if fila_controles[0].button("Comprar", use_container_width=True, disabled=bool(estado.get("trade_abierto")), key="v13_manual_buy"):
        trade = construir_trade_abierto(
            estado["datos"],
            estado["indice_actual"],
            "long",
            estado["capital"],
            estado["riesgo_pct"],
            estado["stop_loss_pips"],
            estado["take_profit_pips"],
            estado["pip_size"],
        )
        if trade:
            estado["trade_abierto"] = trade
            st.rerun()

    if fila_controles[1].button("Vender", use_container_width=True, disabled=bool(estado.get("trade_abierto")), key="v13_manual_sell"):
        trade = construir_trade_abierto(
            estado["datos"],
            estado["indice_actual"],
            "short",
            estado["capital"],
            estado["riesgo_pct"],
            estado["stop_loss_pips"],
            estado["take_profit_pips"],
            estado["pip_size"],
        )
        if trade:
            estado["trade_abierto"] = trade
            st.rerun()

    if fila_controles[2].button("Cerrar trade", use_container_width=True, disabled=not bool(estado.get("trade_abierto")), key="v13_manual_close"):
        indice = estado["indice_actual"]
        fila = estado["datos"].iloc[indice]
        cerrar_trade_manual(estado, float(fila["Close"]), estado["datos"].index[indice], "Cierre manual")
        registrar_equity_manual(estado, estado["datos"].index[indice], float(fila["Close"]))
        st.rerun()

    if fila_controles[3].button("Siguiente vela", use_container_width=True, key="v13_manual_next1"):
        avanzar_manual(estado, 1)
        st.rerun()

    if fila_controles[4].button("+10 velas", use_container_width=True, key="v13_manual_next10"):
        avanzar_manual(estado, 10)
        st.rerun()

    if fila_controles[5].button("Reiniciar", use_container_width=True, key="v13_manual_reset"):
        st.session_state["manual_v13"] = None
        st.rerun()

    datos_visibles = estado["datos"].iloc[: estado["indice_actual"] + 1]
    trades_df = pd.DataFrame(estado["trades"])
    st.plotly_chart(
        crear_grafico_velas_manual(datos_visibles, trades_df, estado.get("trade_abierto")),
        use_container_width=True,
    )

    equity_df = pd.DataFrame(estado["equity_curve"])
    if not equity_df.empty:
        equity_df["DateTime"] = pd.to_datetime(equity_df["DateTime"])
        equity_df = equity_df.set_index("DateTime")
        col_eq, col_dd = st.columns(2)
        with col_eq:
            st.plotly_chart(crear_grafico_equity(equity_df), use_container_width=True)
        with col_dd:
            drawdown = calcular_serie_drawdown(equity_df)
            if not drawdown.empty:
                st.plotly_chart(crear_grafico_drawdown(drawdown), use_container_width=True)

    if estado.get("trade_abierto"):
        trade = estado["trade_abierto"]
        st.info(
            f"Trade abierta: {'Larga' if trade['direction'] == 'long' else 'Corta'} | "
            f"Entrada {trade['entry_price']:.5f} | SL {trade['sl']:.5f} | TP {trade['tp']:.5f}"
        )

    st.subheader("Registro manual")
    if not trades_df.empty:
        tabla = trades_df.rename(
            columns={
                "EntryTime": "Entrada",
                "ExitTime": "Salida",
                "EntryPrice": "Precio entrada",
                "ExitPrice": "Precio salida",
                "PnL": "Resultado",
                "Direction": "Direccion",
                "Motivo": "Motivo",
            }
        )
        st.dataframe(tabla, use_container_width=True, hide_index=True)
    else:
        st.info("Todavia no has cerrado ninguna operacion manual.")


def render_estrategias_v13():
    """Gestiona las estrategias integradas y personalizadas de la version 1.3."""
    st.header("Estrategias")
    st.write(
        "Aqui puedes revisar las estrategias integradas, crear variantes personalizadas y dejarlas guardadas para reutilizarlas en el backtester."
    )

    st.subheader("Estrategias integradas")
    filas = []
    for nombre, configuracion in CONFIGURACION_ESTRATEGIAS.items():
        filas.append(
            {
                "Estrategia": nombre,
                "Descripcion": configuracion["descripcion"],
                "Parametros": len(configuracion["parametros"]),
            }
        )
    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    st.subheader("Crear estrategia personalizada")
    with st.form("form_estrategia_personalizada"):
        nombre = st.text_input("Nombre de la estrategia")
        plantilla = st.selectbox("Plantilla base", list(CONFIGURACION_ESTRATEGIAS.keys()))
        descripcion = st.text_area(
            "Descripcion",
            placeholder="Ejemplo: variante mas rapida del MACD para marcos de 15 minutos.",
        )
        catalogo = obtener_catalogo_base([plantilla])
        parametros = construir_parametros_estrategia(plantilla, catalogo, key_prefix="v13_builder")
        guardar = st.form_submit_button("Guardar estrategia")

    if guardar:
        if not nombre.strip():
            st.error("Ponle un nombre a la estrategia personalizada.")
        else:
            ruta = guardar_estrategia_personalizada(nombre.strip(), plantilla, descripcion.strip(), parametros)
            st.success(f"Estrategia guardada en {ruta.name}")
            st.rerun()

    st.subheader("Estrategias guardadas")
    estrategias_guardadas = listar_estrategias_personalizadas()
    if not estrategias_guardadas:
        st.info("Todavia no has guardado ninguna estrategia personalizada.")
        return

    for indice, item in enumerate(estrategias_guardadas, start=1):
        with st.expander(f"{indice}. {item['nombre']} | Base: {item['plantilla_base']}"):
            st.caption(item.get("fecha_guardado", ""))
            if item.get("descripcion"):
                st.write(item["descripcion"])

            parametros_df = pd.DataFrame(
                [{"Parametro": clave, "Valor": valor} for clave, valor in item.get("parametros", {}).items()]
            )
            if not parametros_df.empty:
                st.dataframe(parametros_df, use_container_width=True, hide_index=True)

            if st.button("Eliminar estrategia", key=f"eliminar_estrategia_{indice}"):
                eliminar_estrategia_personalizada(item["ruta_archivo"])
                st.rerun()


def render_v1_3(archivos_locales: list[dict[str, object]], error_carpeta: str | None, guardados: list[dict[str, object]]):
    """Version 1.3 avanzada."""
    vista = st.session_state["vista_v13"]
    render_navegacion(["Inicio", "Nuevo backtest", "Trading manual", "Estrategias", "Guardados"], "vista_v13")
    st.markdown("---")

    resultado_actual = st.session_state.get("resultado_lote_v13")
    render_sidebar_resumen(archivos_locales, guardados, resultado_actual)

    if vista == "Inicio":
        render_inicio_general(archivos_locales, error_carpeta, guardados, version="1.3")
        return

    if vista == "Trading manual":
        render_trading_manual(archivos_locales, error_carpeta)
        return

    if vista == "Estrategias":
        render_estrategias_v13()
        return

    if vista == "Guardados":
        render_guardados(guardados)
        return

    st.header("Nuevo backtest")
    st.write(
        "La version 1.3 mantiene el flujo de la 1.1 y suma nuevas estrategias integradas y guardadas."
    )

    catalogo = obtener_catalogo_avanzado()
    formulario = render_formulario_backtest(archivos_locales, error_carpeta, catalogo, key_prefix="v13")
    render_seleccion_actual(formulario["seleccion_local"], formulario["archivos_subidos"], archivos_locales)

    if formulario["ejecutar"]:
        ejecutar_y_guardar_lote(formulario, "resultado_lote_v13", "nombre_lote_guardado_v13", "mensaje_guardado_v13")

    render_lote_actual("resultado_lote_v13", "nombre_lote_guardado_v13", "mensaje_guardado_v13", "v13")


def main():
    """Punto de entrada de la aplicacion."""
    st.set_page_config(page_title="Backtester Forex", layout="wide")
    inicializar_estado()

    if not st.session_state["version_activa"]:
        render_selector_version()
        return

    version = st.session_state["version_activa"]
    render_sidebar_version()

    guardados = listar_backtests_guardados()
    archivos_locales, error_carpeta = listar_archivos_locales(st.session_state["carpeta_datos"])

    st.title("Backtester de estrategias Forex")
    st.caption(f"Version activa: {version}")

    if version == "1.0":
        render_v1_0()
    elif version == "1.1":
        render_v1_1(archivos_locales, error_carpeta, guardados)
    else:
        render_v1_3(archivos_locales, error_carpeta, guardados)


if __name__ == "__main__":
    main()
