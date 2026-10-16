from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    features_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="imported")
    room_type: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    expected_computers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="space")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False, index=True)
    requester_name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    attendees: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    space: Mapped[Space] = relationship(back_populates="reservations")


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    serial_number: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="imported")
    asset_code: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="equipment", index=True)
    space_id: Mapped[str | None] = mapped_column(ForeignKey("spaces.id"), nullable=True, index=True)
    host_resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id"), nullable=True, index=True)
    peripheral_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    brand: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    provisional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hardware_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    loans: Mapped[list["Loan"]] = relationship(back_populates="resource")
    events: Mapped[list["ResourceEvent"]] = relationship(back_populates="resource")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), nullable=False, index=True)
    borrower_name: Mapped[str] = mapped_column(String(200), nullable=False)
    borrower_contact: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    purpose: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    loaned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped[Resource] = relationship(back_populates="loans")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    responsible_area: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_core: Mapped[str] = mapped_column(String(32), nullable=False, default="[Ref-Core]")
    priority_raised_by_policy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    space_id: Mapped[str | None] = mapped_column(ForeignKey("spaces.id"), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    events: Mapped[list["IncidentEvent"]] = relationship(back_populates="incident")


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    new_value: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="events")


class ResourceEvent(Base):
    __tablename__ = "resource_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    new_value: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    resource: Mapped[Resource] = relationship(back_populates="events")


class ImportReport(Base):
    __tablename__ = "import_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
