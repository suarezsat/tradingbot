"""Valida candidatos concretos de estrategias sobre varios datasets y spreads."""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimize_forex_strategies import (  # type: ignore
    construir_datasets,
    evaluar_candidato,
    generar_candidatos,
    parse_csv_list,
    parse_years,
    serializar,
)


def parse_candidate_specs(texto: str) -> list[tuple[str, int]]:
    specs: list[tuple[str, int]] = []
    for bloque in [item.strip() for item in texto.split("|") if item.strip()]:
        nombre, indice = bloque.rsplit(":", 1)
        specs.append((nombre.strip(), int(indice.strip())))
    return specs


def parse_spreads(texto: str) -> list[float]:
    return [float(item.strip()) for item in texto.split(",") if item.strip()]


def resolver_parametros(
    specs: list[tuple[str, int]],
    order: list[str],
    candidate_pool_size: int,
    seed_base: int,
) -> list[dict[str, object]]:
    resultados: list[dict[str, object]] = []
    order_map = {nombre: idx for idx, nombre in enumerate(order)}

    for nombre, indice in specs:
        if nombre not in order_map:
            raise ValueError(f"La estrategia '{nombre}' no esta incluida en --strategy-order.")
        if indice < 1 or indice > candidate_pool_size:
            raise ValueError(
                f"Indice invalido para '{nombre}': {indice}. Debe estar entre 1 y {candidate_pool_size}."
            )

        candidatos = generar_candidatos(
            nombre,
            candidate_pool_size,
            semilla=seed_base + order_map[nombre] * 10_000,
        )
        resultados.append(
            {
                "strategy_name": nombre,
                "candidate_index": indice,
                "params": candidatos[indice - 1],
            }
        )
    return resultados


def resumir_resultado(resultado: dict[str, object]) -> dict[str, object]:
    return {
        "strategy_name": resultado["strategy_name"],
        "candidate_index": resultado["candidate_index"],
        "params": resultado["params"],
        "summary": resultado["summary"],
    }


def evaluar_en_spread(
    spread: float,
    strategy_name: str,
    candidate_index: int,
    params: dict[str, object],
    datasets: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "spread": spread,
        "result": evaluar_candidato(
            "validacion_dirigida",
            strategy_name,
            candidate_index,
            params,
            datasets,
            spread,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida candidatos concretos de estrategias.")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--strategy-order", required=True, type=str)
    parser.add_argument("--candidate-specs", required=True, type=str)
    parser.add_argument("--candidate-pool-size", type=int, default=6)
    parser.add_argument("--seed-base", type=int, default=1_000)
    parser.add_argument("--pairs", required=True, type=str)
    parser.add_argument("--years", required=True, type=str)
    parser.add_argument("--spreads", type=str, default="0.5,1.0")
    parser.add_argument("--report-name", type=str, required=True)
    args = parser.parse_args()

    strategy_order = [item.strip() for item in args.strategy_order.split("|") if item.strip()]
    candidate_specs = parse_candidate_specs(args.candidate_specs)
    spreads = parse_spreads(args.spreads)
    datasets = construir_datasets(parse_csv_list(args.pairs), parse_years(args.years))
    candidatos = resolver_parametros(
        candidate_specs,
        strategy_order,
        args.candidate_pool_size,
        args.seed_base,
    )

    report_dir = ROOT / "reports" / "strategy_research" / args.report_name
    report_dir.mkdir(parents=True, exist_ok=True)

    resultados = {
        "metadata": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pairs": parse_csv_list(args.pairs),
            "years": parse_years(args.years),
            "spreads": spreads,
            "strategy_order": strategy_order,
            "candidate_pool_size": args.candidate_pool_size,
            "seed_base": args.seed_base,
        },
        "runs": [],
    }

    tareas = []
    for spread in spreads:
        for candidato in candidatos:
            tareas.append(
                (
                    spread,
                    candidato["strategy_name"],
                    int(candidato["candidate_index"]),
                    candidato["params"],
                    datasets,
                )
            )

    resultados_por_spread = {spread: {"spread": spread, "results": []} for spread in spreads}
    print(
        f"[setup] workers={args.workers} candidatos={len(candidatos)} spreads={len(spreads)} "
        f"datasets={len(datasets)} tareas={len(tareas)}",
        flush=True,
    )

    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(tareas)))) as pool:
        futuros = [
            pool.submit(
                evaluar_en_spread,
                spread,
                strategy_name,
                candidate_index,
                params,
                datasets,
            )
            for spread, strategy_name, candidate_index, params, datasets in tareas
        ]

        for indice, futuro in enumerate(as_completed(futuros), start=1):
            payload = futuro.result()
            spread = payload["spread"]
            resultado = payload["result"]
            resumen = resultado["summary"]
            resultados_por_spread[spread]["results"].append(resumir_resultado(resultado))
            print(
                f"[{indice}/{len(futuros)} spread={spread}] {resultado['strategy_name']} #{resultado['candidate_index']} "
                f"ret={resumen['avg_return']:.2f}% dd={resumen['avg_drawdown']:.2f}% "
                f"score={resumen['avg_score']:.2f}",
                flush=True,
            )

    for spread in spreads:
        run = resultados_por_spread[spread]
        run["results"].sort(key=lambda item: item["summary"]["avg_return"], reverse=True)
        resultados["runs"].append(run)

    (report_dir / "results.json").write_text(
        json.dumps(serializar(resultados), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lineas = [
        "# Validacion dirigida de candidatos",
        "",
        f"- Fecha: {resultados['metadata']['timestamp']}",
        f"- Pares: {', '.join(resultados['metadata']['pairs'])}",
        f"- Anos: {', '.join(str(item) for item in resultados['metadata']['years'])}",
        f"- Spreads: {', '.join(str(item) for item in resultados['metadata']['spreads'])}",
        "",
    ]

    for run in resultados["runs"]:
        lineas.extend(
            [
                f"## Spread {run['spread']} pip(s)",
                "",
            ]
        )
        for item in run["results"]:
            resumen = item["summary"]
            lineas.append(
                f"- {item['strategy_name']} #{item['candidate_index']} {item['params']}: "
                f"retorno medio {resumen['avg_return']:.2f}%, drawdown {resumen['avg_drawdown']:.2f}%, "
                f"sharpe {resumen['avg_sharpe']:.2f}, profit factor {resumen['avg_profit_factor']:.2f}."
            )
        lineas.append("")

    (report_dir / "summary.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"Reporte guardado en: {report_dir}", flush=True)


if __name__ == "__main__":
    main()
