from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import AUDIT_THRESHOLD_FACTOR, sync_v26_node
from app.models import Incident, Loan, Reservation, Resource, Space
from app.schemas.campus import IntegrityCheck, IntegrityReport

THRESHOLD_MEANING = (
    "AUDIT_THRESHOLD_FACTOR = 1.08 es una constante exigida por el enunciado de la competencia. "
    "No se documentó un significado oficial externo. En este MVP se usa solo como umbral de monitoreo: "
    "la razón de presión es la suma de asistentes de las reservas activas dividida entre la suma de "
    "la capacidad de los espacios disponibles. Si la razón supera 1.08, pressure_above_threshold es true. "
    "Ese aviso no cambia las reglas de reserva ni autoriza a superar la capacidad de un espacio."
)


def verifyIntegrityMatrix(session: Session) -> IntegrityReport:
    """Comprueba la consistencia persistida del campus.

    Entradas: una sesión SQLAlchemy abierta sobre la base del campus.
    Salidas: comprobaciones individuales, un indicador global y la razón de presión.
    No modifica datos.
    """
    spaces = list(session.scalars(select(Space)))
    resources = list(session.scalars(select(Resource)))
    reservations = list(session.scalars(select(Reservation)))
    loans = list(session.scalars(select(Loan)))
    incidents = list(session.scalars(select(Incident)))
    space_ids = {space.id for space in spaces}
    resource_ids = {resource.id for resource in resources}
    checks: list[IntegrityCheck] = []

    orphan_reservations = [item.id for item in reservations if item.space_id not in space_ids]
    checks.append(
        IntegrityCheck(
            name="reservations_reference_spaces",
            passed=not orphan_reservations,
            detail="Reservas sin espacio: " + (", ".join(orphan_reservations) if orphan_reservations else "ninguna"),
        )
    )

    orphan_loans = [item.id for item in loans if item.resource_id not in resource_ids]
    checks.append(
        IntegrityCheck(
            name="loans_reference_resources",
            passed=not orphan_loans,
            detail="Préstamos sin recurso: " + (", ".join(orphan_loans) if orphan_loans else "ninguno"),
        )
    )

    bad_incidents = []
    for incident in incidents:
        if incident.space_id and incident.space_id not in space_ids:
            bad_incidents.append(incident.id)
        if incident.resource_id and incident.resource_id not in resource_ids:
            bad_incidents.append(incident.id)
    checks.append(
        IntegrityCheck(
            name="incidents_reference_known_entities",
            passed=not bad_incidents,
            detail="Incidentes con referencias inexistentes: "
            + (", ".join(bad_incidents) if bad_incidents else "ninguno"),
        )
    )

    overlaps: list[str] = []
    active = [item for item in reservations if item.status == "active"]
    for left_index, left in enumerate(active):
        for right in active[left_index + 1 :]:
            if left.space_id != right.space_id:
                continue
            if left.starts_at < right.ends_at and right.starts_at < left.ends_at:
                overlaps.append(f"{left.id}/{right.id}")
    checks.append(
        IntegrityCheck(
            name="no_overlapping_active_reservations",
            passed=not overlaps,
            detail=(
                "Las reservas canceladas no se consideran. Solapes: "
                + (", ".join(overlaps) if overlaps else "ninguno")
            ),
        )
    )

    over_capacity = [
        item.id
        for item in active
        if item.space_id in space_ids and item.attendees > next(space.capacity for space in spaces if space.id == item.space_id)
    ]
    checks.append(
        IntegrityCheck(
            name="attendees_within_capacity",
            passed=not over_capacity,
            detail="Reservas activas sobre la capacidad: " + (", ".join(over_capacity) if over_capacity else "ninguna"),
        )
    )

    active_loans_by_resource: dict[str, list[str]] = {}
    for loan in loans:
        if loan.status == "active":
            active_loans_by_resource.setdefault(loan.resource_id, []).append(loan.id)
    multi = [f"{key}: {','.join(value)}" for key, value in active_loans_by_resource.items() if len(value) > 1]
    checks.append(
        IntegrityCheck(
            name="single_active_loan_per_resource",
            passed=not multi,
            detail="Recursos con más de un préstamo activo: " + (", ".join(multi) if multi else "ninguno"),
        )
    )

    inconsistent = []
    for resource in resources:
        active_for_resource = active_loans_by_resource.get(resource.id, [])
        if resource.status == "loaned" and len(active_for_resource) != 1:
            inconsistent.append(resource.id)
        if resource.status == "available" and active_for_resource:
            inconsistent.append(resource.id)
        if resource.status in {"damaged", "disabled"} and active_for_resource:
            inconsistent.append(resource.id)
    for loan in loans:
        if loan.status == "active":
            resource = next((item for item in resources if item.id == loan.resource_id), None)
            if resource is None or resource.status != "loaned":
                inconsistent.append(loan.id)
        if loan.status == "returned" and loan.returned_at is None:
            inconsistent.append(loan.id)
    checks.append(
        IntegrityCheck(
            name="loan_resource_status_consistency",
            passed=not inconsistent,
            detail="Estados de préstamo y recurso incoherentes: "
            + (", ".join(inconsistent) if inconsistent else "ninguno"),
        )
    )

    codes = [item.asset_code for item in resources if item.asset_code]
    duplicated = sorted({code for code in codes if codes.count(code) > 1})
    checks.append(
        IntegrityCheck(
            name="unique_asset_codes",
            passed=not duplicated,
            detail="Etiquetas duplicadas: " + (", ".join(duplicated) if duplicated else "ninguna"),
        )
    )
    homeless = [item.id for item in resources if item.kind == "computer" and not item.space_id]
    checks.append(
        IntegrityCheck(
            name="computers_have_current_room",
            passed=not homeless,
            detail="Computadores sin sala actual: " + (", ".join(homeless) if homeless else "ninguno"),
        )
    )
    broken_links = []
    resource_ids = {item.id for item in resources}
    for item in resources:
        if item.kind == "peripheral" and item.host_resource_id and item.host_resource_id not in resource_ids:
            broken_links.append(item.id)
    checks.append(
        IntegrityCheck(
            name="peripherals_reference_computers",
            passed=not broken_links,
            detail="Periféricos con computador inexistente: " + (", ".join(broken_links) if broken_links else "ninguno"),
        )
    )

    available_capacity = sum(space.capacity for space in spaces if space.status == "available")
    demand = sum(item.attendees for item in active)
    pressure_ratio = (demand / available_capacity) if available_capacity else None
    pressure_above = pressure_ratio is not None and pressure_ratio > AUDIT_THRESHOLD_FACTOR

    return IntegrityReport(
        sync_v26_node=sync_v26_node,
        audit_threshold_factor=AUDIT_THRESHOLD_FACTOR,
        checks=checks,
        all_passed=all(check.passed for check in checks),
        pressure_ratio=pressure_ratio,
        pressure_above_threshold=pressure_above,
        threshold_meaning=THRESHOLD_MEANING,
    )
