"""
Registro central de modelos ORM.

Alembic (`alembic/env.py`) importa este paquete para que
`Base.metadata` conozca todas las tablas al autogenerar migraciones.

Alcance de este esquema (Fase 1 - Foundation & Feasibility):
las tablas de aca abajo cubren participante, sesion, snapshot de
configuracion, validacion tecnica y un event log generico. Es el
"esquema inicial" pedido para esta fase: suficiente para probar el
walking skeleton Unity <-> Backend <-> PostgreSQL end-to-end.

Deliberadamente NO se modelan todavia (llegan en fases posteriores,
segun el cronograma del anteproyecto):
- KanjiLearningItem / Trial / retrieval data contract completo -> Fase 2-3 (M2)
- EEG windows / WAVEX sync detallado                            -> Fase 4 (M3)
- AdaptationEvent (ESL/LAL) / State Estimator output             -> Fase 5 (M3)
- Outcome / AdaptiveLearnerProfile                               -> Fase 6 (M4)
"""

from app.models.participant import Participant
from app.models.session import ExperimentSession, SessionConfigSnapshot
from app.models.system_event import SessionEvent, SystemValidationEvent

__all__ = [
    "Participant",
    "ExperimentSession",
    "SessionConfigSnapshot",
    "SessionEvent",
    "SystemValidationEvent",
]
