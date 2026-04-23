"""Persistencia local de estrategias personalizadas."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


DIRECTORIO_ESTRATEGIAS = Path(__file__).resolve().parent / "estrategias_guardadas"


def asegurar_directorio_estrategias() -> Path:
    """Crea el directorio de estrategias si todavia no existe."""
    DIRECTORIO_ESTRATEGIAS.mkdir(parents=True, exist_ok=True)
    return DIRECTORIO_ESTRATEGIAS


def _slugify(texto: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9]+", "-", texto.strip()).strip("-").lower()
    return limpio or "estrategia"


def guardar_estrategia_personalizada(
    nombre: str,
    plantilla_base: str,
    descripcion: str,
    parametros: dict[str, object],
) -> Path:
    """Guarda una estrategia personalizada basada en una plantilla existente."""
    directorio = asegurar_directorio_estrategias()
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{marca_tiempo}_{_slugify(nombre)}.json"
    ruta = directorio / nombre_archivo

    payload = {
        "id": ruta.stem,
        "nombre": nombre,
        "fecha_guardado": datetime.now().isoformat(timespec="seconds"),
        "plantilla_base": plantilla_base,
        "descripcion": descripcion,
        "parametros": parametros,
    }

    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def listar_estrategias_personalizadas() -> list[dict[str, object]]:
    """Lista las estrategias guardadas del mas reciente al mas antiguo."""
    directorio = asegurar_directorio_estrategias()
    estrategias = []

    for ruta in sorted(directorio.glob("*.json"), reverse=True):
        try:
            payload = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            continue

        payload["ruta_archivo"] = str(ruta)
        estrategias.append(payload)

    return estrategias


def eliminar_estrategia_personalizada(ruta_archivo: str | Path) -> bool:
    """Elimina una estrategia personalizada por su ruta."""
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        return False
    ruta.unlink()
    return True
