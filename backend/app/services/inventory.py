from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import OFFICIAL_ROOMS
from app.constants import PERIPHERAL_TYPES, RESOURCE_STATUSES
from app.models import Incident, Loan, Resource, ResourceEvent, Space
from app.schemas.campus import LoanOut, ResourceOut, SpaceOut
from app.services.errors import DomainError
from app.services.spaces import new_id, utcnow
from app.validators.audit import reject_audit_markers

UNAVAILABLE = {"maintenance", "damaged", "inactive", "disabled", "loaned"}


def record_event(db: Session, resource_id: str, field: str, old_value: str, new_value: str) -> None:
    if old_value == new_value:
        return
    db.add(
        ResourceEvent(
            resource_id=resource_id,
            field=field,
            old_value=old_value or "",
            new_value=new_value or "",
            created_at=utcnow(),
        )
    )


def computer_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Resource.space_id, func.count())
        .where(Resource.kind == "computer", Resource.space_id.is_not(None))
        .group_by(Resource.space_id)
    ).all()
    return {space_id: int(count) for space_id, count in rows if space_id}


def spaces_with_counts(db: Session) -> list[SpaceOut]:
    counts = computer_counts(db)
    return [SpaceOut.from_model(space, counts.get(space.id, 0)) for space in db.scalars(select(Space).order_by(Space.name))]


def list_computers(db: Session, space_id: str | None = None) -> list[Resource]:
    statement = select(Resource).where(Resource.kind == "computer").order_by(Resource.asset_code, Resource.name)
    if space_id:
        statement = statement.where(Resource.space_id == space_id)
    return list(db.scalars(statement))


def list_peripherals(db: Session, host_id: str | None = None, space_id: str | None = None) -> list[Resource]:
    statement = select(Resource).where(Resource.kind == "peripheral").order_by(Resource.name)
    if host_id:
        statement = statement.where(Resource.host_resource_id == host_id)
    if space_id:
        statement = statement.where(Resource.space_id == space_id)
    return list(db.scalars(statement))


def _require_space(db: Session, space_id: str | None) -> Space | None:
    if not space_id:
        return None
    space = db.get(Space, space_id)
    if space is None:
        raise DomainError("La sala indicada no existe.", 404)
    return space


def _require_unique_code(db: Session, asset_code: str, ignore_id: str | None = None) -> None:
    code = asset_code.strip()
    if not code:
        return
    existing = db.scalar(select(Resource).where(Resource.asset_code == code))
    if existing is not None and existing.id != ignore_id:
        raise DomainError(f"Ya existe un equipo con la etiqueta {code}.", 409)


def _active_loan(db: Session, resource_id: str) -> Loan | None:
    return db.scalar(select(Loan).where(Loan.resource_id == resource_id, Loan.status == "active"))


