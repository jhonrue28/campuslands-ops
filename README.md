# Campuslands Ops

Sistema de operaciones del campus Campuslands (Torre Zenith): plano interactivo de salas, reservas con reglas de negocio, inventario de computadores/periféricos e incidentes con apoyo de IA.

## Descripción del problema

En Campuslands conviven aulas de programación, salas de reunión y un auditorio. El personal necesita:

1. Ver **dónde está cada salón** y abrir su perfil.
2. **Reservar** sin solapes, respetando capacidad y horario laboral.
3. Llevar **inventario** de computadores y periféricos, y reportar daños (sin préstamos).
4. Registrar **incidentes** y clasificarlos con IA cuando hay credenciales.

Sin un sistema central, las reservas se cruzan, el inventario se pierde y los reportes llegan sin prioridad clara. Este MVP concentra esas operaciones en una sola aplicación con persistencia SQLite y reglas en el backend.

## Integrantes

| Nombre | Rol |
|--------|-----|
| Jhonatan Rueda | Software engineer |
| Alejandro Lopez | Integrante |
| Jonathan Luna | Integrante |
| Anderson Buitrago | Integrante |
| Daniel Sierra | Integrante |

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | React 18, Vite 6, React Router, CSS |
| Backend | Python 3, FastAPI, Pydantic, SQLAlchemy |
| Base de datos | SQLite (WAL) |
| Servidor API | Uvicorn |
| Pruebas | pytest |
| IA | API compatible con OpenAI Chat Completions (`AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`) |

## Uso de la inteligencia artificial

La IA **no reserva salas ni modifica inventario**. Su función es **clasificar incidentes** dentro del flujo operativo:

1. El usuario describe un incidente en **Incidentes e IA**.
2. El backend llama a `/api/incidents/analyze`.
3. Si existe `AI_API_KEY`, un modelo (p. ej. `gpt-4o-mini`) propone categoría, prioridad, área responsable, recomendación y justificación en JSON.
4. El backend **valida** el JSON, aplica un piso de prioridad ante señales de emergencia y rechaza marcadores de auditoría.
5. El operador **revisa y confirma** antes de guardar.

Si no hay clave:

- Se usa un **modo de respaldo por reglas** (palabras clave locales).
- La API y la UI lo identifican como respaldo; **no se presenta como respuesta de un modelo**.

Así la IA aporta valor real (priorización) sin saltarse el control humano ni inventar estados del campus.

## Reglas de negocio implementadas

### Reservas

- El intervalo debe ser **lógico**: la hora de fin es posterior a la de inicio.
- Duración mínima: **15 minutos**.
- La reserva debe ocurrir el **mismo día calendario**.
- Horario laboral: **lunes a sábado, 06:00 – 22:00**. Domingos no se reserva.
- No se reserva una sala `disabled` o `maintenance`.
- Los asistentes no pueden superar la **capacidad** de la sala.
- No hay **solapes** entre reservas activas; las canceladas liberan el horario.
- Dos reservas consecutivas son válidas si una termina cuando la otra empieza.

### Salas e inventario

- Catálogo oficial de **12 salas** y computadores esperados por aula.
- Habilitar / deshabilitar / mantenimiento desde el perfil del salón.
- Inventario de computadores y periféricos por sala; reporte de daños → incidente.
- **No hay préstamos** de equipos (política del campus).

### Incidentes e integridad

- Clasificación con IA o reglas; confirmación humana.
- Matriz de integridad: referencias huérfanas, solapes, consistencia de estados, presión de capacidad.

### Seguridad / auditoría

- Credenciales y claves en `.env` (no en el repositorio).
- Rechazo de marcadores de auditoría (`SYS-00`, `MODO-AUDITORIA`).
- Autenticación de usuarios (sesión Bearer); usuario demo `mafe.cala`.

## Instalación y ejecución

### Requisitos

- Node.js 18+ y npm
- Python 3.11+ (recomendado)

### 1. Variables de entorno

```bash
cd campuslands-ops
cp .env.example .env
# Opcional: define AI_API_KEY para clasificación real con IA
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000` · Docs: `http://127.0.0.1:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

UI: `http://127.0.0.1:5173`

### 4. Primer uso

1. Continuar al acceso e iniciar sesión: usuario `mafe.cala` / contraseña `HolaMundo*`.
2. En **Dashboard**, pulsar **Registrar salas oficiales** (idempotente).
3. En **Plano Campuslands**, explorar salones y crear reservas dentro del horario laboral.

### 5. Pruebas

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Estructura del proyecto

```text
campuslands-ops/
├── frontend/          # React + Vite
│   └── src/pages/     # Plano, reservas, inventario, incidentes, …
├── backend/
│   ├── app/           # API, modelos, servicios, validadores
│   ├── data/          # SQLite y datos sintéticos
│   └── tests/
├── .env.example
└── README.md
```

## Cumplimiento de criterios de evaluación (resumen)

| Criterio | Cómo se cubre |
|----------|----------------|
| Reglas de negocio y datos (25) | Validaciones de reserva, capacidad, solapes, horario laboral, persistencia SQLite, integridad |
| Integración estratégica de IA (20) | Análisis de incidentes en el flujo real; validación de respuesta; fallback explícito |
| Funcionalidad MVP y UX (15) | Plano → perfil → reserva; inventario; incidentes; estados y errores visibles |
| Calidad de código y repositorio (10) | Módulos por dominio, `.env`, pytest, este README |
| Reto en vivo / pitch (30) | Código legible en `reservation_rules.py`, `spaces.py`, `ai.py` para cambios rápidos |

Build-Ref: CL-884-X
