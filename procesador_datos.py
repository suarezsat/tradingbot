"""Carga y normalizacion de datos OHLCV para la app de backtesting Forex."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

import pandas as pd


class CSVFormatoError(ValueError):
    """Error controlado para mostrar mensajes claros en la interfaz."""


@dataclass(frozen=True)
class FuenteArchivo:
    """Representa un archivo listo para ser procesado o expandido."""

    nombre: str
    contenido: bytes
    origen: str
    ruta: str | None = None


FORMATOS_COMPATIBLES = {
    "histdata": {
        "columnas": ["DateTime", "Open", "High", "Low", "Close", "Volume"],
        "descripcion": "HistData.com",
    },
    "dukascopy": {
        "columnas": ["Time", "Open", "High", "Low", "Close", "Volume"],
        "descripcion": "Dukascopy",
    },
    "metatrader": {
        "columnas": ["Date", "Time", "Open", "High", "Low", "Close", "Volume"],
        "descripcion": "MetaTrader (MT4/MT5)",
    },
}


def _decodificar_contenido(contenido: bytes) -> str:
    """Intenta decodificar el archivo con codificaciones habituales."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return contenido.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise CSVFormatoError(
        "No se pudo leer el archivo. Guarda el CSV en UTF-8 o Latin-1 e intentalo de nuevo."
    )


def _detectar_formato_texto(texto: str) -> tuple[str, str]:
    """Detecta el formato del archivo y el separador usado sobre texto ya decodificado."""
    primera_linea = next((linea.strip() for linea in texto.splitlines() if linea.strip()), "")

    if not primera_linea:
        raise CSVFormatoError("El archivo esta vacio o no contiene una cabecera valida.")

    for separador in (";", ",", "\t"):
        columnas = [col.strip() for col in primera_linea.split(separador)]

        if columnas == FORMATOS_COMPATIBLES["histdata"]["columnas"]:
            return "histdata", separador
        if columnas == FORMATOS_COMPATIBLES["dukascopy"]["columnas"]:
            return "dukascopy", separador
        if columnas[:7] == FORMATOS_COMPATIBLES["metatrader"]["columnas"]:
            return "metatrader", separador

    if re.fullmatch(
        r"\d{8}\s\d{6};[-+]?\d+(?:[.,]\d+)?;[-+]?\d+(?:[.,]\d+)?;[-+]?\d+(?:[.,]\d+)?;[-+]?\d+(?:[.,]\d+)?;[-+]?\d+(?:[.,]\d+)?",
        primera_linea,
    ):
        return "histdata_sin_cabecera", ";"

    if re.fullmatch(
        r"\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2}:\d{2},[-+]?\d+(?:[.,]\d+)?(?:,[-+]?\d+(?:[.,]\d+)?){4}",
        primera_linea,
    ):
        return "dukascopy_sin_cabecera", ","

    raise CSVFormatoError(
        "Formato CSV no reconocido. Usa un archivo HistData, Dukascopy o MetaTrader con columnas OHLCV."
    )


def detectar_formato_csv(contenido: bytes) -> tuple[str, str]:
    """Detecta el formato del archivo y el separador usado."""
    return _detectar_formato_texto(_decodificar_contenido(contenido))


def _recortar_texto_csv(texto: str, max_filas: int | None) -> str:
    """Conserva solo las ultimas filas utiles manteniendo cabecera si existe."""
    if not max_filas or max_filas <= 0:
        return texto

    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    if len(lineas) <= max_filas + 1:
        return texto

    primera_linea = lineas[0].strip().lower()
    tiene_cabecera = any(
        columna in primera_linea
        for columna in ("datetime", "time", "date", "open", "high", "low", "close")
    )

    if tiene_cabecera:
        return "\n".join([lineas[0], *lineas[-max_filas:]])

    return "\n".join(lineas[-max_filas:])


