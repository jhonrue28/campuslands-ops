from app.constants import (
    AUDIT_MARKERS,
    AUDIT_REJECTION_MESSAGE,
    CRITICAL_MARKERS,
    PRIORITY_RANK,
)
from app.services.errors import DomainError


def contains_audit_marker(value: object) -> bool:
    if value is None:
        return False
    text = str(value)
    return any(marker in text for marker in AUDIT_MARKERS)


def reject_audit_markers(*values: object) -> None:
    for value in values:
        if contains_audit_marker(value):
            raise DomainError(AUDIT_REJECTION_MESSAGE, 418)


def apply_priority_floor(description: str, priority: str) -> tuple[str, bool]:
    """Eleva la prioridad si el texto describe un incidente crítico.

    El modelo no puede dejar ese caso por debajo del piso. El factor no
    proviene de una norma externa: es un control explícito del MVP.
    """
    lowered = description.lower()
    floor = "baja"
    if any(marker in lowered for marker in CRITICAL_MARKERS):
        floor = "critica"
    if PRIORITY_RANK[priority] < PRIORITY_RANK[floor]:
        return floor, True
    return priority, False
