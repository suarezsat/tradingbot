"""Busqueda amplia y validacion robusta de estrategias Forex sobre HistData."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd
from backtesting import Backtest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from estrategias import CONFIGURACION_ESTRATEGIAS
from metricas import calcular_metricas_resumen
from procesador_datos import cargar_fuente_ohlcv, inferir_tamano_pip, leer_fuente_local


SESIONES = {
    "Sin filtro": (-1, -1),
    "Londres": (8, 17),
    "Nueva York": (13, 22),
    "Asiatica": (0, 9),
}

PARES_NUCLEO = ["EURUSD", "GBPUSD", "USDJPY"]
PARES_AMPLIADOS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"]

ESPACIO_COMUN = {
    "stop_loss_pips": [6, 8, 10, 12, 15, 20, 25, 30, 40, 50],
    "take_profit_pips": [12, 16, 20, 24, 30, 40, 60, 80, 100, 120, 160],
    "usar_trailing_stop": [False, True],
    "trailing_stop_pips": [8, 12, 15, 20, 30],
    "session_label": list(SESIONES.keys()),
}

ESPACIOS_ESTRATEGIA = {
    "Cruce de Medias Moviles": {
        "ema_rapida": [5, 8, 10, 12, 15, 20, 30],
        "ema_lenta": [30, 50, 80, 100, 150, 200],
    },
    "RSI con niveles": {
        "rsi_periodo": [4, 7, 10, 14, 21],
        "nivel_sobrecompra": [65, 70, 75, 80, 85],
        "nivel_sobreventa": [15, 20, 25, 30, 35],
    },
    "Bollinger + RSI": {
        "bollinger_periodo": [10, 20, 30, 40, 50],
        "desviaciones": [1.5, 2.0, 2.5, 3.0],
        "rsi_periodo": [7, 14, 21],
    },
    "MACD clasico": {
        "macd_rapido": [6, 8, 12, 16],
        "macd_lento": [18, 24, 26, 32, 40],
        "macd_signal": [5, 9, 12],
    },
    "Donchian Breakout": {
        "donchian_periodo": [10, 20, 30, 40, 55, 80],
    },
    "EMA + RSI tendencia": {
        "ema_rapida": [10, 20, 30],
        "ema_lenta": [50, 100, 150, 200],
        "rsi_periodo": [7, 14, 21],
        "rsi_largo": [52, 55, 60, 65],
        "rsi_corto": [35, 40, 45, 48],
    },
    "Estocastico extremo": {
        "stoch_k": [5, 9, 14, 21],
        "stoch_d": [3, 5, 7],
        "nivel_sobrecompra": [75, 80, 85, 90],
        "nivel_sobreventa": [10, 15, 20, 25],
    },
    "Donchian + EMA": {
        "donchian_periodo": [10, 20, 30, 40, 55, 80],
        "ema_tendencia": [50, 100, 150, 200, 300],
    },
    "RSI2 con tendencia": {
        "ema_tendencia": [50, 100, 150, 200, 300],
        "rsi_periodo": [2, 3, 4, 5],
        "umbral_largo": [5, 10, 15, 20, 25],
        "umbral_corto": [75, 80, 85, 90, 95],
    },
    "Ruptura de sesion": {
        "hora_inicio_utc": [7, 8, 12, 13],
        "minutos_rango": [15, 30, 45, 60, 90],
        "hora_fin_operativa": [10, 11, 12, 14, 16],
        "buffer_pips": [0.0, 0.5, 1.0, 1.5, 2.0, 3.0],
    },
}


def _valor_defecto_estrategia(nombre: str) -> dict[str, object]:
    return {
        parametro.clave: parametro.valor_defecto
        for parametro in CONFIGURACION_ESTRATEGIAS[nombre]["parametros"]
    }


def _es_parametrizacion_valida(nombre: str, parametros: dict[str, object]) -> bool:
    if parametros["take_profit_pips"] < parametros["stop_loss_pips"]:
        return False

    if nombre in {"Cruce de Medias Moviles", "EMA + RSI tendencia"}:
        if parametros["ema_rapida"] >= parametros["ema_lenta"]:
            return False

    if nombre == "RSI con niveles":
        if parametros["nivel_sobreventa"] >= parametros["nivel_sobrecompra"]:
            return False

    if nombre == "MACD clasico":
        if parametros["macd_rapido"] >= parametros["macd_lento"]:
            return False

    if nombre == "EMA + RSI tendencia":
        if parametros["rsi_corto"] >= parametros["rsi_largo"]:
            return False

    if nombre == "Estocastico extremo":
        if parametros["stoch_d"] > parametros["stoch_k"]:
            return False
        if parametros["nivel_sobreventa"] >= parametros["nivel_sobrecompra"]:
            return False

    if nombre == "Ruptura de sesion":
        fin_rango = parametros["hora_inicio_utc"] * 60 + parametros["minutos_rango"]
        fin_operativa = parametros["hora_fin_operativa"] * 60
        if fin_rango >= fin_operativa:
            return False
        if (fin_operativa - fin_rango) < 15:
            return False
        if parametros["session_label"] != "Sin filtro":
            return False

    return True


def generar_candidatos(nombre: str, cantidad: int, semilla: int) -> list[dict[str, object]]:
    """Crea combinaciones aleatorias unicas respetando restricciones basicas."""
    aleatorio = random.Random(semilla)
    base = {
        **_valor_defecto_estrategia(nombre),
        "stop_loss_pips": 20,
        "take_profit_pips": 40,
        "usar_trailing_stop": False,
        "trailing_stop_pips": 15,
        "session_label": "Sin filtro",
    }

    candidatos = {json.dumps(base, sort_keys=True): base}
    espacio = {**ESPACIO_COMUN, **ESPACIOS_ESTRATEGIA[nombre]}
    claves = list(espacio.keys())
    max_intentos = max(cantidad * 400, 1000)
    intentos = 0

    while len(candidatos) < cantidad and intentos < max_intentos:
        intentos += 1
        candidato = {clave: aleatorio.choice(espacio[clave]) for clave in claves}
        if not _es_parametrizacion_valida(nombre, candidato):
            continue
        clave_json = json.dumps(candidato, sort_keys=True)
        candidatos[clave_json] = candidato

    return list(candidatos.values())[:cantidad]


def encontrar_csv_anual(pair: str, year: int) -> Path:
    patron = f"*_{pair}/{year}/full_year/extracted/DAT_ASCII_{pair}_M1_{year}.csv"
    coincidencias = sorted((ROOT / "data" / "histdata_ascii_m1").glob(patron))
    if not coincidencias:
        raise FileNotFoundError(f"No se encontro dataset anual para {pair} {year}")
    return coincidencias[0]


@lru_cache(maxsize=64)
def cargar_dataset(path_str: str) -> tuple[pd.DataFrame, float]:
    """Carga el CSV una vez por proceso y reaprovecha el DataFrame en tareas sucesivas."""
    fuente = leer_fuente_local(Path(path_str))
    datos, _ = cargar_fuente_ohlcv(fuente)
    return datos, float(inferir_tamano_pip(datos))


def _valor_float(valor: object, defecto: float = float("nan")) -> float:
    if valor is None:
        return defecto
    try:
        if pd.isna(valor):
            return defecto
    except TypeError:
        pass
    return float(valor)


def puntuar_metricas(metricas: dict[str, object]) -> float:
    """Score robusto que penaliza drawdown, poca muestra y factores fragiles."""
    trades = int(metricas.get("total_operaciones", 0))
    if trades < 15:
        return -150 + trades

    retorno = _valor_float(metricas.get("rentabilidad_total"), -1000.0)
    drawdown = abs(_valor_float(metricas.get("drawdown_maximo"), -100.0))
    profit_factor = _valor_float(metricas.get("profit_factor"), 0.0)
    sharpe = _valor_float(metricas.get("sharpe_ratio"), -2.0)
    ratio_rr = _valor_float(metricas.get("ratio_rr_real"), 0.5)

    score = retorno
    score -= max(drawdown - 20.0, 0.0) * 1.5
    score += min(max((profit_factor - 1.0) * 15.0, -25.0), 35.0)
    score += min(max(sharpe * 8.0, -20.0), 24.0)
    score += min(max((ratio_rr - 1.0) * 4.0, -10.0), 12.0)
    return float(score)


def resumir_resultados(resultados: dict[str, dict[str, object]], dataset_ids: list[str]) -> dict[str, object]:
    validos = [resultados[dataset_id] for dataset_id in dataset_ids if dataset_id in resultados and not resultados[dataset_id].get("error")]
    errores = [resultados[dataset_id] for dataset_id in dataset_ids if dataset_id in resultados and resultados[dataset_id].get("error")]

    if not validos:
        return {
            "datasets_ok": 0,
            "datasets_error": len(errores),
            "avg_score": -9999.0,
            "avg_return": float("nan"),
            "median_return": float("nan"),
            "avg_drawdown": float("nan"),
            "avg_profit_factor": float("nan"),
            "avg_sharpe": float("nan"),
            "avg_trades": float("nan"),
        }

    def promedio(clave: str) -> float:
        valores = [_valor_float(item["metricas"].get(clave)) for item in validos]
        valores = [valor for valor in valores if not math.isnan(valor)]
        return float(statistics.mean(valores)) if valores else float("nan")

    retornos = [_valor_float(item["metricas"].get("rentabilidad_total")) for item in validos]
    retornos = [valor for valor in retornos if not math.isnan(valor)]

    return {
        "datasets_ok": len(validos),
        "datasets_error": len(errores),
        "avg_score": float(statistics.mean(item["score"] for item in validos)),
        "avg_return": promedio("rentabilidad_total"),
        "median_return": float(statistics.median(retornos)) if retornos else float("nan"),
        "avg_drawdown": promedio("drawdown_maximo"),
        "avg_profit_factor": promedio("profit_factor"),
        "avg_sharpe": promedio("sharpe_ratio"),
        "avg_trades": promedio("total_operaciones"),
    }


def ejecutar_en_dataset(
    strategy_name: str,
    parametros: dict[str, object],
    dataset: dict[str, object],
    spread_pips: float,
) -> dict[str, object]:
    datos, pip_size = cargar_dataset(dataset["path"])
    clase = CONFIGURACION_ESTRATEGIAS[strategy_name]["clase"]
    session_start, session_end = SESIONES[parametros["session_label"]]
    spread_rate = (spread_pips * pip_size) / max(float(datos["Close"].median()), 1e-9)

    motor = Backtest(
        datos,
        clase,
        cash=10_000,
        spread=spread_rate,
        commission=0.0,
        margin=1 / 30.0,
        trade_on_close=False,
        hedging=False,
        exclusive_orders=False,
        finalize_trades=True,
    )

    parametros_run = {
        clave: valor
        for clave, valor in parametros.items()
        if clave != "session_label"
    }
    parametros_run.update(
        {
            "risk_per_trade": 1.0,
            "max_open_trades": 1,
            "session_start": session_start,
            "session_end": session_end,
            "pip_size": pip_size,
        }
    )

    try:
        stats = motor.run(**parametros_run)
        metricas = calcular_metricas_resumen(stats)
        score = puntuar_metricas(metricas)
        return {
            "dataset_id": dataset["id"],
            "pair": dataset["pair"],
            "year": dataset["year"],
            "metricas": {
                "rentabilidad_total": _valor_float(metricas.get("rentabilidad_total")),
                "total_operaciones": int(metricas.get("total_operaciones", 0)),
                "win_rate": _valor_float(metricas.get("win_rate")),
                "ratio_rr_real": _valor_float(metricas.get("ratio_rr_real")),
                "drawdown_maximo": _valor_float(metricas.get("drawdown_maximo")),
                "sharpe_ratio": _valor_float(metricas.get("sharpe_ratio")),
                "profit_factor": _valor_float(metricas.get("profit_factor")),
                "mejor_operacion": _valor_float(metricas.get("mejor_operacion")),
                "peor_operacion": _valor_float(metricas.get("peor_operacion")),
                "duracion_media": str(metricas.get("duracion_media")),
            },
            "score": score,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - depende del motor
        return {
            "dataset_id": dataset["id"],
            "pair": dataset["pair"],
            "year": dataset["year"],
            "metricas": {},
            "score": -9999.0,
            "error": str(exc),
        }


def evaluar_candidato(
    phase_name: str,
    strategy_name: str,
    candidate_index: int,
    parametros: dict[str, object],
    datasets: list[dict[str, object]],
    spread_pips: float,
) -> dict[str, object]:
    resultados_por_dataset = {}
    for dataset in datasets:
        resultado = ejecutar_en_dataset(strategy_name, parametros, dataset, spread_pips)
        resultados_por_dataset[dataset["id"]] = resultado

    resumen = resumir_resultados(resultados_por_dataset, [item["id"] for item in datasets])
    return {
        "phase": phase_name,
        "strategy_name": strategy_name,
        "candidate_index": candidate_index,
        "params": parametros,
        "dataset_results": resultados_por_dataset,
        "summary": resumen,
    }


def construir_datasets(pairs: list[str], years: list[int]) -> list[dict[str, object]]:
    datasets = []
    for pair in pairs:
        for year in years:
            try:
                path = encontrar_csv_anual(pair, year)
            except FileNotFoundError:
                continue
            datasets.append(
                {
                    "id": f"{pair}_{year}",
                    "pair": pair,
                    "year": year,
                    "path": str(path),
                }
            )
    if not datasets:
        raise RuntimeError("No se encontraron datasets para construir el experimento.")
    return datasets


def ejecutar_fase(
    phase_name: str,
    strategy_names: list[str],
    candidates_per_strategy: int,
    datasets: list[dict[str, object]],
    spread_pips: float,
    workers: int,
    seed_base: int,
) -> list[dict[str, object]]:
    tareas = []
    for strategy_offset, strategy_name in enumerate(strategy_names):
        candidatos = generar_candidatos(
            strategy_name,
            candidates_per_strategy,
            semilla=seed_base + strategy_offset * 10_000,
        )
        for candidate_index, parametros in enumerate(candidatos, start=1):
            tareas.append((phase_name, strategy_name, candidate_index, parametros, datasets, spread_pips))

    resultados = []
    print(
        f"[{phase_name}] Lanzando {len(tareas)} candidatos sobre {len(datasets)} datasets "
        f"({len(tareas) * len(datasets)} backtests)."
    )

    if workers <= 1:
        for indice, tarea in enumerate(tareas, start=1):
            resultado = evaluar_candidato(*tarea)
            resultados.append(resultado)
            resumen = resultado["summary"]
            print(
                f"[{phase_name}] {indice}/{len(tareas)} "
                f"{resultado['strategy_name']} #{resultado['candidate_index']} "
                f"score={resumen['avg_score']:.2f} "
                f"ret={resumen['avg_return']:.2f}% "
                f"dd={resumen['avg_drawdown']:.2f}%"
            )
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futuros = [
                pool.submit(evaluar_candidato, phase_name, strategy_name, candidate_index, parametros, datasets, spread_pips)
                for phase_name, strategy_name, candidate_index, parametros, datasets, spread_pips in tareas
            ]

            for indice, futuro in enumerate(as_completed(futuros), start=1):
                resultado = futuro.result()
                resultados.append(resultado)
                resumen = resultado["summary"]
                print(
                    f"[{phase_name}] {indice}/{len(futuros)} "
                    f"{resultado['strategy_name']} #{resultado['candidate_index']} "
                    f"score={resumen['avg_score']:.2f} "
                    f"ret={resumen['avg_return']:.2f}% "
                    f"dd={resumen['avg_drawdown']:.2f}%"
                )

    resultados.sort(key=lambda item: item["summary"]["avg_score"], reverse=True)
    return resultados


def mejores_estrategias(resultados: list[dict[str, object]], limite: int) -> list[str]:
    vistos = []
    for resultado in resultados:
        nombre = resultado["strategy_name"]
        if nombre not in vistos:
            vistos.append(nombre)
        if len(vistos) >= limite:
            break
    return vistos


def mejores_por_estrategia(resultados: list[dict[str, object]], por_estrategia: int) -> dict[str, list[dict[str, object]]]:
    agrupados: dict[str, list[dict[str, object]]] = {}
    for resultado in resultados:
        agrupados.setdefault(resultado["strategy_name"], []).append(resultado)
    return {
        estrategia: items[:por_estrategia]
        for estrategia, items in agrupados.items()
    }


def analizar_walk_forward(
    deep_results: list[dict[str, object]],
    pair_core: list[str],
) -> list[dict[str, object]]:
    folds = [
        {
            "name": "2021-2022 -> 2023",
            "train": [f"{pair}_{year}" for pair in pair_core for year in (2021, 2022)],
            "test": [f"{pair}_2023" for pair in pair_core],
        },
        {
            "name": "2022-2023 -> 2024",
            "train": [f"{pair}_{year}" for pair in pair_core for year in (2022, 2023)],
            "test": [f"{pair}_2024" for pair in pair_core],
        },
        {
            "name": "2023-2024 -> 2025",
            "train": [f"{pair}_{year}" for pair in pair_core for year in (2023, 2024)],
            "test": [f"{pair}_2025" for pair in pair_core],
        },
    ]

    top_candidates = mejores_por_estrategia(deep_results, por_estrategia=12)
    analisis = []

    for strategy_name, candidatos in top_candidates.items():
        detalles_folds = []
        for fold in folds:
            candidatos_fold = []
            for candidato in candidatos:
                train_summary = resumir_resultados(candidato["dataset_results"], fold["train"])
                test_summary = resumir_resultados(candidato["dataset_results"], fold["test"])
                candidatos_fold.append(
                    {
                        "params": candidato["params"],
                        "train_summary": train_summary,
                        "test_summary": test_summary,
                    }
                )

            mejor = max(candidatos_fold, key=lambda item: item["train_summary"]["avg_score"])
            detalles_folds.append(
                {
                    "fold": fold["name"],
                    "params": mejor["params"],
                    "train_summary": mejor["train_summary"],
                    "test_summary": mejor["test_summary"],
                }
            )

        avg_oos_score = statistics.mean(item["test_summary"]["avg_score"] for item in detalles_folds)
        avg_oos_return = statistics.mean(item["test_summary"]["avg_return"] for item in detalles_folds)
        avg_oos_drawdown = statistics.mean(item["test_summary"]["avg_drawdown"] for item in detalles_folds)
        positive_folds = sum(1 for item in detalles_folds if item["test_summary"]["avg_return"] > 0)

        analisis.append(
            {
                "strategy_name": strategy_name,
                "folds": detalles_folds,
                "avg_oos_score": avg_oos_score,
                "avg_oos_return": avg_oos_return,
                "avg_oos_drawdown": avg_oos_drawdown,
                "positive_folds": positive_folds,
            }
        )

    analisis.sort(
        key=lambda item: (item["positive_folds"], item["avg_oos_score"], item["avg_oos_return"]),
        reverse=True,
    )
    return analisis


def seleccionar_parametros_finales(
    deep_results: list[dict[str, object]],
    strategy_name: str,
    pair_core: list[str],
) -> dict[str, object]:
    candidatos = [item for item in deep_results if item["strategy_name"] == strategy_name][:12]
    datasets_train = [f"{pair}_{year}" for pair in pair_core for year in (2021, 2022, 2023, 2024)]
    mejor = max(candidatos, key=lambda item: resumir_resultados(item["dataset_results"], datasets_train)["avg_score"])
    return mejor["params"]


def preparar_comparativa_final(
    top_walkforward: list[dict[str, object]],
    deep_results: list[dict[str, object]],
    spread_pips: float,
    workers: int,
) -> list[dict[str, object]]:
    estrategias = [item["strategy_name"] for item in top_walkforward[:3]]
    datasets = construir_datasets(PARES_AMPLIADOS, [2025])
    tareas = []
    for indice, strategy_name in enumerate(estrategias, start=1):
        parametros = seleccionar_parametros_finales(deep_results, strategy_name, PARES_NUCLEO)
        tareas.append(("validacion_final", strategy_name, indice, parametros, datasets, spread_pips))

    resultados = []
    if min(workers, len(tareas)) <= 1:
        for tarea in tareas:
            resultados.append(evaluar_candidato(*tarea))
    else:
        with ProcessPoolExecutor(max_workers=min(workers, len(tareas))) as pool:
            futuros = [
                pool.submit(evaluar_candidato, phase, strategy_name, idx, params, datasets, spread_pips)
                for phase, strategy_name, idx, params, datasets, spread_pips in tareas
            ]
            for futuro in as_completed(futuros):
                resultados.append(futuro.result())

    resultados.sort(key=lambda item: item["summary"]["avg_return"], reverse=True)
    return resultados


def serializar(objeto):
    if isinstance(objeto, dict):
        return {clave: serializar(valor) for clave, valor in objeto.items()}
    if isinstance(objeto, list):
        return [serializar(valor) for valor in objeto]
    if isinstance(objeto, float):
        if math.isnan(objeto) or math.isinf(objeto):
            return None
        return round(objeto, 6)
    return objeto


def escribir_reporte_markdown(
    ruta: Path,
    metadata: dict[str, object],
    screening: list[dict[str, object]],
    deep_results: list[dict[str, object]],
    walkforward: list[dict[str, object]],
    comparativa_final: list[dict[str, object]],
):
    top_screen = screening[:10]
    top_deep = deep_results[:10]
    mejor_walk = walkforward[0] if walkforward else None
    mejor_final = comparativa_final[0] if comparativa_final else None

    lineas = [
        "# Investigacion de estrategias Forex",
        "",
        f"- Fecha: {metadata['timestamp']}",
        f"- Spread supuesto: {metadata['spread_pips']} pip(s)",
        f"- Pares nucleo: {', '.join(metadata['pairs_core'])}",
        f"- Pares validacion final: {', '.join(metadata['pairs_expanded'])}",
        f"- Años nucleo: {', '.join(str(year) for year in metadata['core_years'])}",
        f"- Backtests ejecutados: {metadata['backtests_executed']}",
        "",
        "## Protocolo",
        "",
        "- Cribado inicial de todas las estrategias con combinaciones aleatorias y costes de spread.",
        "- Busqueda profunda solo sobre las mejores familias.",
        "- Seleccion con validacion walk-forward 2021-2022->2023, 2022-2023->2024 y 2023-2024->2025.",
        "- Validacion final ampliada sobre 2025 en seis pares mayores.",
        "",
        "## Fuentes externas usadas",
        "",
        "- Documentacion oficial de `backtesting.py` sobre `Backtest.optimize()` y el tratamiento de `spread`: https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html",
        "- Hsu, Taylor y Wang (2016), sobre muchas reglas, control del data snooping y validacion fuera de muestra: https://www.sciencedirect.com/science/article/pii/S0022199616300472",
        "- Neely y Weller (2003), sobre como la rentabilidad intradia desaparece facilmente al meter costes realistas: https://www.sciencedirect.com/science/article/pii/S0261560602001018",
        "- Holmberg, Lonnbark y Lundstrom (2013), como justificacion para probar una familia ORB/rango inicial: https://www.sciencedirect.com/science/article/pii/S1544612312000438",
        "",
        "## Top del cribado inicial",
        "",
    ]

    for item in top_screen:
        resumen = item["summary"]
        lineas.append(
            f"- {item['strategy_name']}: score {resumen['avg_score']:.2f}, retorno {resumen['avg_return']:.2f}%, drawdown {resumen['avg_drawdown']:.2f}%."
        )

    lineas.extend(
        [
            "",
            "## Top de la busqueda profunda",
            "",
        ]
    )

    for item in top_deep:
        resumen = item["summary"]
        lineas.append(
            f"- {item['strategy_name']} {item['params']}: score {resumen['avg_score']:.2f}, retorno {resumen['avg_return']:.2f}%, drawdown {resumen['avg_drawdown']:.2f}%."
        )

    lineas.extend(
        [
            "",
            "## Resultado walk-forward",
            "",
        ]
    )

    for item in walkforward:
        lineas.append(
            f"- {item['strategy_name']}: OOS medio {item['avg_oos_return']:.2f}%, score OOS {item['avg_oos_score']:.2f}, drawdown OOS {item['avg_oos_drawdown']:.2f}%, folds positivos {item['positive_folds']}/3."
        )
        for fold in item["folds"]:
            lineas.append(
                f"  - {fold['fold']}: retorno {fold['test_summary']['avg_return']:.2f}%, drawdown {fold['test_summary']['avg_drawdown']:.2f}%, params {fold['params']}"
            )

    if mejor_walk:
        lineas.extend(
            [
                "",
                "## Mejor estrategia robusta hallada",
                "",
                f"- Estrategia: {mejor_walk['strategy_name']}",
                f"- Retorno medio OOS: {mejor_walk['avg_oos_return']:.2f}%",
                f"- Drawdown medio OOS: {mejor_walk['avg_oos_drawdown']:.2f}%",
                f"- Folds positivos: {mejor_walk['positive_folds']}/3",
            ]
        )

    lineas.extend(
        [
            "",
            "## Validacion final ampliada 2025",
            "",
        ]
    )

    for item in comparativa_final:
        resumen = item["summary"]
        lineas.append(
            f"- {item['strategy_name']} {item['params']}: retorno medio {resumen['avg_return']:.2f}%, drawdown {resumen['avg_drawdown']:.2f}%, sharpe {resumen['avg_sharpe']:.2f}, profit factor {resumen['avg_profit_factor']:.2f}."
        )

    if mejor_final:
        lineas.extend(
            [
                "",
                "## Conclusiones operativas",
                "",
                f"- La mejor configuracion final ampliada fue `{mejor_final['strategy_name']}` con parametros `{mejor_final['params']}`.",
                f"- En los seis pares mayores de 2025 dio un retorno medio de {mejor_final['summary']['avg_return']:.2f}% con drawdown medio de {mejor_final['summary']['avg_drawdown']:.2f}%.",
                "- Aun asi, esto sigue siendo investigacion historica; no implica robustez futura ni garantiza beneficio real.",
            ]
        )

    ruta.write_text("\n".join(lineas), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Busca combinaciones robustas de estrategias Forex.")
    parser.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    parser.add_argument("--spread-pips", type=float, default=1.0)
    parser.add_argument("--screen-candidates", type=int, default=8)
    parser.add_argument("--deep-candidates", type=int, default=24)
    parser.add_argument("--report-name", type=str, default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    args = parser.parse_args()

    workers = max(1, args.workers)
    report_dir = ROOT / "reports" / "strategy_research" / args.report_name
    report_dir.mkdir(parents=True, exist_ok=True)

    screen_datasets = construir_datasets(PARES_NUCLEO, [2024, 2025])
    all_strategy_names = list(CONFIGURACION_ESTRATEGIAS.keys())

    screening = ejecutar_fase(
        phase_name="screening",
        strategy_names=all_strategy_names,
        candidates_per_strategy=args.screen_candidates,
        datasets=screen_datasets,
        spread_pips=args.spread_pips,
        workers=workers,
        seed_base=1_000,
    )

    top_strategy_names = mejores_estrategias(screening, limite=4)
    deep_datasets = construir_datasets(PARES_NUCLEO, [2021, 2022, 2023, 2024, 2025])

    deep_results = ejecutar_fase(
        phase_name="deep_search",
        strategy_names=top_strategy_names,
        candidates_per_strategy=args.deep_candidates,
        datasets=deep_datasets,
        spread_pips=args.spread_pips,
        workers=workers,
        seed_base=9_000,
    )

    walkforward = analizar_walk_forward(deep_results, PARES_NUCLEO)
    comparativa_final = preparar_comparativa_final(walkforward, deep_results, args.spread_pips, workers)

    metadata = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "spread_pips": args.spread_pips,
        "pairs_core": PARES_NUCLEO,
        "pairs_expanded": PARES_AMPLIADOS,
        "core_years": [2021, 2022, 2023, 2024, 2025],
        "screen_candidates": args.screen_candidates,
        "deep_candidates": args.deep_candidates,
        "backtests_executed": (
            len(screening) * len(screen_datasets)
            + len(deep_results) * len(deep_datasets)
            + len(comparativa_final) * len(construir_datasets(PARES_AMPLIADOS, [2025]))
        ),
    }

    payload = {
        "metadata": metadata,
        "screening": screening,
        "deep_results": deep_results,
        "walkforward": walkforward,
        "final_validation": comparativa_final,
    }

    (report_dir / "results.json").write_text(
        json.dumps(serializar(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    escribir_reporte_markdown(
        report_dir / "summary.md",
        metadata,
        screening,
        deep_results,
        walkforward,
        comparativa_final,
    )

    print(f"Reporte guardado en: {report_dir}")
    if walkforward:
        print(
            f"Mejor estrategia walk-forward: {walkforward[0]['strategy_name']} "
            f"(OOS medio {walkforward[0]['avg_oos_return']:.2f}%)"
        )
    if comparativa_final:
        print(
            f"Mejor validacion final: {comparativa_final[0]['strategy_name']} "
            f"(retorno medio {comparativa_final[0]['summary']['avg_return']:.2f}%)"
        )


if __name__ == "__main__":
    main()
