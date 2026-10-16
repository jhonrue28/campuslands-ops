import json
from datetime import datetime

from pydantic import BaseModel, Field

from app.constants import (
    INCIDENT_AREAS,
    INCIDENT_CATEGORIES,
    INCIDENT_PRIORITIES,
    INCIDENT_SOURCES,
    INCIDENT_STATUSES,
    REF_CORE,
)
from app.models import Incident, IncidentEvent, Loan, Reservation, Resource, Space


class SpaceOut(BaseModel):
    id: str
    name: str
    location: str
    capacity: int
    status: str
    features: list[str]
    description: str
    origin: str
    room_type: str = "general"
    expected_computers: int = 0
    computers_registered: int = 0

    @classmethod
    def from_model(cls, space: Space, computers_registered: int = 0) -> "SpaceOut":
        try:
            features = json.loads(space.features_json or "[]")
        except json.JSONDecodeError:
            features = []
        if not isinstance(features, list):
            features = []
        return cls(
            id=space.id,
            name=space.name,
            location=space.location,
            capacity=space.capacity,
            status=space.status,
            features=[str(item) for item in features],
            description=space.description,
            origin=space.origin,
            room_type=getattr(space, "room_type", "general") or "general",
            expected_computers=int(getattr(space, "expected_computers", 0) or 0),
            computers_registered=computers_registered,
        )


class ReservationCreate(BaseModel):
    space_id: str = Field(min_length=1, max_length=64)
    requester_name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=500)
    attendees: int = Field(ge=1, le=10000)
    starts_at: datetime
    ends_at: datetime


class ReservationPatch(BaseModel):
    requester_name: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = Field(default=None, min_length=1, max_length=500)
    attendees: int | None = Field(default=None, ge=1, le=10000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = None


class SpaceStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    note: str = Field(default="", max_length=500)


class ReservationOut(BaseModel):
    id: str
    space_id: str
    space_name: str | None = None
    requester_name: str
    purpose: str
    attendees: int
    starts_at: datetime
    ends_at: datetime
    status: str
    created_at: datetime

    @classmethod
    def from_model(cls, reservation: Reservation, space_name: str | None = None) -> "ReservationOut":
        return cls(
            id=reservation.id,
            space_id=reservation.space_id,
            space_name=space_name,
            requester_name=reservation.requester_name,
            purpose=reservation.purpose,
            attendees=reservation.attendees,
            starts_at=reservation.starts_at,
            ends_at=reservation.ends_at,
            status=reservation.status,
            created_at=reservation.created_at,
        )


class AvailabilityOut(BaseModel):
    space_id: str
    available: bool
    reason: str
    conflicts: list[ReservationOut]


class LoanCreate(BaseModel):
    resource_id: str = Field(min_length=1, max_length=64)
    borrower_name: str = Field(min_length=1, max_length=200)
    borrower_contact: str = Field(default="", max_length=200)
    purpose: str = Field(default="", max_length=500)
    due_at: datetime | None = None


class LoanOut(BaseModel):
    id: str
    resource_id: str
    resource_name: str | None = None
    borrower_name: str
    borrower_contact: str
    purpose: str
    status: str
    loaned_at: datetime
    due_at: datetime | None
    returned_at: datetime | None

    @classmethod
    def from_model(cls, loan: Loan, resource_name: str | None = None) -> "LoanOut":
        return cls(
            id=loan.id,
            resource_id=loan.resource_id,
            resource_name=resource_name,
            borrower_name=loan.borrower_name,
            borrower_contact=loan.borrower_contact,
            purpose=loan.purpose,
            status=loan.status,
            loaned_at=loan.loaned_at,
            due_at=loan.due_at,
            returned_at=loan.returned_at,
        )


class ResourceOut(BaseModel):
    id: str
    name: str
    category: str
    location: str
    status: str
    serial_number: str
    notes: str
    origin: str
    available: bool
    asset_code: str = ""
    kind: str = "equipment"
    space_id: str | None = None
    host_resource_id: str | None = None
    peripheral_type: str = ""
    brand: str = ""
    model_name: str = ""
    provisional: bool = False
    hardware_notes: str = ""

    @classmethod
    def from_model(cls, resource: Resource) -> "ResourceOut":
        return cls(
            id=resource.id,
            name=resource.name,
            category=resource.category,
            location=resource.location,
            status=resource.status,
            serial_number=resource.serial_number,
            notes=resource.notes,
            origin=resource.origin,
            available=resource.status == "available",
            asset_code=resource.asset_code or "",
            kind=resource.kind or "equipment",
            space_id=resource.space_id,
            host_resource_id=resource.host_resource_id,
            peripheral_type=resource.peripheral_type or "",
            brand=resource.brand or "",
            model_name=resource.model_name or "",
            provisional=bool(resource.provisional),
            hardware_notes=resource.hardware_notes or "",
        )


class IncidentAnalyzeIn(BaseModel):
    description: str = Field(min_length=8, max_length=4000)
    space_id: str | None = None
    resource_id: str | None = None


class IncidentAnalysis(BaseModel):
    category: str
    priority: str
    responsible_area: str
    recommendation: str
    rationale: str
    source: str
    ref_core: str = REF_CORE
    priority_raised_by_policy: bool = False
    ai_configured: bool
    provider: str


class IncidentCreate(BaseModel):
    description: str = Field(min_length=8, max_length=4000)
    title: str | None = Field(default=None, max_length=200)
    category: str
    priority: str
    responsible_area: str
    recommendation: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=2000)
    source: str
    priority_raised_by_policy: bool = False
    corrected: bool = False
    space_id: str | None = None
    resource_id: str | None = None

    def validate_enums(self) -> None:
        from app.services.errors import DomainError

        if self.category not in INCIDENT_CATEGORIES:
            raise DomainError(
                "La categoría no es válida. Use: " + ", ".join(INCIDENT_CATEGORIES) + ".",
                422,
            )
        if self.priority not in INCIDENT_PRIORITIES:
            raise DomainError(
                "La prioridad no es válida. Use: " + ", ".join(INCIDENT_PRIORITIES) + ".",
                422,
            )
        if self.responsible_area not in INCIDENT_AREAS:
            raise DomainError(
                "El área responsable no es válida. Use: " + ", ".join(INCIDENT_AREAS) + ".",
                422,
            )
        if self.source not in INCIDENT_SOURCES:
            raise DomainError(
                "El origen no es válido. Use: " + ", ".join(INCIDENT_SOURCES) + ".",
                422,
            )


