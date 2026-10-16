from datetime import datetime

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import AUDIT_REJECTION_MESSAGE, sync_v26_node
from app.db.session import get_db
from app.schemas.campus import (
    AvailabilityOut,
    DashboardOut,
    ImportReportOut,
    IncidentAnalysis,
    IncidentAnalyzeIn,
    IncidentCreate,
    IncidentOut,
    IncidentPatch,
    IntegrityReport,
    LoanCreate,
    LoanOut,
    LocationChange,
    PeripheralCreate,
    PeripheralHostChange,
    ReservationCreate,
    ReservationOut,
    ReservationPatch,
    ResourceOut,
    SpaceOut,
    SpaceStatusChange,
    StatusChange,
    ComputerCreate,
    ComputerPatch,
    LoginIn,
    UserCreate,
    UserOut,
    UserPatch,
)
from app.services.ai import analyze_text
from app.services.auth import (
    create_user,
    current_user,
    delete_user,
    list_users,
    login,
    logout,
    serialize_user,
    update_user,
)
from app.services.dashboard import build_dashboard
from app.services.errors import DomainError
from app.models import User
from app.services.importer import import_csv_text, import_json_text, import_synthetic, list_reports
from app.services.incidents import create_incident, get_incident, list_incidents, serialize_incident, update_incident
from app.services.integrity import verifyIntegrityMatrix
from app.services.inventory import (
    change_location,
    change_status,
    computer_detail,
    initialize_official_catalog,
    list_computers,
    list_peripherals,
    reassign_peripheral,
    register_computer,
    register_peripheral,
    room_summary,
    spaces_with_counts,
    update_computer,
)
from app.services.resources import create_loan, get_resource, list_loans, list_resources, return_loan
from app.services.spaces import (
    cancel_reservation,
    check_availability,
    create_reservation,
    get_space,
    list_reservations,
    list_spaces,
    update_reservation,
    update_space_status,
)
from app.validators.audit import contains_audit_marker, reject_audit_markers

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    settings = get_settings()
    return {
        "status": "ok",
        "sync_v26_node": sync_v26_node,
        "database": "ok",
        "ai_configured": settings.ai_configured,
    }


@router.post("/auth/login")
def auth_login(payload: LoginIn, db: Session = Depends(get_db)) -> dict:
    return login(db, payload.username, payload.password)


@router.post("/auth/logout")
def auth_logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(current_user),
) -> dict:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    logout(db, token)
    return {"ok": True}


@router.get("/auth/me")
def auth_me(user: User = Depends(current_user)) -> dict:
    return serialize_user(user)


@router.get("/users", response_model=list[UserOut])
def users_list(_user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_user(item) for item in list_users(db)]


