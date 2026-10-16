from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    INCIDENT_AREAS,
    INCIDENT_CATEGORIES,
    INCIDENT_PRIORITIES,
    INCIDENT_STATUSES,
    REF_CORE,
)
from app.models import Incident, IncidentEvent, Resource, Space
from app.schemas.campus import IncidentCreate, IncidentOut, IncidentPatch
from app.services.errors import DomainError
from app.services.spaces import new_id, utcnow
from app.validators.audit import reject_audit_markers


def _ensure_links(db: Session, space_id: str | None, resource_id: str | None) -> None:
    if space_id:
        if db.get(Space, space_id) is None:
            raise DomainError("El espacio indicado en el incidente no existe.", 404)
    if resource_id:
        if db.get(Resource, resource_id) is None:
            raise DomainError("El recurso indicado en el incidente no existe.", 404)


def _add_event(db: Session, incident_id: str, field: str, old_value: str, new_value: str) -> None:
    db.add(
        IncidentEvent(
            incident_id=incident_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            created_at=utcnow(),
        )
    )


def list_incidents(
    db: Session,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> list[Incident]:
    statement = select(Incident).order_by(Incident.created_at.desc())
    if category:
        statement = statement.where(Incident.category == category)
    if priority:
        statement = statement.where(Incident.priority == priority)
    if status:
        statement = statement.where(Incident.status == status)
    return list(db.scalars(statement))


def get_incident(db: Session, incident_id: str) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise DomainError("El incidente no existe.", 404)
    return incident


def create_incident(db: Session, payload: IncidentCreate) -> Incident:
    payload.validate_enums()
    reject_audit_markers(
        payload.description,
        payload.title,
        payload.category,
        payload.priority,
        payload.responsible_area,
        payload.recommendation,
        payload.rationale,
        payload.space_id,
        payload.resource_id,
    )
    _ensure_links(db, payload.space_id, payload.resource_id)
    title = (payload.title or payload.description).strip()
    if len(title) > 80:
        title = title[:77].rstrip() + "..."
    now = utcnow()
    incident = Incident(
        id=new_id(),
        title=title,
        description=payload.description.strip(),
        category=payload.category,
        priority=payload.priority,
        responsible_area=payload.responsible_area,
        recommendation=payload.recommendation.strip(),
        rationale=payload.rationale.strip(),
        status="open",
        source=payload.source,
        ref_core=REF_CORE,
        priority_raised_by_policy=payload.priority_raised_by_policy,
        corrected=payload.corrected,
        space_id=payload.space_id,
        resource_id=payload.resource_id,
        created_at=now,
        updated_at=now,
    )
    db.add(incident)
    db.flush()
    _add_event(db, incident.id, "status", "", "open")
    _add_event(db, incident.id, "priority", "", payload.priority)
    _add_event(db, incident.id, "source", "", payload.source)
    db.commit()
    db.refresh(incident)
    return incident


def update_incident(db: Session, incident_id: str, payload: IncidentPatch) -> Incident:
    reject_audit_markers(payload.status, payload.priority, payload.category, payload.responsible_area)
    incident = get_incident(db, incident_id)
    changes: list[tuple[str, str, str]] = []

    def assign(field: str, value: str | None, allowed: tuple[str, ...], label: str) -> None:
        if value is None:
            return
        if value not in allowed:
            raise DomainError(f"{label} no es válido. Use: {', '.join(allowed)}.", 422)
        current = getattr(incident, field)
        if current != value:
            changes.append((field, current, value))
            setattr(incident, field, value)

    assign("status", payload.status, INCIDENT_STATUSES, "El estado")
    assign("priority", payload.priority, INCIDENT_PRIORITIES, "La prioridad")
    assign("category", payload.category, INCIDENT_CATEGORIES, "La categoría")
    assign("responsible_area", payload.responsible_area, INCIDENT_AREAS, "El área responsable")
    if not changes:
        return incident
    incident.updated_at = utcnow()
    for field, old, new in changes:
        _add_event(db, incident.id, field, old, new)
    db.commit()
    db.refresh(incident)
    return incident


def serialize_incident(incident: Incident, include_events: bool = False) -> IncidentOut:
    return IncidentOut.from_model(incident, include_events=include_events)
