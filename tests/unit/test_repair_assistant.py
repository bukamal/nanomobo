from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from nanomobo.core.device_db import DeviceMode
from nanomobo.core.device_intelligence import ConfidenceBand, analyze_device
from nanomobo.core.repair_assistant import (
    RISK_LABELS,
    SYMPTOMS,
    PlanStep,
    RepairPlan,
    RiskLevel,
    StepKind,
    Symptom,
    _report_text,
    _risk_for,
    _steps_for,
    _symptom_label,
    _warnings_for,
    create_repair_plan,
)
from nanomobo.core.usb_bridge import Interface, UsbDeviceInfo
from nanomobo.protocols.base import ProbeStatus, ProtocolProbe


def make_device(
    vendor_id: int = 0x05C6,
    product_id: int = 0x9008,
    interfaces: list[tuple[int, int, int]] | None = None,
) -> UsbDeviceInfo:
    return UsbDeviceInfo(
        device_name="1/1",
        vendor_id=vendor_id,
        product_id=product_id,
        device_class=0xFF,
        product="EDL Device",
        interfaces=[],
    )


def make_probe(status: ProbeStatus) -> ProtocolProbe:
    return ProtocolProbe(
        mode=DeviceMode.QUALCOMM_EDL,
        status=status,
        label="probe",
        detail="detail",
        interface_indexes=(0,),
        bulk_endpoint_count=2,
    )


def test_symptoms_table_covers_all_enum_members() -> None:
    assert {symptom for symptom, _label in SYMPTOMS} == set(Symptom)
    assert all(label.strip() for _symptom, label in SYMPTOMS)


def test_every_symptom_produces_a_read_only_plan() -> None:
    device = make_device()
    for symptom in Symptom:
        plan = create_repair_plan(device, symptom)
        assert plan.read_only is True
        assert plan.writes_locked is True
        assert plan.safe is True
        assert plan.steps
        assert plan.warnings
        assert plan.warnings[0].startswith("الخطة قراءة فقط")
        assert "قراءة فقط" in plan.summary


def test_low_confidence_device_raises_risk_at_least_moderate() -> None:
    device = make_device(0x1234, 0xABCD)  # unknown vendor/product, no interfaces
    report = analyze_device(device)
    assert report.band is ConfidenceBand.LOW
    plan = create_repair_plan(device, Symptom.USB_NOT_DETECTED)
    assert plan.risk in {RiskLevel.MODERATE, RiskLevel.ELEVATED}


def test_critical_symptom_on_unknown_mode_is_elevated() -> None:
    device = make_device(0x1234, 0xABCD)
    report = analyze_device(device)
    assert report.mode is DeviceMode.UNKNOWN
    risk = _risk_for(report, Symptom.DEVICE_NOT_BOOTING, None)
    assert risk is RiskLevel.ELEVATED


def test_unrecognized_probe_lifts_risk() -> None:
    device = make_device(0x05C6, 0x9008)
    report = analyze_device(device)
    base = _risk_for(report, Symptom.STUCK_ON_LOGO, None)
    with_probe = _risk_for(report, Symptom.STUCK_ON_LOGO, make_probe(ProbeStatus.UNRECOGNIZED))
    assert base is RiskLevel.LOW
    assert with_probe is RiskLevel.MODERATE


def test_plan_steps_include_protocol_inspection_and_documentation() -> None:
    device = make_device()
    plan = create_repair_plan(device, Symptom.INVALID_IDENTITY)
    titles = [step.title for step in plan.steps]
    assert any("البروتوكول" in title for title in titles)
    assert any("وثّق" in title for title in titles)
    kinds = {step.kind for step in plan.steps}
    assert StepKind.CHECK in kinds
    assert StepKind.SAFE in kinds


def test_report_text_contains_sections_and_safety_line() -> None:
    device = make_device()
    plan = create_repair_plan(device, Symptom.DEVICE_NOT_BOOTING)
    text = plan.report_text
    assert text.startswith("NanoMobo Repair Assistant")
    assert "Device: EDL Device" in text
    assert "Safety: read-only" in text
    assert "Steps:" in text
    assert "Warnings:" in text


def test_report_text_handles_missing_probe() -> None:
    device = make_device()
    report = analyze_device(device)
    plan = RepairPlan(
        symptom=Symptom.STUCK_ON_LOGO,
        device_name=device.device_name,
        id_label=device.id_label,
        mode_label="Qualcomm EDL 9008",
        confidence=90,
        risk=RiskLevel.LOW,
        summary="s",
        steps=(),
        warnings=(),
        report_text="",
    )
    text = _report_text(device, report, None, plan)
    assert "Protocol: Not inspected" in text


def test_symptom_label_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unsupported symptom"):
        _symptom_label("not-a-symptom")  # type: ignore[arg-type]


def test_warnings_flag_mass_storage_and_unrecognized_probe() -> None:
    device = UsbDeviceInfo(
        device_name="1/1",
        vendor_id=0x1234,
        product_id=0x5678,
        device_class=0x00,
        interfaces=[Interface(0, 0x08, 0x06, 0x50)],
    )
    report = analyze_device(device)
    warnings = _warnings_for(
        report,
        Symptom.USB_NOT_DETECTED,
        make_probe(ProbeStatus.UNRECOGNIZED),
        RiskLevel.MODERATE,
    )
    assert any("وضع التخزين" in warning for warning in warnings)
    assert any("غير موثق" in warning for warning in warnings)


def test_steps_embed_probe_detail_when_available() -> None:
    device = make_device()
    report = analyze_device(device)
    steps = _steps_for(device, Symptom.STUCK_ON_LOGO, report, make_probe(ProbeStatus.RECOGNIZED))
    assert any("detail" in step.detail for step in steps)


def test_risk_labels_are_complete() -> None:
    assert set(RISK_LABELS) == set(RiskLevel)
    assert all(label.strip() for label in RISK_LABELS.values())


def test_plan_step_is_frozen_dataclass() -> None:
    step = PlanStep("t", "d", StepKind.SAFE)
    with pytest.raises(FrozenInstanceError):
        step.title = "other"  # type: ignore[misc]
