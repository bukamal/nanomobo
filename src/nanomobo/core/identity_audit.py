from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nanomobo.core.identity import (
    IdentityKind,
    IdentityMatch,
    IdentityValidation,
    compare_identity,
    validate_identity,
)


class AuditStatus(str, Enum):
    CLEAN = "clean"
    TAMPERED = "tampered"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"


class OwnershipStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    title: str
    detail: str
    severity: AuditSeverity


@dataclass(frozen=True, slots=True)
class IdentityAudit:
    current: str
    original: str
    status: AuditStatus
    ownership: OwnershipStatus
    findings: tuple[AuditFinding, ...]
    report_text: str
    read_only: bool = True
    writes_locked: bool = True

    @property
    def needs_attention(self) -> bool:
        return self.status in {AuditStatus.TAMPERED, AuditStatus.INVALID}


@dataclass(frozen=True, slots=True)
class IdentityBackup:
    device_id: str
    primary: str
    secondary: str
    owner_verified: bool
    read_only: bool = True


@dataclass(frozen=True, slots=True)
class RestorePlan:
    target: str
    owner_verified: bool
    blocked: bool
    reason: str
    steps: tuple[str, ...]
    warnings: tuple[str, ...]
    report_text: str
    writes_locked: bool = True


def audit_identity(
    current: str,
    original: str = "",
    *,
    owner_verified: bool = False,
) -> IdentityAudit:
    current_validation = validate_identity(current)
    original_validation = validate_identity(original)
    ownership = OwnershipStatus.VERIFIED if owner_verified else OwnershipStatus.UNVERIFIED
    findings: list[AuditFinding] = [
        _format_finding("الحالي", current_validation),
    ]
    status = _audit_status(current_validation, original)

    if original.strip():
        findings.append(_format_finding("الأصلي", original_validation))
        comparison = compare_identity(current, original)
        if comparison.result is IdentityMatch.MATCH:
            findings.append(
                AuditFinding(
                    "المقارنة",
                    "القيمة الحالية مطابقة للقيمة الأصلية المخزّنة",
                    AuditSeverity.INFO,
                )
            )
        elif comparison.result is IdentityMatch.MISMATCH:
            findings.append(
                AuditFinding(
                    "المقارنة",
                    "القيمة الحالية مختلفة عن القيمة الأصلية — احتمال تلاعب",
                    AuditSeverity.CRITICAL,
                )
            )
        else:
            findings.append(
                AuditFinding(
                    "المقارنة",
                    "لا يمكن المقارنة: قيمة ناقصة",
                    AuditSeverity.WARNING,
                )
            )
    else:
        findings.append(
            AuditFinding(
                "الأصلي",
                "لا توجد قيمة أصلية مخزّنة للمقارنة",
                AuditSeverity.WARNING,
            )
        )

    findings.append(_ownership_finding(ownership))

    audit = IdentityAudit(
        current=current_validation.value,
        original=original_validation.value,
        status=status,
        ownership=ownership,
        findings=tuple(findings),
        report_text="",
    )
    return IdentityAudit(
        current=audit.current,
        original=audit.original,
        status=audit.status,
        ownership=audit.ownership,
        findings=audit.findings,
        report_text=_audit_report_text(audit),
    )


def create_backup(
    device_id: str,
    primary: str,
    secondary: str = "",
    *,
    owner_verified: bool = False,
) -> IdentityBackup:
    return IdentityBackup(
        device_id=device_id,
        primary=validate_identity(primary).value,
        secondary=validate_identity(secondary).value,
        owner_verified=owner_verified,
    )


def plan_restore(backup: IdentityBackup, *, owner_verified: bool) -> RestorePlan:
    authorized = owner_verified and backup.owner_verified
    if not backup.primary:
        reason = "لا توجد قيمة أصلية مخزّنة للاستعادة"
    elif not authorized:
        reason = "الاستعادة تحتاج إثبات ملكية موثّق"
    else:
        reason = "الاستعادة تتطلب أداة رسمية؛ لا يتم الكتابة من هذا التطبيق"

    steps = (
        "تحقق من ملكية الجهاز ووثّقها",
        "قارن القيمة الحالية بالأصلية المخزّنة",
        "خذ نسخة احتياطية كاملة قبل أي عملية",
        "نفّذ استعادة القيمة الأصلية عبر القناة الرسمية المعتمدة",
        "أعد الفحص وأنشئ تقريرًا نهائيًا",
    )
    warnings: list[str] = [
        "لا يُسمح بكتابة IMEI جديد أو مختلف؛ فقط القيمة الأصلية الموثّقة",
        "هذا التطبيق لا يكتب على الجهاز؛ الاستعادة تُنفَّذ بأداة رسمية",
    ]
    if not authorized:
        warnings.append("إثبات الملكية مفقود أو غير موثّق")

    plan = RestorePlan(
        target=backup.primary,
        owner_verified=authorized,
        blocked=True,
        reason=reason,
        steps=steps,
        warnings=tuple(warnings),
        report_text="",
    )
    return RestorePlan(
        target=plan.target,
        owner_verified=plan.owner_verified,
        blocked=plan.blocked,
        reason=plan.reason,
        steps=plan.steps,
        warnings=plan.warnings,
        report_text=_restore_report_text(backup, plan),
    )


