"""
Session Clock (anteproyecto 5.3): referencia temporal comun que
sincroniza telemetria de Unity, comportamiento y EEG.

Para la Fase 1 esto es intencionalmente simple: el backend es la
fuente de verdad del "instante cero" de la sesion (`session_clock_started_at`,
en UTC) y cada evento entrante trae su propio `client_timestamp`. La
diferencia entre ambos permite estimar clock offset / latencia, que es
justamente lo que M1 pide poder medir antes de invertir en contenido.

La logica de sincronizacion fina con el WAVEX Adapter (Fase 4) se
construye sobre esta base, no la reemplaza.
"""

from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def offset_ms(client_timestamp: datetime | None, received_at: datetime) -> float | None:
    """Diferencia en milisegundos entre el timestamp reportado por el
    cliente (Unity/WAVEX) y el momento en que el backend lo recibio."""
    if client_timestamp is None:
        return None
    delta = received_at - client_timestamp
    return delta.total_seconds() * 1000
