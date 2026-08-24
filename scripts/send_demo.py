import os

from nonprofit_sms.alert_service import DonorReceipt, deliver_alert
from nonprofit_sms.infrai_sms import InfraiSmsClient


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    phone = os.environ.get("DEMO_PHONE")
    if not api_key or not phone:
        raise SystemExit("Set INFRAI_API_KEY and DEMO_PHONE")

    receipt = DonorReceipt(
        kind="donor_receipt",
        event_id="demo-donation-1042",
        to=phone,
        donor_name="Maya",
        amount_cents=2500,
        campaign_name="Community Pantry",
        donation_confirmed=True,
    )
    print(deliver_alert(receipt, InfraiSmsClient(api_key)).model_dump())


if __name__ == "__main__":
    main()
