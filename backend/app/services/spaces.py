import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import RESERVATION_STATUSES, SPACE_STATUSES
from app.models import Reservation, Space
from app.schemas.campus import AvailabilityOut, ReservationCreate, ReservationOut, ReservationPatch
from app.services.errors import DomainError
from app.services.reservation_rules import validate_reservation_window
from app.validators.audit import reject_audit_markers

_write_lock = threading.Lock()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def overlapping_query(space_id: str, starts_at: datetime, ends_at: datetime, ignore_id: str | None = None):
    statement = select(Reservation).where(
        Reservation.space_id == space_id,
        Reservation.status == "active",
        Reservation.starts_at < ends_at,
        Reservation.ends_at > starts_at,
    )
    if ignore_id:
        statement = statement.where(Reservation.id != ignore_id)
    return statement


def list_spaces(db: Session) -> list[Space]:
    return list(db.scalars(select(Space).order_by(Space.name)))


def get_space(db: Session, space_id: str) -> Space:
    space = db.get(Space, space_id)
    if space is None:
        raise DomainError("El espacio no existe.", 404)
    return space


def list_reservations(
    db: Session,
    space_id: str | None = None,
    status: str | None = None,
) -> list[ReservationOut]:
    statement = select(Reservation, Space.name).join(Space, Space.id == Reservation.space_id)
    if space_id:
        statement = statement.where(Reservation.space_id == space_id)
    if status:
        statement = statement.where(Reservation.status == status)
    statement = statement.order_by(Reservation.starts_at.desc())
    rows = db.execute(statement).all()
    return [ReservationOut.from_model(reservation, space_name) for reservation, space_name in rows]


def check_availability(
    db: Session,
    space_id: str,
    starts_at: datetime,
    ends_at: datetime,
) -> AvailabilityOut:
    starts_at = _naive(starts_at)
    ends_at = _naive(ends_at)
    space = get_space(db, space_id)
    try:
        validate_reservation_window(starts_at, ends_at)
    except DomainError as exc:
        return AvailabilityOut(
            space_id=space.id,
            available=False,
            reason=exc.message,
            conflicts=[],
        )
    if space.status != "available":
        return AvailabilityOut(
            space_id=space.id,
            available=False,
            reason=f"El espacio no está disponible (estado: {space.status}).",
            conflicts=[],
        )
    conflicts = list(db.scalars(overlapping_query(space.id, starts_at, ends_at)))
    if conflicts:
        return AvailabilityOut(
            space_id=space.id,
            available=False,
            reason="Ya existe una reserva activa que se solapa con ese intervalo.",
            conflicts=[ReservationOut.from_model(item, space.name) for item in conflicts],
        )
    return AvailabilityOut(
        space_id=space.id,
        available=True,
        reason="El espacio está libre en ese intervalo.",
        conflicts=[],
    )


def create_reservation(db: Session, payload: ReservationCreate) -> Reservation:
    reject_audit_markers(payload.space_id, payload.requester_name, payload.purpose)
    starts_at = _naive(payload.starts_at)
    ends_at = _naive(payload.ends_at)
    validate_reservation_window(starts_at, ends_at)

    with _write_lock:
        space = db.get(Space, payload.space_id)
        if space is None:
            raise DomainError("El espacio no existe.", 404)
        if space.status != "available":
            raise DomainError(
                f"No se puede reservar el espacio porque su estado es '{space.status}'.",
                409,
            )
        if payload.attendees > space.capacity:
            raise DomainError(
                f"La cantidad de asistentes ({payload.attendees}) supera la capacidad del espacio ({space.capacity}).",
                422,
            )
        conflict = db.scalar(overlapping_query(space.id, starts_at, ends_at))
        if conflict is not None:
            raise DomainError(
                "No se puede reservar: el intervalo se solapa con la reserva activa "
                f"{conflict.id} ({conflict.starts_at.isoformat(sep=' ', timespec='minutes')} – "
                f"{conflict.ends_at.isoformat(sep=' ', timespec='minutes')}). "
                "Las reservas canceladas no bloquean el horario. "
                "Dos reservas seguidas son válidas si una termina cuando la otra empieza.",
                409,
            )
        reservation = Reservation(
            id=new_id(),
            space_id=space.id,
            requester_name=payload.requester_name.strip(),
            purpose=payload.purpose.strip(),
            attendees=payload.attendees,
            starts_at=starts_at,
            ends_at=ends_at,
            status="active",
            created_at=utcnow(),
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation


def cancel_reservation(db: Session, reservation_id: str) -> Reservation:
    with _write_lock:
        reservation = db.get(Reservation, reservation_id)
        if reservation is None:
            raise DomainError("La reserva no existe.", 404)
        if reservation.status == "cancelled":
            raise DomainError("La reserva ya está cancelada.", 409)
        reservation.status = "cancelled"
        db.commit()
        db.refresh(reservation)
        return reservation


def update_space_status(db: Session, space_id: str, status: str, note: str = "") -> Space:
    reject_audit_markers(space_id, status, note)
    if status not in SPACE_STATUSES:
        raise DomainError("Estado de sala no válido. Use available, disabled o maintenance.", 422)
    with _write_lock:
        space = get_space(db, space_id)
        space.status = status
        if note.strip():
            suffix = f" [{note.strip()}]"
            if suffix not in space.description:
                space.description = (space.description or "").rstrip() + suffix
        db.commit()
        db.refresh(space)
        return space


def update_reservation(db: Session, reservation_id: str, payload: ReservationPatch) -> Reservation:
    reject_audit_markers(
        reservation_id,
        payload.requester_name,
        payload.purpose,
        payload.status,
    )
    with _write_lock:
        reservation = db.get(Reservation, reservation_id)
        if reservation is None:
            raise DomainError("La reserva no existe.", 404)

        requester_name = (
            payload.requester_name.strip() if payload.requester_name is not None else reservation.requester_name
        )
        purpose = payload.purpose.strip() if payload.purpose is not None else reservation.purpose
        attendees = payload.attendees if payload.attendees is not None else reservation.attendees
        starts_at = _naive(payload.starts_at) if payload.starts_at is not None else reservation.starts_at
        ends_at = _naive(payload.ends_at) if payload.ends_at is not None else reservation.ends_at
        status = payload.status if payload.status is not None else reservation.status

        if status not in RESERVATION_STATUSES:
            raise DomainError("Estado de reserva no válido. Use active o cancelled.", 422)
        validate_reservation_window(starts_at, ends_at)

        space = get_space(db, reservation.space_id)
        if status == "active":
            if space.status != "available":
                raise DomainError(
                    f"No se puede activar la reserva porque la sala está '{space.status}'.",
                    409,
                )
            if attendees > space.capacity:
                raise DomainError(
                    f"La cantidad de asistentes ({attendees}) supera la capacidad del espacio ({space.capacity}).",
                    422,
                )
            conflict = db.scalar(overlapping_query(space.id, starts_at, ends_at, ignore_id=reservation.id))
            if conflict is not None:
                raise DomainError(
                    "No se puede actualizar: el intervalo se solapa con la reserva activa "
                    f"{conflict.id}.",
                    409,
                )

        reservation.requester_name = requester_name
        reservation.purpose = purpose
        reservation.attendees = attendees
        reservation.starts_at = starts_at
        reservation.ends_at = ends_at
        reservation.status = status
        db.commit()
        db.refresh(reservation)
        return reservation
