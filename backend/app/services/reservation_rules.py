"""Reglas de negocio para reservas de salas."""

from datetime import datetime, time

from app.services.errors import DomainError

# Horario regular Campuslands: lunes a sábado, 06:00 – 22:00.
BUSINESS_OPEN = time(6, 0)
BUSINESS_CLOSE = time(22, 0)
# Monday=0 … Sunday=6
BUSINESS_WEEKDAYS = {0, 1, 2, 3, 4, 5}
MIN_DURATION_MINUTES = 15


def validate_reservation_window(starts_at: datetime, ends_at: datetime) -> None:
    """Valida intervalo lógico y horario laboral."""
    if ends_at <= starts_at:
        raise DomainError("La fecha de finalización debe ser posterior a la de inicio.", 422)

    duration_minutes = (ends_at - starts_at).total_seconds() / 60
    if duration_minutes < MIN_DURATION_MINUTES:
        raise DomainError(
            f"La reserva debe durar al menos {MIN_DURATION_MINUTES} minutos.",
            422,
        )

    if starts_at.date() != ends_at.date():
        raise DomainError(
            "La reserva debe iniciar y terminar el mismo día. "
            "El horario laboral es de 06:00 a 22:00, de lunes a sábado.",
            422,
        )

    if starts_at.weekday() not in BUSINESS_WEEKDAYS:
        raise DomainError(
            "No se pueden reservar salas los domingos. El horario laboral es de lunes a sábado.",
            422,
        )

    start_t = starts_at.time()
    end_t = ends_at.time()
    if start_t < BUSINESS_OPEN or end_t > BUSINESS_CLOSE:
        raise DomainError(
            "La reserva debe quedar dentro del horario laboral "
            f"({BUSINESS_OPEN.strftime('%H:%M')} – {BUSINESS_CLOSE.strftime('%H:%M')}, lunes a sábado).",
            422,
        )
    if start_t >= BUSINESS_CLOSE:
        raise DomainError(
            "La hora de inicio debe ser anterior al cierre laboral (22:00).",
            422,
        )
