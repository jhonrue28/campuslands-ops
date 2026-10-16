import csv
import io
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import SYNTHETIC_DATA_PATH
from app.constants import (
    INCIDENT_AREAS,
    INCIDENT_CATEGORIES,
    INCIDENT_PRIORITIES,
    INCIDENT_SOURCES,
    INCIDENT_STATUSES,
    LOAN_STATUSES,
    RESERVATION_STATUSES,
    RESOURCE_STATUSES,
    SPACE_STATUSES,
)
from app.models import ImportReport, Incident, IncidentEvent, Loan, Reservation, Resource, Space
from app.schemas.campus import ImportIssue, ImportReportOut
from app.services.errors import DomainError
from app.services.spaces import overlapping_query, utcnow
from app.validators.audit import reject_audit_markers


def _features(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("|", ";").split(";") if part.strip()]


def _as_int(value, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"El campo {field} debe ser un número entero.") from exc


def _as_dt(value, field: str) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"El campo {field} es obligatorio y debe ser una fecha.")
    text = value.strip().replace("Z", "")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"El campo {field} no tiene un formato de fecha válido.") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _same_space(existing: Space, data: dict) -> bool:
    return (
        existing.name == data["name"]
        and existing.location == data["location"]
        and existing.capacity == data["capacity"]
        and existing.status == data["status"]
        and json.loads(existing.features_json) == data["features"]
    )


def _same_resource(existing: Resource, data: dict) -> bool:
    return (
        existing.name == data["name"]
        and existing.category == data["category"]
        and existing.location == data["location"]
        and existing.status == data["status"]
        and existing.serial_number == data["serial_number"]
    )


