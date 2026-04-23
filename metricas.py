"""Funciones auxiliares para metricas, tablas y curvas de resultados."""

from __future__ import annotations

import numpy as np
import pandas as pd


def extraer_trades(stats) -> pd.DataFrame:
    """Devuelve las operaciones cerradas con columnas listas para mostrar."""
    trades = getattr(stats, "_trades", pd.DataFrame()).copy()
    if trades.empty:
        return trades

    for columna in ("EntryTime", "ExitTime"):
        if columna in trades.columns:
            trades[columna] = pd.to_datetime(trades[columna], errors="coerce")

    if "Direction" not in trades.columns and "Size" in trades.columns:
        trades["Direction"] = np.where(trades["Size"] > 0, "Larga", "Corta")

    return trades


def extraer_curva_equity(stats) -> pd.DataFrame:
    """Devuelve la curva de equity calculada por backtesting.py."""
    equity = getattr(stats, "_equity_curve", pd.DataFrame()).copy()
    if equity.empty:
        return equity

    equity.index = pd.to_datetime(equity.index, errors="coerce")
    return equity


def calcular_serie_drawdown(curva_equity: pd.DataFrame) -> pd.Series:
    """Calcula drawdown porcentual acumulado a partir del equity."""
    if curva_equity.empty or "Equity" not in curva_equity.columns:
        return pd.Series(dtype=float)

    equity = curva_equity["Equity"].astype(float)
    maximos = equity.cummax()
    drawdown = ((equity / maximos) - 1) * 100
    return drawdown.fillna(0)


def _profit_factor_desde_trades(trades: pd.DataFrame) -> float:
    ganancias = trades.loc[trades["PnL"] > 0, "PnL"].sum()
    perdidas = abs(trades.loc[trades["PnL"] < 0, "PnL"].sum())
    if perdidas == 0:
        return np.nan if ganancias == 0 else float("inf")
    return float(ganancias / perdidas)


def _ratio_rr_real(trades: pd.DataFrame) -> float:
    media_ganadora = trades.loc[trades["PnL"] > 0, "PnL"].mean()
    media_perdedora = trades.loc[trades["PnL"] < 0, "PnL"].abs().mean()
    if pd.isna(media_ganadora) or pd.isna(media_perdedora) or media_perdedora == 0:
        return np.nan
    return float(media_ganadora / media_perdedora)


def calcular_metricas_resumen(stats) -> dict[str, object]:
    """Agrupa las metricas principales para mostrarlas en la interfaz."""
    trades = extraer_trades(stats)

    profit_factor = stats.get("Profit Factor", np.nan)
    if pd.isna(profit_factor) and not trades.empty and "PnL" in trades.columns:
        profit_factor = _profit_factor_desde_trades(trades)

    mejor_operacion = trades["PnL"].max() if not trades.empty else np.nan
    peor_operacion = trades["PnL"].min() if not trades.empty else np.nan
    duracion_media = trades["Duration"].mean() if not trades.empty and "Duration" in trades else pd.NaT

    return {
        "rentabilidad_total": float(stats.get("Return [%]", np.nan)),
        "total_operaciones": int(stats.get("# Trades", 0)),
        "win_rate": float(stats.get("Win Rate [%]", np.nan)),
        "ratio_rr_real": _ratio_rr_real(trades) if not trades.empty else np.nan,
        "drawdown_maximo": float(stats.get("Max. Drawdown [%]", np.nan)),
        "sharpe_ratio": float(stats.get("Sharpe Ratio", np.nan)),
        "profit_factor": float(profit_factor) if not pd.isna(profit_factor) else np.nan,
        "mejor_operacion": float(mejor_operacion) if not pd.isna(mejor_operacion) else np.nan,
        "peor_operacion": float(peor_operacion) if not pd.isna(peor_operacion) else np.nan,
        "duracion_media": duracion_media,
    }


def formatear_numero(valor: object, sufijo: str = "", decimales: int = 2) -> str:
    """Formatea valores numericos de forma consistente."""
    if valor is None or pd.isna(valor):
        return "N/D"
    if valor == float("inf"):
        return "Infinito"
    return f"{valor:,.{decimales}f}{sufijo}".replace(",", "_").replace(".", ",").replace("_", ".")


def formatear_duracion(valor: object) -> str:
    """Convierte un Timedelta a un texto mas legible."""
    if valor is None or pd.isna(valor):
        return "N/D"

    duracion = pd.to_timedelta(valor)
    total_minutos = int(duracion.total_seconds() // 60)
    dias, resto_minutos = divmod(total_minutos, 1440)
    horas, minutos = divmod(resto_minutos, 60)

    partes = []
    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos or not partes:
        partes.append(f"{minutos}m")

    return " ".join(partes)


def preparar_tabla_operaciones(trades: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una tabla con nombres de columnas en espanol."""
    if trades.empty:
        return trades

    tabla = trades.copy()
    columnas = {
        "EntryTime": "Entrada",
        "ExitTime": "Salida",
        "EntryPrice": "Precio entrada",
        "ExitPrice": "Precio salida",
        "PnL": "Resultado",
        "ReturnPct": "Retorno %",
        "Size": "Tamano",
        "Duration": "Duracion",
        "Direction": "Direccion",
    }

    disponibles = [col for col in columnas if col in tabla.columns]
    tabla = tabla[disponibles].rename(columns=columnas)

    if "Duracion" in tabla.columns:
        tabla["Duracion"] = tabla["Duracion"].apply(formatear_duracion)

    return tabla