class IncidentPatch(BaseModel):
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    responsible_area: str | None = None


class IncidentEventOut(BaseModel):
    id: int
    field: str
    old_value: str
    new_value: str
    created_at: datetime

    @classmethod
    def from_model(cls, event: IncidentEvent) -> "IncidentEventOut":
        return cls(
            id=event.id,
            field=event.field,
            old_value=event.old_value,
            new_value=event.new_value,
            created_at=event.created_at,
        )


class IncidentOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    priority: str
    responsible_area: str
    recommendation: str
    rationale: str
    status: str
    source: str
    ref_core: str
    priority_raised_by_policy: bool
    corrected: bool
    space_id: str | None
    resource_id: str | None
    created_at: datetime
    updated_at: datetime
    events: list[IncidentEventOut] | None = None

    @classmethod
    def from_model(cls, incident: Incident, include_events: bool = False) -> "IncidentOut":
        events = None
        if include_events:
            events = [IncidentEventOut.from_model(event) for event in incident.events]
        return cls(
            id=incident.id,
            title=incident.title,
            description=incident.description,
            category=incident.category,
            priority=incident.priority,
            responsible_area=incident.responsible_area,
            recommendation=incident.recommendation,
            rationale=incident.rationale,
            status=incident.status,
            source=incident.source,
            ref_core=incident.ref_core,
            priority_raised_by_policy=incident.priority_raised_by_policy,
            corrected=incident.corrected,
            space_id=incident.space_id,
            resource_id=incident.resource_id,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            events=events,
        )


class ImportIssue(BaseModel):
    entity: str
    row: int
    identifier: str | None = None
    reason: str


class ImportReportOut(BaseModel):
    id: int | None = None
    source_name: str
    accepted: int
    rejected: int
    skipped_duplicates: int
    synthetic: bool = False
    issues: list[ImportIssue]
    notices: list[str] = []
    created_at: datetime | None = None


class IntegrityCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class IntegrityReport(BaseModel):
    sync_v26_node: bool
    audit_threshold_factor: float
    checks: list[IntegrityCheck]
    all_passed: bool
    pressure_ratio: float | None
    pressure_above_threshold: bool
    threshold_meaning: str


class ActivityItem(BaseModel):
    kind: str
    label: str
    at: datetime


class ComputerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    space_id: str = Field(min_length=1, max_length=64)
    asset_code: str = Field(default="", max_length=80)
    notes: str = ""
    hardware_notes: str = ""
    provisional: bool = False


class ComputerPatch(BaseModel):
    name: str | None = None
    notes: str | None = None
    hardware_notes: str | None = None
    asset_code: str | None = None


class StatusChange(BaseModel):
    status: str
    note: str = ""


class LocationChange(BaseModel):
    space_id: str


class PeripheralCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    peripheral_type: str
    host_resource_id: str | None = None
    space_id: str | None = None
    asset_code: str = ""
    notes: str = ""
    brand: str = ""
    model_name: str = ""


class PeripheralHostChange(BaseModel):
    host_resource_id: str | None = None


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=200)
    role: str = "operator"
    notes: str = ""
    active: bool = True


class UserPatch(BaseModel):
    full_name: str | None = None
    username: str | None = None
    password: str | None = None
    role: str | None = None
    notes: str | None = None
    active: bool | None = None


class UserOut(BaseModel):
    id: str
    full_name: str
    username: str
    role: str
    active: bool
    notes: str
    created_at: datetime
    updated_at: datetime


class DashboardOut(BaseModel):
    spaces_total: int
    spaces_available: int
    active_reservations: int
    resources_total: int
    resources_available: int
    active_loans: int
    open_incidents: int
    incidents_by_priority: dict[str, int]
    synthetic_data_present: bool
    sync_v26_node: bool
    ai_configured: bool
    computers_total: int = 0
    computers_available: int = 0
    computers_loaned: int = 0
    computers_unavailable: int = 0
    peripherals_registered: int = 0
    recent_activity: list[ActivityItem] = []
