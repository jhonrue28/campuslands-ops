"""Catálogo de salas indicado para esta operación.

Las capacidades y los nombres salen de la tabla entregada para el campus.
La suma de esas capacidades es 295. El enunciado también menciona 201;
no se alteran las capacidades de la tabla para forzar esa cifra.
"""

OFFICIAL_ROOMS = (
    {"id": "sala-auditorio", "name": "Auditorio", "capacity": 100, "room_type": "AUDITORIO", "expected_computers": 0},
    {"id": "sala-cosmos", "name": "Cosmos", "capacity": 25, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "sala-blanca", "name": "Blanca", "capacity": 12, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "sala-azul", "name": "Azul", "capacity": 10, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "sala-amarilla-1", "name": "Sala Amarilla 1", "capacity": 6, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "sala-amarilla-2", "name": "Sala Amarilla 2", "capacity": 6, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "sala-verde-1", "name": "Sala verde 1", "capacity": 6, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "sala-verde-2", "name": "Sala verde 2", "capacity": 6, "room_type": "SALA_REUNION", "expected_computers": 0},
    {"id": "aula-artemis", "name": "Artemis", "capacity": 32, "room_type": "AULA_PROGRAMACION", "expected_computers": 34},
    {"id": "aula-skylab", "name": "Skylab", "capacity": 20, "room_type": "AULA_PROGRAMACION", "expected_computers": 20},
    {"id": "aula-sputnik", "name": "Sputnik", "capacity": 38, "room_type": "AULA_PROGRAMACION", "expected_computers": 38},
    {"id": "aula-apolo", "name": "Apolo", "capacity": 34, "room_type": "AULA_PROGRAMACION", "expected_computers": 34},
)

PROVISIONAL_NOTE = ""
