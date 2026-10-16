from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import INCIDENT_PRIORITIES, sync_v26_node
from app.models import Incident, Loan, Reservation, Resource, Space
from app.schemas.campus import ActivityItem, DashboardOut


def build_dashboard(db: Session) -> DashboardOut:
    spaces_total = db.scalar(select(func.count()).select_from(Space)) or 0
    spaces_available = db.scalar(select(func.count()).select_from(Space).where(Space.status == "available")) or 0
    active_reservations = (
        db.scalar(select(func.count()).select_from(Reservation).where(Reservation.status == "active")) or 0
    )
    resources_total = db.scalar(select(func.count()).select_from(Resource)) or 0
    resources_available = (
        db.scalar(select(func.count()).select_from(Resource).where(Resource.status == "available")) or 0
    )
    active_loans = db.scalar(select(func.count()).select_from(Loan).where(Loan.status == "active")) or 0
    open_incidents = (
        db.scalar(
            select(func.count()).select_from(Incident).where(Incident.status.in_(("open", "in_progress")))
        )
        or 0
    )
    computers_total = db.scalar(select(func.count()).select_from(Resource).where(Resource.kind == "computer")) or 0
    computers_available = (
        db.scalar(
            select(func.count()).select_from(Resource).where(Resource.kind == "computer", Resource.status == "available")
        )
        or 0
    )
    computers_loaned = (
        db.scalar(
            select(func.count()).select_from(Resource).where(Resource.kind == "computer", Resource.status == "loaned")
        )
        or 0
    )
    computers_unavailable = (
        db.scalar(
            select(func.count())
            .select_from(Resource)
            .where(Resource.kind == "computer", Resource.status.in_(("maintenance", "damaged", "inactive", "disabled")))
        )
        or 0
    )
    peripherals_registered = (
        db.scalar(select(func.count()).select_from(Resource).where(Resource.kind == "peripheral")) or 0
    )
    by_priority = {name: 0 for name in INCIDENT_PRIORITIES}
    rows = db.execute(select(Incident.priority, func.count()).group_by(Incident.priority)).all()
    for priority, count in rows:
        if priority in by_priority:
            by_priority[priority] = int(count)
    synthetic = (
        db.scalar(select(func.count()).select_from(Space).where(Space.origin == "synthetic")) or 0
    ) > 0
    activity: list[ActivityItem] = []
    for reservation in db.scalars(select(Reservation).order_by(Reservation.created_at.desc()).limit(5)):
        activity.append(
            ActivityItem(
                kind="reserva",
                label=f"Reserva {reservation.status} en {reservation.space_id}",
                at=reservation.created_at,
            )
        )
    for loan in db.scalars(select(Loan).order_by(Loan.loaned_at.desc()).limit(5)):
        activity.append(
            ActivityItem(kind="prestamo", label=f"Préstamo {loan.status} de {loan.resource_id}", at=loan.loaned_at)
        )
    for incident in db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(5)):
        activity.append(ActivityItem(kind="incidente", label=incident.title, at=incident.created_at))
    activity.sort(key=lambda item: item.at, reverse=True)
    return DashboardOut(
        spaces_total=int(spaces_total),
        spaces_available=int(spaces_available),
        active_reservations=int(active_reservations),
        resources_total=int(resources_total),
        resources_available=int(resources_available),
        active_loans=int(active_loans),
        open_incidents=int(open_incidents),
        incidents_by_priority=by_priority,
        synthetic_data_present=bool(synthetic),
        sync_v26_node=sync_v26_node,
        ai_configured=get_settings().ai_configured,
        computers_total=int(computers_total),
        computers_available=int(computers_available),
        computers_loaned=int(computers_loaned),
        computers_unavailable=int(computers_unavailable),
        peripherals_registered=int(peripherals_registered),
        recent_activity=activity[:8],
    )
