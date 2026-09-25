from __future__ import annotations

from nanomobo.core.identity_audit import (
    AuditSeverity,
    AuditStatus,
    OwnershipStatus,
    audit_identity,
    create_backup,
    plan_restore,
)

VALID_IMEI = "490154203237518"
OTHER_VALID_IMEI = "490154203237526"


def test_valid_imei_without_original_is_clean_but_unverified() -> None:
    audit = audit_identity(VALID_IMEI)

    assert audit.status is AuditStatus.CLEAN
    assert audit.ownership is OwnershipStatus.UNVERIFIED
    assert audit.read_only is True
    assert audit.writes_locked is True
    assert audit.needs_attention is False
    assert any(finding.title == "الملكية" for finding in audit.findings)


def test_mismatch_against_original_is_flagged_as_tampered() -> None:
    audit = audit_identity(VALID_IMEI, OTHER_VALID_IMEI)

    assert audit.status is AuditStatus.TAMPERED
    assert audit.needs_attention is True
    critical = [f for f in audit.findings if f.severity is AuditSeverity.CRITICAL]
    assert critical


def test_matching_value_is_clean() -> None:
    audit = audit_identity(VALID_IMEI, VALID_IMEI)

    assert audit.status is AuditStatus.CLEAN
    assert any("مطابقة" in finding.detail for finding in audit.findings)


def test_invalid_format_is_reported() -> None:
    audit = audit_identity("12345")

    assert audit.status is AuditStatus.INVALID
    assert audit.needs_attention is True


def test_empty_value_is_incomplete() -> None:
    audit = audit_identity("")

    assert audit.status is AuditStatus.INCOMPLETE
    assert audit.current == ""


def test_owner_verified_changes_finding_severity() -> None:
    audit = audit_identity(VALID_IMEI, owner_verified=True)

    ownership_findings = [f for f in audit.findings if f.title == "الملكية"]
    assert ownership_findings
    assert ownership_findings[0].severity is AuditSeverity.INFO
    assert audit.ownership is OwnershipStatus.VERIFIED


def test_create_backup_normalizes_values() -> None:
    backup = create_backup(
        "device-1",
        "49 015420 323751 8",
        "a0000012345678",
        owner_verified=True,
    )

    assert backup.primary == VALID_IMEI
    assert backup.secondary == "A0000012345678"
    assert backup.owner_verified is True
    assert backup.read_only is True


def test_restore_plan_is_always_blocked_without_owner_proof() -> None:
    backup = create_backup("device-1", VALID_IMEI, owner_verified=False)

    plan = plan_restore(backup, owner_verified=False)

    assert plan.blocked is True
    assert plan.owner_verified is False
    assert plan.writes_locked is True
    assert any("ملكية" in warning for warning in plan.warnings)
    assert "official tool" in plan.report_text or "أداة رسمية" in plan.report_text


def test_restore_plan_still_blocks_device_writes_when_owner_verified() -> None:
    backup = create_backup("device-1", VALID_IMEI, owner_verified=True)

    plan = plan_restore(backup, owner_verified=True)

    assert plan.owner_verified is True
    assert plan.blocked is True
    assert "أداة رسمية" in plan.reason
    assert any("لا يكتب" in warning for warning in plan.warnings)


def test_restore_plan_without_backup_value_is_blocked() -> None:
    backup = create_backup("device-1", "", owner_verified=True)

    plan = plan_restore(backup, owner_verified=True)

    assert plan.blocked is True
    assert plan.target == ""


def test_audit_report_contains_safety_line() -> None:
    audit = audit_identity(VALID_IMEI, OTHER_VALID_IMEI)

    assert audit.report_text.startswith("NanoMobo Identity Audit")
    assert "Safety: read-only" in audit.report_text
    assert "Findings:" in audit.report_text