def _leer_csv(
    texto: str,
    separador: str,
    nombres_columnas: list[str] | None = None,
    sin_cabecera: bool = False,
) -> pd.DataFrame:
    """Lee el CSV ya decodificado preservando los nombres de columnas."""
    try:
        return pd.read_csv(
            StringIO(texto),
            sep=separador,
            engine="python",
            skip_blank_lines=True,
            header=None if sin_cabecera else 0,
            names=nombres_columnas,
        )
    except Exception as exc:  # pragma: no cover - error de libreria
        raise CSVFormatoError(f"No se pudo leer el archivo CSV: {exc}") from exc


def _parsear_fechas_multiples(serie: pd.Series, formatos: list[str]) -> pd.Series:
    """Prueba varios formatos tipicos de fecha hasta encontrar uno valido."""
    resultado = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")

    for formato in formatos:
        faltantes = resultado.isna()
        if not faltantes.any():
            break
        resultado.loc[faltantes] = pd.to_datetime(
            serie.loc[faltantes],
            format=formato,
            errors="coerce",
        )

    faltantes = resultado.isna()
    if faltantes.any():
        resultado.loc[faltantes] = pd.to_datetime(
            serie.loc[faltantes],
            errors="coerce",
            dayfirst=True,
        )

    return resultado