def _audit_status(
    current: IdentityValidation,
    original: str,
) -> AuditStatus:
    if not current.value:
        return AuditStatus.INCOMPLETE
    if not current.valid_format:
        return AuditStatus.INVALID
    if original.strip():
        comparison = compare_identity(current.value, original)
        if comparison.result is IdentityMatch.MISMATCH:
            return AuditStatus.TAMPERED
    return AuditStatus.CLEAN


def _format_finding(label: str, validation: IdentityValidation) -> AuditFinding:
    if validation.kind is IdentityKind.IMEI:
        detail = "IMEI صالح الصيغة" if validation.valid_format else "IMEI غير صالح الصيغة"
    elif validation.kind is IdentityKind.MEID:
        detail = "MEID بطول صالح" if validation.valid_format else "MEID غير صالح"
    else:
        detail = "معرّف غير معروف الطول أو الصيغة"
    return AuditFinding(
        title=label,
        detail=f"{detail} ({validation.value or 'فارغ'})",
        severity=AuditSeverity.INFO,
    )


def _ownership_finding(ownership: OwnershipStatus) -> AuditFinding:
    if ownership is OwnershipStatus.VERIFIED:
        return AuditFinding(
            "الملكية",
            "تم توثيق ملكية الجهاز لهذا الفحص",
            AuditSeverity.INFO,
        )
    return AuditFinding(
        "الملكية",
        "بدون إثبات ملكية؛ لن يُسمح بأي استعادة للقيمة الأصلية",
        AuditSeverity.WARNING,
    )


def status_label(status: AuditStatus) -> str:
    return {
        AuditStatus.CLEAN: "سليم",
        AuditStatus.TAMPERED: "تلاعب محتمل",
        AuditStatus.INVALID: "صيغة غير صالحة",
        AuditStatus.INCOMPLETE: "بيانات ناقصة",
    }[status]


def ownership_label(ownership: OwnershipStatus) -> str:
    return {
        OwnershipStatus.VERIFIED: "موثّقة",
        OwnershipStatus.UNVERIFIED: "غير موثّقة",
    }[ownership]


def _audit_report_text(audit: IdentityAudit) -> str:
    lines = [
        "NanoMobo Identity Audit",
        f"Current: {audit.current or 'N/A'}",
        f"Original: {audit.original or 'N/A'}",
        f"Status: {status_label(audit.status)}",
        f"Ownership: {ownership_label(audit.ownership)}",
        "Findings:",
    ]
    lines.extend(f"- {finding.title}: {finding.detail}" for finding in audit.findings)
    lines.append("Safety: read-only; no IMEI writing from this app.")
    return "\n".join(lines)


def _restore_report_text(backup: IdentityBackup, plan: RestorePlan) -> str:
    lines = [
        "NanoMobo Identity Restore Plan",
        f"Device: {backup.device_id or 'N/A'}",
        f"Original primary: {backup.primary or 'N/A'}",
        f"Owner verified: {'yes' if plan.owner_verified else 'no'}",
        f"Blocked: {'yes' if plan.blocked else 'no'}",
        f"Reason: {plan.reason}",
        "Steps:",
    ]
    lines.extend(f"{index}. {step}" for index, step in enumerate(plan.steps, start=1))
    lines.append("Warnings:")
    lines.extend(f"- {warning}" for warning in plan.warnings)
    lines.append("Safety: restore is executed only by an official tool; this app never writes.")
    return "\n".join(lines)


__all__ = [
    "AuditFinding",
    "AuditSeverity",
    "AuditStatus",
    "IdentityAudit",
    "IdentityBackup",
    "OwnershipStatus",
    "RestorePlan",
    "audit_identity",
    "create_backup",
    "ownership_label",
    "plan_restore",
    "status_label",
]
