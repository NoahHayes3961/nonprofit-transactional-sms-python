from nonprofit_sms.alert_service import DonorReceipt, VolunteerReminder, deliver_alert


class RecordingSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, object]:
        self.calls.append({"to": to, "body": body, "idempotency_key": idempotency_key})
        return {"message_id": "msg_test_42"}


def test_unconfirmed_donation_is_not_sent() -> None:
    sender = RecordingSender()
    alert = DonorReceipt(
        kind="donor_receipt",
        event_id="donation-17",
        to="+15550102030",
        donor_name="Maya",
        amount_cents=2500,
        campaign_name="Community Pantry",
        donation_confirmed=False,
    )

    result = deliver_alert(alert, sender)

    assert result.model_dump() == {
        "outcome": "skipped",
        "message_id": None,
        "reason": "donation_not_confirmed",
    }
    assert sender.calls == []


def test_volunteer_reminder_has_stable_delivery_boundary() -> None:
    sender = RecordingSender()
    alert = VolunteerReminder(
        kind="volunteer_reminder",
        event_id="shift-88-jordan",
        to="+15550102031",
        volunteer_name="Jordan",
        shift_name="food packing",
        starts_at="Saturday at 09:00",
    )

    result = deliver_alert(alert, sender)

    assert result.message_id == "msg_test_42"
    assert sender.calls == [{
        "to": "+15550102031",
        "body": "Hi Jordan, reminder: your food packing volunteer shift starts Saturday at 09:00.",
        "idempotency_key": "nonprofit-alert:shift-88-jordan",
    }]
