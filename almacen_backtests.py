"""Persistencia local de backtests guardados."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


DIRECTORIO_BACKTESTS = Path(__file__).resolve().parent / "backtests_guardados"


def asegurar_directorio_guardados() -> Path:
    """Crea el directorio de guardado si todavia no existe."""
    DIRECTORIO_BACKTESTS.mkdir(parents=True, exist_ok=True)
    return DIRECTORIO_BACKTESTS


def _slugify(texto: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", texto.strip()).strip("-").lower()
    return limpio or "backtest"


def _serializar_valor(valor):
    """Convierte tipos de pandas y numpy a estructuras JSON simples."""
    if isinstance(valor, Path):
        return str(valor)

    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()

    if isinstance(valor, pd.Timedelta):
        return str(valor)

    if isinstance(valor, dict):
        return {str(clave): _serializar_valor(item) for clave, item in valor.items()}

    if isinstance(valor, (list, tuple)):
        return [_serializar_valor(item) for item in valor]

    if hasattr(valor, "item"):
        try:
            valor = valor.item()
        except Exception:
            pass

    if isinstance(valor, float):
        if math.isnan(valor):
            return None
        if math.isinf(valor):
            return "inf" if valor > 0 else "-inf"

    return valor


def guardar_backtest_lote(
    nombre_lote: str,
    estrategia: str,
    parametros: dict[str, object],
    resumen_global: dict[str, object],
    resultados_archivos: list[dict[str, object]],
) -> Path:
    """Guarda un lote de resultados en formato JSON."""
    directorio = asegurar_directorio_guardados()
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{marca_tiempo}_{_slugify(nombre_lote)}.json"
    ruta = directorio / nombre_archivo

    payload = {
        "nombre_lote": nombre_lote,
        "fecha_guardado": datetime.now().isoformat(timespec="seconds"),
        "estrategia": estrategia,
        "parametros": _serializar_valor(parametros),
        "resumen_global": _serializar_valor(resumen_global),
        "archivos": _serializar_valor(resultados_archivos),
    }

    ruta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


def listar_backtests_guardados() -> list[dict[str, object]]:
    """Devuelve los backtests guardados ordenados del mas reciente al mas antiguo."""
    directorio = asegurar_directorio_guardados()
    resultados = []

    for ruta in sorted(directorio.glob("*.json"), reverse=True):
        try:
            payload = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            continue

        payload["ruta_archivo"] = str(ruta)
        resultados.append(payload)

    return resultados