@router.post("/users", response_model=UserOut, status_code=201)
def users_create(payload: UserCreate, _user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return serialize_user(
        create_user(
            db,
            full_name=payload.full_name,
            username=payload.username,
            password=payload.password,
            role=payload.role,
            notes=payload.notes,
            active=payload.active,
        )
    )


@router.patch("/users/{user_id}", response_model=UserOut)
def users_patch(
    user_id: str,
    payload: UserPatch,
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    reject_audit_markers(user_id)
    return serialize_user(
        update_user(
            db,
            user_id,
            full_name=payload.full_name,
            username=payload.username,
            password=payload.password,
            role=payload.role,
            notes=payload.notes,
            active=payload.active,
        )
    )


@router.delete("/users/{user_id}")
def users_delete(user_id: str, _user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    reject_audit_markers(user_id)
    delete_user(db, user_id)
    return {"ok": True}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    return build_dashboard(db)


@router.get("/integrity", response_model=IntegrityReport)
def integrity(db: Session = Depends(get_db)) -> IntegrityReport:
    return verifyIntegrityMatrix(db)


@router.get("/spaces", response_model=list[SpaceOut])
def spaces(db: Session = Depends(get_db)) -> list[SpaceOut]:
    return spaces_with_counts(db)


@router.get("/spaces/{space_id}/availability", response_model=AvailabilityOut)
def space_availability(
    space_id: str,
    starts_at: datetime,
    ends_at: datetime,
    db: Session = Depends(get_db),
) -> AvailabilityOut:
    reject_audit_markers(space_id)
    return check_availability(db, space_id, starts_at, ends_at)


@router.get("/spaces/{space_id}", response_model=SpaceOut)
def space_detail(space_id: str, db: Session = Depends(get_db)) -> SpaceOut:
    reject_audit_markers(space_id)
    space = get_space(db, space_id)
    counts = {item.id: item.computers_registered for item in spaces_with_counts(db)}
    return SpaceOut.from_model(space, counts.get(space.id, 0))


@router.patch("/spaces/{space_id}/status", response_model=SpaceOut)
def patch_space_status(space_id: str, payload: SpaceStatusChange, db: Session = Depends(get_db)) -> SpaceOut:
    reject_audit_markers(space_id)
    space = update_space_status(db, space_id, payload.status, payload.note)
    counts = {item.id: item.computers_registered for item in spaces_with_counts(db)}
    return SpaceOut.from_model(space, counts.get(space.id, 0))


@router.get("/spaces/{space_id}/computers", response_model=list[ResourceOut])
def space_computers(space_id: str, db: Session = Depends(get_db)) -> list[ResourceOut]:
    reject_audit_markers(space_id)
    get_space(db, space_id)
    return [ResourceOut.from_model(item) for item in list_computers(db, space_id)]


@router.get("/reservations", response_model=list[ReservationOut])
def reservations(
    space_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[ReservationOut]:
    reject_audit_markers(space_id, status)
    return list_reservations(db, space_id=space_id, status=status)


@router.post("/reservations", response_model=ReservationOut, status_code=201)
def post_reservation(payload: ReservationCreate, db: Session = Depends(get_db)) -> ReservationOut:
    reservation = create_reservation(db, payload)
    space = get_space(db, reservation.space_id)
    return ReservationOut.from_model(reservation, space.name)


@router.patch("/reservations/{reservation_id}", response_model=ReservationOut)
def patch_reservation(reservation_id: str, payload: ReservationPatch, db: Session = Depends(get_db)) -> ReservationOut:
    reject_audit_markers(reservation_id)
    reservation = update_reservation(db, reservation_id, payload)
    space = get_space(db, reservation.space_id)
    return ReservationOut.from_model(reservation, space.name)


@router.patch("/reservations/{reservation_id}/cancel", response_model=ReservationOut)
def patch_cancel_reservation(reservation_id: str, db: Session = Depends(get_db)) -> ReservationOut:
    reject_audit_markers(reservation_id)
    reservation = cancel_reservation(db, reservation_id)
    space = get_space(db, reservation.space_id)
    return ReservationOut.from_model(reservation, space.name)


@router.get("/resources", response_model=list[ResourceOut])
def resources(db: Session = Depends(get_db)) -> list[ResourceOut]:
    return [ResourceOut.from_model(resource) for resource in list_resources(db)]


@router.get("/catalog/rooms")
def catalog_rooms(db: Session = Depends(get_db)) -> list[dict]:
    return room_summary(db)


@router.post("/catalog/official")
def catalog_official(db: Session = Depends(get_db)) -> dict:
    return initialize_official_catalog(db)


@router.get("/computers", response_model=list[ResourceOut])
def computers(space_id: str | None = None, db: Session = Depends(get_db)) -> list[ResourceOut]:
    reject_audit_markers(space_id)
    return [ResourceOut.from_model(item) for item in list_computers(db, space_id)]


@router.get("/computers/{resource_id}")
def computer(resource_id: str, db: Session = Depends(get_db)) -> dict:
    reject_audit_markers(resource_id)
    return computer_detail(db, resource_id)


@router.post("/computers", response_model=ResourceOut, status_code=201)
def post_computer(payload: ComputerCreate, db: Session = Depends(get_db)) -> ResourceOut:
    resource = register_computer(
        db,
        name=payload.name,
        space_id=payload.space_id,
        asset_code=payload.asset_code,
        notes=payload.notes,
        hardware_notes=payload.hardware_notes,
        provisional=payload.provisional,
    )
    return ResourceOut.from_model(resource)


@router.patch("/computers/{resource_id}", response_model=ResourceOut)
def patch_computer(resource_id: str, payload: ComputerPatch, db: Session = Depends(get_db)) -> ResourceOut:
    reject_audit_markers(resource_id)
    return ResourceOut.from_model(
        update_computer(
            db,
            resource_id,
            name=payload.name,
            notes=payload.notes,
            hardware_notes=payload.hardware_notes,
            asset_code=payload.asset_code,
        )
    )


@router.post("/computers/{resource_id}/status", response_model=ResourceOut)
def post_computer_status(resource_id: str, payload: StatusChange, db: Session = Depends(get_db)) -> ResourceOut:
    reject_audit_markers(resource_id)
    return ResourceOut.from_model(change_status(db, resource_id, payload.status, payload.note))


@router.post("/computers/{resource_id}/location", response_model=ResourceOut)
def post_computer_location(resource_id: str, payload: LocationChange, db: Session = Depends(get_db)) -> ResourceOut:
    reject_audit_markers(resource_id, payload.space_id)
    return ResourceOut.from_model(change_location(db, resource_id, payload.space_id))


@router.get("/peripherals", response_model=list[ResourceOut])
def peripherals(host_id: str | None = None, space_id: str | None = None, db: Session = Depends(get_db)) -> list[ResourceOut]:
    reject_audit_markers(host_id, space_id)
    return [ResourceOut.from_model(item) for item in list_peripherals(db, host_id, space_id)]


@router.post("/peripherals", response_model=ResourceOut, status_code=201)
def post_peripheral(payload: PeripheralCreate, db: Session = Depends(get_db)) -> ResourceOut:
    return ResourceOut.from_model(
        register_peripheral(
            db,
            name=payload.name,
            peripheral_type=payload.peripheral_type,
            host_resource_id=payload.host_resource_id,
            space_id=payload.space_id,
            asset_code=payload.asset_code,
            notes=payload.notes,
            brand=payload.brand,
            model_name=payload.model_name,
        )
    )


@router.post("/peripherals/{peripheral_id}/host", response_model=ResourceOut)
def post_peripheral_host(
    peripheral_id: str,
    payload: PeripheralHostChange,
    db: Session = Depends(get_db),
) -> ResourceOut:
    reject_audit_markers(peripheral_id, payload.host_resource_id)
    return ResourceOut.from_model(reassign_peripheral(db, peripheral_id, payload.host_resource_id))


@router.get("/loans", response_model=list[LoanOut])
def loans(status: str | None = None, db: Session = Depends(get_db)) -> list[LoanOut]:
    reject_audit_markers(status)
    if status is not None and status not in {"active", "returned"}:
        raise DomainError("El estado del préstamo debe ser active o returned.", 422)
    return list_loans(db, status=status)


@router.post("/loans", response_model=LoanOut, status_code=201)
def post_loan(payload: LoanCreate, db: Session = Depends(get_db)) -> LoanOut:
    loan = create_loan(db, payload)
    resource = get_resource(db, loan.resource_id)
    return LoanOut.from_model(loan, resource.name)


@router.post("/loans/{loan_id}/return", response_model=LoanOut)
def post_return_loan(loan_id: str, db: Session = Depends(get_db)) -> LoanOut:
    reject_audit_markers(loan_id)
    loan = return_loan(db, loan_id)
    resource = get_resource(db, loan.resource_id)
    return LoanOut.from_model(loan, resource.name)


@router.post("/incidents/analyze", response_model=IncidentAnalysis)
def analyze_incident(payload: IncidentAnalyzeIn, db: Session = Depends(get_db)) -> IncidentAnalysis:
    from app.services.incidents import _ensure_links

    reject_audit_markers(payload.description, payload.space_id, payload.resource_id)
    _ensure_links(db, payload.space_id, payload.resource_id)
    return analyze_text(payload.description)


@router.get("/incidents", response_model=list[IncidentOut])
def incidents(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[IncidentOut]:
    reject_audit_markers(category, priority, status)
    return [serialize_incident(item) for item in list_incidents(db, category, priority, status)]


@router.post("/incidents", response_model=IncidentOut, status_code=201)
def post_incident(payload: IncidentCreate, db: Session = Depends(get_db)) -> IncidentOut:
    return serialize_incident(create_incident(db, payload), include_events=True)


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
def incident_detail(incident_id: str, db: Session = Depends(get_db)) -> IncidentOut:
    reject_audit_markers(incident_id)
    return serialize_incident(get_incident(db, incident_id), include_events=True)


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def patch_incident(incident_id: str, payload: IncidentPatch, db: Session = Depends(get_db)) -> IncidentOut:
    reject_audit_markers(incident_id)
    return serialize_incident(update_incident(db, incident_id, payload), include_events=True)


@router.post("/import/synthetic", response_model=ImportReportOut)
def import_synthetic_data(db: Session = Depends(get_db)) -> ImportReportOut:
    return import_synthetic(db)


@router.get("/import/reports", response_model=list[ImportReportOut])
def import_reports(db: Session = Depends(get_db)) -> list[ImportReportOut]:
    return list_reports(db)


@router.post("/import", response_model=ImportReportOut)
async def import_file(
    file: UploadFile = File(...),
    entity: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ImportReportOut:
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise DomainError("El archivo supera el límite de 2 MB.", 413)
    try:
        text_body = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DomainError("El archivo debe estar codificado en UTF-8.", 422) from exc
    if contains_audit_marker(text_body) or contains_audit_marker(file.filename):
        raise DomainError(AUDIT_REJECTION_MESSAGE, 418)
    name = file.filename or "upload"
    if name.lower().endswith(".csv"):
        if not entity:
            raise DomainError("Para un CSV indique el parámetro entity.", 422)
        return import_csv_text(db, text_body, entity, name)
    if not name.lower().endswith(".json"):
        raise DomainError("El archivo debe ser .json o .csv.", 422)
    return import_json_text(db, text_body, name)
