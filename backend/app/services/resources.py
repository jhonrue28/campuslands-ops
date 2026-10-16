import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Loan, Resource, ResourceEvent
from app.schemas.campus import LoanCreate, LoanOut
from app.services.errors import DomainError
from app.services.spaces import new_id, utcnow
from app.validators.audit import reject_audit_markers

_write_lock = threading.Lock()


def list_resources(db: Session) -> list[Resource]:
    return list(db.scalars(select(Resource).order_by(Resource.name)))


def get_resource(db: Session, resource_id: str) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise DomainError("El recurso no existe.", 404)
    return resource


def list_loans(db: Session, status: str | None = None) -> list[LoanOut]:
    statement = select(Loan, Resource.name).join(Resource, Resource.id == Loan.resource_id)
    if status:
        statement = statement.where(Loan.status == status)
    statement = statement.order_by(Loan.loaned_at.desc())
    rows = db.execute(statement).all()
    return [LoanOut.from_model(loan, resource_name) for loan, resource_name in rows]


def create_loan(db: Session, payload: LoanCreate) -> Loan:
    reject_audit_markers(
        payload.resource_id,
        payload.borrower_name,
        payload.borrower_contact,
        payload.purpose,
    )
    with _write_lock:
        resource = db.get(Resource, payload.resource_id)
        if resource is None:
            raise DomainError("El recurso no existe.", 404)
        existing = db.scalar(
            select(Loan).where(Loan.resource_id == resource.id, Loan.status == "active")
        )
        if resource.status == "loaned" or existing is not None:
            loan_id = existing.id if existing is not None else "sin identificador"
            raise DomainError(
                f"El recurso ya tiene un préstamo activo ({loan_id}). Devuélvalo antes de prestarlo de nuevo.",
                409,
            )
        if resource.status != "available":
            raise DomainError(
                f"No se puede prestar el recurso porque su estado es '{resource.status}'.",
                409,
            )
        loan = Loan(
            id=new_id(),
            resource_id=resource.id,
            borrower_name=payload.borrower_name.strip(),
            borrower_contact=payload.borrower_contact.strip(),
            purpose=payload.purpose.strip(),
            status="active",
            loaned_at=utcnow(),
            due_at=payload.due_at,
            returned_at=None,
        )
        previous = resource.status
        resource.status = "loaned"
        db.add(loan)
        db.add(
            ResourceEvent(
                resource_id=resource.id,
                field="status",
                old_value=previous,
                new_value="loaned",
                created_at=utcnow(),
            )
        )
        db.commit()
        db.refresh(loan)
        return loan


def return_loan(db: Session, loan_id: str) -> Loan:
    with _write_lock:
        loan = db.get(Loan, loan_id)
        if loan is None:
            raise DomainError("El préstamo no existe.", 404)
        if loan.status == "returned":
            raise DomainError("Este préstamo ya fue devuelto.", 409)
        resource = db.get(Resource, loan.resource_id)
        if resource is None:
            raise DomainError("El recurso asociado al préstamo no existe.", 409)
        loan.status = "returned"
        loan.returned_at = utcnow()
        if resource.status == "loaned":
            resource.status = "available"
            db.add(
                ResourceEvent(
                    resource_id=resource.id,
                    field="status",
                    old_value="loaned",
                    new_value="available",
                    created_at=loan.returned_at,
                )
            )
        db.commit()
        db.refresh(loan)
        return loan
