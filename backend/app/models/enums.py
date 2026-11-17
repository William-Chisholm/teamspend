import enum


class Role(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    APPROVER = "approver"
    MEMBER = "member"


class ExpenseStatus(enum.StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"