def computer_detail(db: Session, resource_id: str) -> dict:
    resource = db.get(Resource, resource_id)
    if resource is None or resource.kind != "computer":
        raise DomainError("El computador no existe.", 404)
    space = db.get(Space, resource.space_id) if resource.space_id else None
    peripherals = list_peripherals(db, host_id=resource.id)
    loans = list(db.scalars(select(Loan).where(Loan.resource_id == resource.id).order_by(Loan.loaned_at.desc())))
    incidents = list(
        db.scalars(select(Incident).where(Incident.resource_id == resource.id).order_by(Incident.created_at.desc()))
    )
    events = list(
        db.scalars(
            select(ResourceEvent).where(ResourceEvent.resource_id == resource.id).order_by(ResourceEvent.id.desc())
        )
    )
    return {
        "computer": ResourceOut.from_model(resource),
        "space_name": space.name if space else None,
        "peripherals": [ResourceOut.from_model(item) for item in peripherals],
        "loans": [LoanOut.from_model(item, resource.name) for item in loans],
        "incidents": [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "priority": item.priority,
                "created_at": item.created_at,
            }
            for item in incidents
        ],
        "events": [
            {
                "id": event.id,
                "field": event.field,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


def register_computer(
    db: Session,
    *,
    name: str,
    space_id: str,
    asset_code: str = "",
    notes: str = "",
    hardware_notes: str = "",
    provisional: bool = True,
) -> Resource:
    reject_audit_markers(name, space_id, asset_code, notes, hardware_notes)
    space = _require_space(db, space_id)
    assert space is not None
    _require_unique_code(db, asset_code)
    resource = Resource(
        id=new_id(),
        name=name.strip(),
        category="computador",
        location=space.name,
        status="available",
        serial_number="",
        notes=notes.strip(),
        origin="provisional" if provisional else "imported",
        asset_code=asset_code.strip(),
        kind="computer",
        space_id=space.id,
        provisional=provisional,
        hardware_notes=hardware_notes.strip(),
    )
    db.add(resource)
    db.flush()
    record_event(db, resource.id, "space_id", "", space.id)
    record_event(db, resource.id, "status", "", "available")
    db.commit()
    db.refresh(resource)
    return resource


def register_peripheral(
    db: Session,
    *,
    name: str,
    peripheral_type: str,
    host_resource_id: str | None = None,
    space_id: str | None = None,
    asset_code: str = "",
    notes: str = "",
    brand: str = "",
    model_name: str = "",
) -> Resource:
    reject_audit_markers(name, peripheral_type, host_resource_id, space_id, asset_code, notes, brand, model_name)
    if peripheral_type not in PERIPHERAL_TYPES or peripheral_type == "":
        raise DomainError("Indique un tipo de periférico: monitor, teclado, raton, auriculares u otro.", 422)
    host = None
    if host_resource_id:
        host = db.get(Resource, host_resource_id)
        if host is None or host.kind != "computer":
            raise DomainError("El computador asociado no existe.", 404)
    space = _require_space(db, space_id or (host.space_id if host else None))
    _require_unique_code(db, asset_code)
    resource = Resource(
        id=new_id(),
        name=name.strip(),
        category="periferico",
        location=space.name if space else "",
        status="available",
        notes=notes.strip(),
        origin="imported",
        asset_code=asset_code.strip(),
        kind="peripheral",
        space_id=space.id if space else None,
        host_resource_id=host.id if host else None,
        peripheral_type=peripheral_type,
        brand=brand.strip(),
        model_name=model_name.strip(),
        provisional=not bool(asset_code.strip()),
    )
    db.add(resource)
    db.flush()
    if host:
        record_event(db, resource.id, "host_resource_id", "", host.id)
    if space:
        record_event(db, resource.id, "space_id", "", space.id)
    db.commit()
    db.refresh(resource)
    return resource


def update_computer(db: Session, resource_id: str, *, name: str | None, notes: str | None, hardware_notes: str | None, asset_code: str | None) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None or resource.kind != "computer":
        raise DomainError("El computador no existe.", 404)
    reject_audit_markers(name, notes, hardware_notes, asset_code)
    if asset_code is not None:
        _require_unique_code(db, asset_code, ignore_id=resource.id)
        record_event(db, resource.id, "asset_code", resource.asset_code, asset_code.strip())
        resource.asset_code = asset_code.strip()
        resource.provisional = resource.asset_code == "" or resource.origin == "provisional"
    if name is not None and name.strip():
        resource.name = name.strip()
    if notes is not None:
        resource.notes = notes.strip()
    if hardware_notes is not None:
        resource.hardware_notes = hardware_notes.strip()
    db.commit()
    db.refresh(resource)
    return resource


def change_status(db: Session, resource_id: str, status: str, note: str = "") -> Resource:
    reject_audit_markers(status, note)
    if status not in RESOURCE_STATUSES or status == "loaned":
        raise DomainError("Ese estado no se puede asignar manualmente. El estado prestado sale de un préstamo.", 422)
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise DomainError("El equipo no existe.", 404)
    if status == "available" and _active_loan(db, resource.id) is not None:
        raise DomainError("No se puede marcar como disponible mientras tenga un préstamo activo.", 409)
    record_event(db, resource.id, "status", resource.status, status)
    if note.strip():
        record_event(db, resource.id, "note", "", note.strip())
    resource.status = status
    db.commit()
    db.refresh(resource)
    return resource


def change_location(db: Session, resource_id: str, space_id: str) -> Resource:
    reject_audit_markers(space_id)
    resource = db.get(Resource, resource_id)
    if resource is None or resource.kind not in {"computer", "peripheral"}:
        raise DomainError("El equipo no existe.", 404)
    space = _require_space(db, space_id)
    assert space is not None
    previous = resource.space_id or ""
    if previous == space.id:
        return resource
    record_event(db, resource.id, "space_id", previous, space.id)
    resource.space_id = space.id
    resource.location = space.name
    if resource.kind == "computer":
        for peripheral in list_peripherals(db, host_id=resource.id):
            old = peripheral.space_id or ""
            peripheral.space_id = space.id
            peripheral.location = space.name
            record_event(db, peripheral.id, "space_id", old, space.id)
    db.commit()
    db.refresh(resource)
    return resource


def reassign_peripheral(db: Session, peripheral_id: str, host_resource_id: str | None) -> Resource:
    peripheral = db.get(Resource, peripheral_id)
    if peripheral is None or peripheral.kind != "peripheral":
        raise DomainError("El periférico no existe.", 404)
    host = None
    if host_resource_id:
        host = db.get(Resource, host_resource_id)
        if host is None or host.kind != "computer":
            raise DomainError("El computador asociado no existe.", 404)
    previous = peripheral.host_resource_id or ""
    new_value = host.id if host else ""
    record_event(db, peripheral.id, "host_resource_id", previous, new_value)
    peripheral.host_resource_id = host.id if host else None
    if host and host.space_id:
        old_space = peripheral.space_id or ""
        peripheral.space_id = host.space_id
        peripheral.location = host.location
        record_event(db, peripheral.id, "space_id", old_space, host.space_id)
    db.commit()
    db.refresh(peripheral)
    return peripheral


def room_summary(db: Session) -> list[dict]:
    counts = computer_counts(db)
    rooms = []
    for spec in OFFICIAL_ROOMS:
        space = db.get(Space, spec["id"])
        registered = counts.get(spec["id"], 0) if space else 0
        by_status = {name: 0 for name in ("available", "loaned", "maintenance", "damaged", "inactive", "disabled")}
        if space:
            rows = db.execute(
                select(Resource.status, func.count())
                .where(Resource.kind == "computer", Resource.space_id == space.id)
                .group_by(Resource.status)
            ).all()
            for status, count in rows:
                by_status[status] = int(count)
        pending = 0
        if space:
            pending = db.scalar(
                select(func.count())
                .select_from(Resource)
                .where(Resource.kind == "computer", Resource.space_id == space.id, Resource.provisional.is_(True))
            ) or 0
        rooms.append(
            {
                "id": spec["id"],
                "name": spec["name"],
                "registered_room": space is not None,
                "capacity": space.capacity if space else spec["capacity"],
                "expected_computers": spec["expected_computers"],
                "registered_computers": registered,
                "matches_expected": space is not None and registered == spec["expected_computers"],
                "available": by_status["available"],
                "loaned": by_status["loaned"],
                "maintenance": by_status["maintenance"],
                "damaged": by_status["damaged"],
                "inactive": by_status["inactive"] + by_status["disabled"],
                "pending_identification": int(pending),
            }
        )
    return rooms


def initialize_official_catalog(db: Session) -> dict:
    created_rooms = 0
    skipped_rooms = 0
    conflicts: list[str] = []
    created_computers = 0
    skipped_computers = 0
    gaps: list[str] = []
    for spec in OFFICIAL_ROOMS:
        existing = db.get(Space, spec["id"])
        if existing is None:
            db.add(
                Space(
                    id=spec["id"],
                    name=spec["name"],
                    location="Campuslands",
                    capacity=spec["capacity"],
                    status="available",
                    features_json="[]",
                    description="Sala del catálogo operativo indicado para el campus.",
                    origin="official",
                    room_type=spec["room_type"],
                    expected_computers=spec["expected_computers"],
                )
            )
            created_rooms += 1
            db.flush()
            existing = db.get(Space, spec["id"])
        else:
            same = (
                existing.name == spec["name"]
                and existing.capacity == spec["capacity"]
                and existing.room_type == spec["room_type"]
                and existing.expected_computers == spec["expected_computers"]
            )
            if same:
                skipped_rooms += 1
            else:
                conflicts.append(
                    f"{spec['id']} ya existe con datos distintos "
                    f"(nombre {existing.name}, capacidad {existing.capacity}, "
                    f"tipo {existing.room_type}, equipos esperados {existing.expected_computers}). "
                    "No se sobrescribió."
                )
                continue
        if spec["expected_computers"] == 0:
            continue
        current = db.scalar(
            select(func.count()).select_from(Resource).where(Resource.kind == "computer", Resource.space_id == spec["id"])
        ) or 0
        if current == spec["expected_computers"]:
            skipped_computers += current
            continue
        if current > 0:
            gaps.append(
                f"{spec['name']}: hay {current} computadores registrados y se esperan {spec['expected_computers']}. "
                "No se crearon ni eliminaron unidades."
            )
            continue
        prefix = spec["name"].upper().replace(" ", "-")
        for number in range(1, spec["expected_computers"] + 1):
            code = f"{prefix}-PC-{number:03d}"
            resource = Resource(
                id=f"{spec['id']}-pc-{number:03d}",
                name=f"{spec['name']} PC {number:03d}",
                category="computador",
                location=spec["name"],
                status="available",
                notes="",
                origin="official",
                asset_code=code,
                kind="computer",
                space_id=spec["id"],
                provisional=False,
                hardware_notes="",
            )
            db.add(resource)
            db.flush()
            record_event(db, resource.id, "space_id", "", spec["id"])
            record_event(db, resource.id, "status", "", "available")
            created_computers += 1
    db.commit()
    summary = room_summary(db)
    return {
        "created_rooms": created_rooms,
        "skipped_rooms": skipped_rooms,
        "conflicts": conflicts,
        "created_computers": created_computers,
        "skipped_computers": skipped_computers,
        "gaps": gaps,
        "rooms": summary,
        "expected_room_count": len(OFFICIAL_ROOMS),
        "expected_computer_count": sum(item["expected_computers"] for item in OFFICIAL_ROOMS),
        "capacity_sum": sum(item["capacity"] for item in OFFICIAL_ROOMS),
        "stated_capacity_total_in_brief": 201,
        "capacity_note": (
            "La suma de las capacidades de la tabla es 295. El brief también cita 201. "
            "Se conservaron las capacidades de cada sala y no se ajustaron para cuadrar el total."
        ),
    }