class _Importer:
    def __init__(self, db: Session, source_name: str, origin: str):
        self.db = db
        self.source_name = source_name
        self.origin = origin
        self.accepted = 0
        self.rejected = 0
        self.skipped = 0
        self.issues: list[ImportIssue] = []
        self.notices: list[str] = []

    def issue(self, entity: str, row: int, reason: str, identifier: str | None = None) -> None:
        self.rejected += 1
        self.issues.append(ImportIssue(entity=entity, row=row, identifier=identifier, reason=reason))

    def skip(self, entity: str, row: int, identifier: str) -> None:
        self.skipped += 1
        self.notices.append(
            f"{entity} fila {row} ({identifier}): registro duplicado idéntico. No se insertó de nuevo."
        )

    def import_bundle(self, payload: dict) -> ImportReportOut:
        if not isinstance(payload, dict):
            raise DomainError("El archivo JSON debe ser un objeto con las colecciones del campus.", 422)
        reject_audit_markers(json.dumps(payload, ensure_ascii=False))
        try:
            self._spaces(payload.get("spaces") or [])
            self._resources(payload.get("resources") or [])
            self._reservations(payload.get("reservations") or [])
            self._loans(payload.get("loans") or [])
            self._incidents(payload.get("incidents") or [])
            report = self._persist()
            self.db.commit()
            return report
        except Exception:
            self.db.rollback()
            raise

    def _persist(self) -> ImportReportOut:
        created = utcnow()
        row = ImportReport(
            source_name=self.source_name,
            accepted=self.accepted,
            rejected=self.rejected,
            skipped_duplicates=self.skipped,
            details_json=json.dumps(
                {
                    "issues": [item.model_dump() for item in self.issues],
                    "notices": self.notices,
                },
                ensure_ascii=False,
            ),
            created_at=created,
        )
        self.db.add(row)
        self.db.flush()
        return ImportReportOut(
            id=row.id,
            source_name=self.source_name,
            accepted=self.accepted,
            rejected=self.rejected,
            skipped_duplicates=self.skipped,
            synthetic=self.origin == "synthetic",
            issues=self.issues,
            notices=self.notices,
            created_at=created,
        )

    def _spaces(self, rows) -> None:
        if not isinstance(rows, list):
            raise DomainError("La colección spaces debe ser una lista.", 422)
        for index, raw in enumerate(rows, start=1):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("La fila no es un objeto.")
                space_id = str(raw.get("id") or "").strip()
                name = str(raw.get("name") or "").strip()
                if not space_id or not name:
                    raise ValueError("id y name son obligatorios.")
                capacity = _as_int(raw.get("capacity"), "capacity")
                if capacity < 1:
                    raise ValueError("La capacidad debe ser mayor que cero.")
                status = str(raw.get("status") or "available").strip()
                if status not in SPACE_STATUSES:
                    raise ValueError(f"Estado de espacio no permitido: {status}.")
                data = {
                    "name": name,
                    "location": str(raw.get("location") or "").strip(),
                    "capacity": capacity,
                    "status": status,
                    "features": _features(raw.get("features")),
                    "description": str(raw.get("description") or "").strip(),
                }
                existing = self.db.get(Space, space_id)
                if existing:
                    if _same_space(existing, data):
                        self.skip("spaces", index, space_id)
                    else:
                        raise ValueError("Ya existe un espacio con ese id y los datos no coinciden.")
                    continue
                self.db.add(
                    Space(
                        id=space_id,
                        name=data["name"],
                        location=data["location"],
                        capacity=data["capacity"],
                        status=data["status"],
                        features_json=json.dumps(data["features"], ensure_ascii=False),
                        description=data["description"],
                        origin=self.origin,
                    )
                )
                self.accepted += 1
            except ValueError as exc:
                self.issue("spaces", index, str(exc), str(raw.get("id") or "") or None)

    def _resources(self, rows) -> None:
        if not isinstance(rows, list):
            raise DomainError("La colección resources debe ser una lista.", 422)
        for index, raw in enumerate(rows, start=1):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("La fila no es un objeto.")
                resource_id = str(raw.get("id") or "").strip()
                name = str(raw.get("name") or "").strip()
                if not resource_id or not name:
                    raise ValueError("id y name son obligatorios.")
                quantity = _as_int(raw.get("quantity", 1), "quantity")
                if quantity < 1:
                    raise ValueError("La cantidad debe ser mayor que cero.")
                status = str(raw.get("status") or "available").strip()
                if status == "loaned":
                    raise ValueError(
                        "El estado 'loaned' se deriva de un préstamo. Importe el recurso como available y el préstamo aparte."
                    )
                if status not in RESOURCE_STATUSES:
                    raise ValueError(f"Estado de recurso no permitido: {status}.")
                units = [resource_id] if quantity == 1 else [f"{resource_id}-{number}" for number in range(1, quantity + 1)]
                if quantity > 1:
                    self.notices.append(
                        f"resources fila {index} ({resource_id}): la cantidad {quantity} se adaptó a unidades "
                        + ", ".join(units)
                        + ". No se perdieron unidades."
                    )
                pending: list[tuple[str, dict]] = []
                identical: list[str] = []
                notes = str(raw.get("notes") or "").strip()
                for unit_id in units:
                    data = {
                        "name": name if quantity == 1 else f"{name} #{unit_id.rsplit('-', 1)[-1]}",
                        "category": str(raw.get("category") or "").strip(),
                        "location": str(raw.get("location") or "").strip(),
                        "status": status,
                        "serial_number": str(raw.get("serial_number") or "").strip(),
                    }
                    existing = self.db.get(Resource, unit_id)
                    if existing:
                        if _same_resource(existing, data):
                            identical.append(unit_id)
                        else:
                            raise ValueError(f"Ya existe el recurso {unit_id} con datos distintos.")
                    else:
                        pending.append((unit_id, data))
                for unit_id in identical:
                    self.skip("resources", index, unit_id)
                for unit_id, data in pending:
                    self.db.add(
                        Resource(
                            id=unit_id,
                            name=data["name"],
                            category=data["category"],
                            location=data["location"],
                            status=data["status"],
                            serial_number=data["serial_number"],
                            notes=notes,
                            origin=self.origin,
                        )
                    )
                    self.accepted += 1
            except ValueError as exc:
                self.issue("resources", index, str(exc), str(raw.get("id") or "") or None)

    def _reservations(self, rows) -> None:
        if not isinstance(rows, list):
            raise DomainError("La colección reservations debe ser una lista.", 422)
        for index, raw in enumerate(rows, start=1):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("La fila no es un objeto.")
                reservation_id = str(raw.get("id") or "").strip()
                space_id = str(raw.get("space_id") or "").strip()
                requester = str(raw.get("requester_name") or "").strip()
                purpose = str(raw.get("purpose") or "").strip()
                if not reservation_id or not space_id or not requester or not purpose:
                    raise ValueError("id, space_id, requester_name y purpose son obligatorios.")
                if self.db.get(Reservation, reservation_id) is not None:
                    self.skip("reservations", index, reservation_id)
                    continue
                space = self.db.get(Space, space_id)
                if space is None:
                    raise ValueError(f"El espacio {space_id} no existe.")
                attendees = _as_int(raw.get("attendees"), "attendees")
                if attendees < 1:
                    raise ValueError("Debe haber al menos un asistente.")
                if attendees > space.capacity:
                    raise ValueError(
                        f"Los asistentes ({attendees}) superan la capacidad ({space.capacity})."
                    )
                starts_at = _as_dt(raw.get("starts_at"), "starts_at")
                ends_at = _as_dt(raw.get("ends_at"), "ends_at")
                if ends_at <= starts_at:
                    raise ValueError("La finalización debe ser posterior al inicio.")
                status = str(raw.get("status") or "active").strip()
                if status not in RESERVATION_STATUSES:
                    raise ValueError(f"Estado de reserva no permitido: {status}.")
                if status == "active" and space.status != "available":
                    raise ValueError(f"No se puede importar una reserva activa en un espacio {space.status}.")
                if status == "active" and self.db.scalar(overlapping_query(space_id, starts_at, ends_at)) is not None:
                    raise ValueError("La reserva se solapa con otra reserva activa del mismo espacio.")
                self.db.add(
                    Reservation(
                        id=reservation_id,
                        space_id=space_id,
                        requester_name=requester,
                        purpose=purpose,
                        attendees=attendees,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        status=status,
                        created_at=_as_dt(raw.get("created_at"), "created_at")
                        if raw.get("created_at")
                        else utcnow(),
                    )
                )
                self.accepted += 1
            except ValueError as exc:
                self.issue("reservations", index, str(exc), str(raw.get("id") or "") or None)

    def _loans(self, rows) -> None:
        if not isinstance(rows, list):
            raise DomainError("La colección loans debe ser una lista.", 422)
        ordered = list(enumerate(rows, start=1))
        def _loan_order(item: tuple[int, object]) -> int:
            raw_row = item[1]
            if isinstance(raw_row, dict) and str(raw_row.get("status") or "") == "returned":
                return 0
            return 1

        ordered.sort(key=_loan_order)
        for index, raw in ordered:
            try:
                if not isinstance(raw, dict):
                    raise ValueError("La fila no es un objeto.")
                loan_id = str(raw.get("id") or "").strip()
                resource_id = str(raw.get("resource_id") or "").strip()
                borrower = str(raw.get("borrower_name") or "").strip()
                if not loan_id or not resource_id or not borrower:
                    raise ValueError("id, resource_id y borrower_name son obligatorios.")
                if self.db.get(Loan, loan_id) is not None:
                    self.skip("loans", index, loan_id)
                    continue
                resource = self.db.get(Resource, resource_id)
                if resource is None:
                    raise ValueError(f"El recurso {resource_id} no existe.")
                status = str(raw.get("status") or "active").strip()
                if status not in LOAN_STATUSES:
                    raise ValueError(f"Estado de préstamo no permitido: {status}.")
                if status == "active":
                    if resource.status != "available":
                        raise ValueError(
                            f"No se puede prestar un recurso en estado {resource.status}."
                        )
                    existing = self.db.scalar(
                        select(Loan).where(Loan.resource_id == resource.id, Loan.status == "active")
                    )
                    if existing is not None:
                        raise ValueError("El recurso ya tiene un préstamo activo.")
                returned_at = _as_dt(raw.get("returned_at"), "returned_at") if raw.get("returned_at") else None
                if status == "returned" and returned_at is None:
                    raise ValueError("Un préstamo devuelto requiere returned_at.")
                if status == "active" and returned_at is not None:
                    raise ValueError("Un préstamo activo no puede tener returned_at.")
                loan = Loan(
                    id=loan_id,
                    resource_id=resource.id,
                    borrower_name=borrower,
                    borrower_contact=str(raw.get("borrower_contact") or "").strip(),
                    purpose=str(raw.get("purpose") or "").strip(),
                    status=status,
                    loaned_at=_as_dt(raw.get("loaned_at") or raw.get("starts_at"), "loaned_at")
                    if (raw.get("loaned_at") or raw.get("starts_at"))
                    else utcnow(),
                    due_at=_as_dt(raw.get("due_at"), "due_at") if raw.get("due_at") else None,
                    returned_at=returned_at,
                )
                self.db.add(loan)
                if status == "active":
                    resource.status = "loaned"
                self.accepted += 1
            except ValueError as exc:
                self.issue("loans", index, str(exc), str(raw.get("id") or "") or None)

    def _incidents(self, rows) -> None:
        if not isinstance(rows, list):
            raise DomainError("La colección incidents debe ser una lista.", 422)
        for index, raw in enumerate(rows, start=1):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("La fila no es un objeto.")
                incident_id = str(raw.get("id") or "").strip()
                description = str(raw.get("description") or "").strip()
                if not incident_id or not description:
                    raise ValueError("id y description son obligatorios.")
                if self.db.get(Incident, incident_id) is not None:
                    self.skip("incidents", index, incident_id)
                    continue
                category = str(raw.get("category") or "otro").strip()
                priority = str(raw.get("priority") or "media").strip()
                area = str(raw.get("responsible_area") or "administracion").strip()
                status = str(raw.get("status") or "open").strip()
                source = str(raw.get("source") or "manual").strip()
                if category not in INCIDENT_CATEGORIES:
                    raise ValueError(f"Categoría no permitida: {category}.")
                if priority not in INCIDENT_PRIORITIES:
                    raise ValueError(f"Prioridad no permitida: {priority}.")
                if area not in INCIDENT_AREAS:
                    raise ValueError(f"Área no permitida: {area}.")
                if status not in INCIDENT_STATUSES:
                    raise ValueError(f"Estado no permitido: {status}.")
                if source not in INCIDENT_SOURCES:
                    raise ValueError(f"Origen no permitido: {source}.")
                if source == "ai":
                    raise ValueError(
                        "Un incidente importado no puede declararse como respuesta de IA. Use source manual."
                    )
                space_id = str(raw.get("space_id") or "").strip() or None
                resource_id = str(raw.get("resource_id") or "").strip() or None
                if space_id and self.db.get(Space, space_id) is None:
                    raise ValueError(f"El espacio {space_id} no existe.")
                if resource_id and self.db.get(Resource, resource_id) is None:
                    raise ValueError(f"El recurso {resource_id} no existe.")
                title = str(raw.get("title") or description).strip()
                if len(title) > 200:
                    title = title[:197] + "..."
                now = utcnow()
                self.db.add(
                    Incident(
                        id=incident_id,
                        title=title,
                        description=description,
                        category=category,
                        priority=priority,
                        responsible_area=area,
                        recommendation=str(raw.get("recommendation") or "").strip(),
                        rationale=str(raw.get("rationale") or "").strip(),
                        status=status,
                        source=source,
                        ref_core="[Ref-Core]" if source != "manual" else "",
                        priority_raised_by_policy=False,
                        corrected=False,
                        space_id=space_id,
                        resource_id=resource_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
                self.db.flush()
                self.db.add(
                    IncidentEvent(
                        incident_id=incident_id,
                        field="import",
                        old_value="",
                        new_value=status,
                        created_at=now,
                    )
                )
                self.accepted += 1
            except ValueError as exc:
                self.issue("incidents", index, str(exc), str(raw.get("id") or "") or None)


def import_payload(db: Session, payload: dict, source_name: str, origin: str) -> ImportReportOut:
    return _Importer(db, source_name, origin).import_bundle(payload)


def import_json_text(db: Session, text: str, source_name: str) -> ImportReportOut:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DomainError(f"El JSON no se pudo leer: {exc.msg}.", 422) from exc
    dataset = str(payload.get("dataset") or "").lower() if isinstance(payload, dict) else ""
    origin = "synthetic" if dataset == "synthetic" else "imported"
    return import_payload(db, payload, source_name, origin)


def import_csv_text(db: Session, text: str, entity: str, source_name: str) -> ImportReportOut:
    allowed = {"spaces", "resources", "reservations", "loans", "incidents"}
    if entity not in allowed:
        raise DomainError("El parámetro entity debe ser spaces, resources, reservations, loans o incidents.", 422)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise DomainError("El CSV no tiene encabezados.", 422)
    rows = []
    for raw in reader:
        item = {key.strip(): (value.strip() if isinstance(value, str) else value) for key, value in raw.items() if key}
        rows.append(item)
    return import_payload(db, {entity: rows}, source_name, "imported")


def import_synthetic(db: Session) -> ImportReportOut:
    if not SYNTHETIC_DATA_PATH.exists():
        raise DomainError("No se encontró el archivo de datos sintéticos.", 500)
    return import_json_text(db, SYNTHETIC_DATA_PATH.read_text(encoding="utf-8"), SYNTHETIC_DATA_PATH.name)


def list_reports(db: Session) -> list[ImportReportOut]:
    rows = list(db.scalars(select(ImportReport).order_by(ImportReport.created_at.desc())))
    reports = []
    for row in rows:
        parsed = json.loads(row.details_json or "{}")
        if isinstance(parsed, list):
            issues = [ImportIssue(**item) for item in parsed]
            notices: list[str] = []
        else:
            issues = [ImportIssue(**item) for item in parsed.get("issues", [])]
            notices = [str(item) for item in parsed.get("notices", [])]
        reports.append(
            ImportReportOut(
                id=row.id,
                source_name=row.source_name,
                accepted=row.accepted,
                rejected=row.rejected,
                skipped_duplicates=row.skipped_duplicates,
                synthetic=row.source_name == SYNTHETIC_DATA_PATH.name,
                issues=issues,
                notices=notices,
                created_at=row.created_at,
            )
        )
    return reports