def _normalizar_numeros(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Convierte columnas numericas a float limpiando espacios y separadores."""
    for columna in columnas:
        serie = (
            df[columna]
            .astype(str)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[columna] = pd.to_numeric(serie, errors="coerce")
    return df


def _normalizar_dataframe(df: pd.DataFrame, columna_fecha: pd.Series) -> pd.DataFrame:
    """Devuelve un DataFrame con el formato requerido por backtesting.py."""
    columnas_ohlcv = ["Open", "High", "Low", "Close", "Volume"]
    faltantes = [col for col in columnas_ohlcv if col not in df.columns]
    if faltantes:
        raise CSVFormatoError(
            f"Faltan columnas obligatorias en el CSV: {', '.join(faltantes)}."
        )

    df = _normalizar_numeros(df.copy(), columnas_ohlcv)
    df["Date"] = columna_fecha
    df = df.dropna(subset=["Date"] + columnas_ohlcv)

    if df.empty:
        raise CSVFormatoError(
            "No se encontraron filas validas despues de procesar fechas y precios."
        )

    datos = (
        df[["Date"] + columnas_ohlcv]
        .rename(columns={"Date": "DateTime"})
        .set_index("DateTime")
        .sort_index()
    )

    datos = datos[~datos.index.duplicated(keep="first")]

    if len(datos) < 50:
        raise CSVFormatoError(
            "El archivo tiene muy pocas velas para hacer un backtest fiable. Sube al menos 50 filas."
        )

    return datos


def cargar_contenido_ohlcv(contenido: bytes, max_filas: int | None = None) -> tuple[pd.DataFrame, str]:
    """Normaliza contenido en bruto a un DataFrame OHLCV."""
    texto = _decodificar_contenido(contenido)
    formato, separador = _detectar_formato_texto(texto)
    texto = _recortar_texto_csv(texto, max_filas)
    sin_cabecera = formato.endswith("_sin_cabecera")

    if formato == "histdata_sin_cabecera":
        formato_base = "histdata"
        nombres_columnas = FORMATOS_COMPATIBLES["histdata"]["columnas"]
    elif formato == "dukascopy_sin_cabecera":
        formato_base = "dukascopy"
        nombres_columnas = FORMATOS_COMPATIBLES["dukascopy"]["columnas"]
    else:
        formato_base = formato
        nombres_columnas = None

    df = _leer_csv(
        texto,
        separador,
        nombres_columnas=nombres_columnas,
        sin_cabecera=sin_cabecera,
    )

    if formato_base == "histdata":
        fechas = pd.to_datetime(
            df["DateTime"].astype(str).str.strip(),
            format="%Y%m%d %H%M%S",
            errors="coerce",
        )
    elif formato_base == "dukascopy":
        fechas = pd.to_datetime(
            df["Time"].astype(str).str.strip(),
            format="%d.%m.%Y %H:%M:%S",
            errors="coerce",
        )
    else:
        combinada = (
            df["Date"].astype(str).str.strip() + " " + df["Time"].astype(str).str.strip()
        )
        fechas = _parsear_fechas_multiples(
            combinada,
            [
                "%Y.%m.%d %H:%M",
                "%Y.%m.%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%d.%m.%Y %H:%M",
                "%d.%m.%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y %H:%M:%S",
            ],
        )

    datos = _normalizar_dataframe(df, fechas)
    return datos, FORMATOS_COMPATIBLES[formato_base]["descripcion"]


def cargar_csv_ohlcv(archivo) -> tuple[pd.DataFrame, str]:
    """Carga el archivo subido en Streamlit y lo normaliza a OHLCV."""
    return cargar_contenido_ohlcv(archivo.getvalue())


def cargar_fuente_ohlcv(fuente: FuenteArchivo, max_filas: int | None = None) -> tuple[pd.DataFrame, str]:
    """Carga una fuente genetrica ya sea local, subida o extraida de un ZIP."""
    return cargar_contenido_ohlcv(fuente.contenido, max_filas=max_filas)


def leer_fuente_local(ruta: str | Path) -> FuenteArchivo:
    """Lee un archivo del disco para usarlo dentro de la app."""
    ruta_archivo = Path(ruta)

    if not ruta_archivo.exists():
        raise CSVFormatoError(f"No se encontro el archivo local: {ruta_archivo}")

    if not ruta_archivo.is_file():
        raise CSVFormatoError(f"La ruta indicada no es un archivo valido: {ruta_archivo}")

    try:
        contenido = ruta_archivo.read_bytes()
    except OSError as exc:
        raise CSVFormatoError(f"No se pudo leer el archivo local {ruta_archivo.name}: {exc}") from exc

    return FuenteArchivo(
        nombre=ruta_archivo.name,
        contenido=contenido,
        origen="Carpeta local",
        ruta=str(ruta_archivo),
    )


def _extraer_fuentes_zip(fuente: FuenteArchivo) -> list[FuenteArchivo]:
    """Expande un ZIP y se queda solo con archivos OHLCV reconocibles."""
    fuentes = []

    try:
        with ZipFile(BytesIO(fuente.contenido)) as archivo_zip:
            for info in archivo_zip.infolist():
                if info.is_dir():
                    continue

                ruta_interna = info.filename.replace("\\", "/")
                extension = Path(ruta_interna).suffix.lower()
                if extension not in {".csv", ".txt"}:
                    continue

                contenido = archivo_zip.read(info.filename)
                try:
                    detectar_formato_csv(contenido)
                except CSVFormatoError:
                    continue

                fuentes.append(
                    FuenteArchivo(
                        nombre=f"{Path(fuente.nombre).name} / {ruta_interna}",
                        contenido=contenido,
                        origen=f"{fuente.origen} / ZIP",
                        ruta=f"{fuente.ruta}::{ruta_interna}" if fuente.ruta else f"{fuente.nombre}::{ruta_interna}",
                    )
                )
    except BadZipFile as exc:
        raise CSVFormatoError(
            f"El archivo {fuente.nombre} no es un ZIP valido o esta dañado."
        ) from exc

    if not fuentes:
        raise CSVFormatoError(
            f"El ZIP {fuente.nombre} no contiene ningun CSV/TXT OHLCV compatible."
        )

    return fuentes


def expandir_fuente_archivo(fuente: FuenteArchivo) -> list[FuenteArchivo]:
    """Devuelve una o varias fuentes segun el tipo de archivo."""
    if Path(fuente.nombre).suffix.lower() == ".zip":
        return _extraer_fuentes_zip(fuente)
    return [fuente]


def inferir_tamano_pip(datos: pd.DataFrame) -> float:
    """Aproxima el tamano de pip segun el rango de precios del activo."""
    precio_medio = float(datos["Close"].median())
    return 0.01 if precio_medio >= 20 else 0.0001
