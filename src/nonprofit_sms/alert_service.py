from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Protocol


class AlertModel:
    def model_dump(self) -> dict[str, object]:
        return asdict(self)  # type: ignore[arg-type]


def _require_text(**values: str) -> None:
    for name, value in values.items():
        if not value:
            raise ValueError(f"{name} must not be empty")


@dataclass
class DonorReceipt(AlertModel):
    kind: Literal["donor_receipt"]
    event_id: str
    to: str
    donor_name: str
    amount_cents: int
    campaign_name: str
    donation_confirmed: bool

    def __post_init__(self) -> None:
        if self.kind != "donor_receipt":
            raise ValueError("kind must be donor_receipt")
        _require_text(
            event_id=self.event_id,
            to=self.to,
            donor_name=self.donor_name,
            campaign_name=self.campaign_name,
        )
        if self.amount_cents <= 0:
            raise ValueError("amount_cents must be greater than zero")


@dataclass
class VolunteerReminder(AlertModel):
    kind: Literal["volunteer_reminder"]
    event_id: str
    to: str
    volunteer_name: str
    shift_name: str
    starts_at: str

    def __post_init__(self) -> None:
        if self.kind != "volunteer_reminder":
            raise ValueError("kind must be volunteer_reminder")
        _require_text(
            event_id=self.event_id,
            to=self.to,
            volunteer_name=self.volunteer_name,
            shift_name=self.shift_name,
            starts_at=self.starts_at,
        )


@dataclass
class CampaignReport(AlertModel):
    kind: Literal["campaign_report"]
    event_id: str
    to: str
    campaign_name: str
    donor_count: int
    amount_cents: int

    def __post_init__(self) -> None:
        if self.kind != "campaign_report":
            raise ValueError("kind must be campaign_report")
        _require_text(event_id=self.event_id, to=self.to, campaign_name=self.campaign_name)
        if self.donor_count < 0:
            raise ValueError("donor_count must be non-negative")
        if self.amount_cents < 0:
            raise ValueError("amount_cents must be non-negative")


AlertRequest = DonorReceipt | VolunteerReminder | CampaignReport


@dataclass
class DeliveryResult(AlertModel):
    outcome: Literal["sent", "skipped"]
    message_id: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.outcome not in ("sent", "skipped"):
            raise ValueError("outcome must be sent or skipped")


class SmsSender(Protocol):
    def send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, object]:
        """Send one transactional text and return its delivery data."""


def deliver_alert(alert: DonorReceipt | VolunteerReminder | CampaignReport, sender: SmsSender) -> DeliveryResult:
    if isinstance(alert, DonorReceipt):
        if not alert.donation_confirmed:
            return DeliveryResult(outcome="skipped", reason="donation_not_confirmed")
        amount = alert.amount_cents / 100
        body = (
            f"Hi {alert.donor_name}, we received your ${amount:.2f} donation to "
            f"{alert.campaign_name}. Thank you for helping."
        )
    elif isinstance(alert, VolunteerReminder):
        body = (
            f"Hi {alert.volunteer_name}, reminder: your {alert.shift_name} volunteer shift "
            f"starts {alert.starts_at}."
        )
    else:
        amount = alert.amount_cents / 100
        body = (
            f"{alert.campaign_name} report: {alert.donor_count} donors contributed "
            f"${amount:.2f}."
        )

    data = sender.send(to=alert.to, body=body, idempotency_key=f"nonprofit-alert:{alert.event_id}")
    return DeliveryResult(outcome="sent", message_id=str(data["message_id"]))
