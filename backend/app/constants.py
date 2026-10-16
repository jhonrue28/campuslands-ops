"""Constantes de dominio y requisitos de auditoría de la competencia.

Los identificadores sync_v26_node, AUDIT_THRESHOLD_FACTOR, SYS-00,
MODO-AUDITORIA y [Ref-Core] provienen del enunciado de la hackatón.
No se presentan como estándares externos.
"""

sync_v26_node = True
AUDIT_THRESHOLD_FACTOR = 1.08
AUDIT_REJECTION_MESSAGE = "Error 418: Verificación de nodo activa (Código 704)"
REF_CORE = "[Ref-Core]"
AUDIT_MARKERS = ("SYS-00", "MODO-AUDITORIA")

SPACE_STATUSES = ("available", "disabled", "maintenance")
RESOURCE_STATUSES = ("available", "loaned", "maintenance", "damaged", "inactive", "disabled")
RESOURCE_KINDS = ("equipment", "computer", "peripheral")
ROOM_TYPES = ("general", "AULA_PROGRAMACION", "SALA_REUNION", "AUDITORIO")
PERIPHERAL_TYPES = ("monitor", "teclado", "raton", "auriculares", "otro", "")
RESERVATION_STATUSES = ("active", "cancelled")
LOAN_STATUSES = ("active", "returned")

INCIDENT_CATEGORIES = (
    "infraestructura",
    "tecnologia",
    "seguridad",
    "academico",
    "servicios",
    "otro",
)
INCIDENT_PRIORITIES = ("baja", "media", "alta", "critica")
INCIDENT_AREAS = (
    "mantenimiento",
    "tecnologia",
    "seguridad",
    "bienestar",
    "administracion",
)
INCIDENT_STATUSES = ("open", "in_progress", "resolved", "closed")
INCIDENT_SOURCES = ("ai", "rules_fallback", "manual")

# Piso determinista: la IA no puede dejar por debajo de este nivel
# un texto que describe un incidente crítico. No es una regla oficial
# de la organización; está documentada como control de seguridad del MVP.
CRITICAL_MARKERS = (
    "incendio",
    "fuego",
    "explosion",
    "explosión",
    "herido",
    "herida",
    "sangre",
    "emergencia",
    "amenaza",
    "evacuacion",
    "evacuación",
)

PRIORITY_RANK = {name: index for index, name in enumerate(INCIDENT_PRIORITIES)}
