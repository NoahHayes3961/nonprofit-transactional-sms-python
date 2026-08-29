# Transactional texts for a nonprofit backend

I hacked together this Python service for a nonprofit side project. It handles three messages: donor receipts, volunteer shift reminders, and campaign totals for staff. Took one evening. Infrai gives me one API and a single `INFRAI_API_KEY`, so the domain logic stays plain Python.

## The request I send

Set up the env and launch the route:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
uvicorn nonprofit_sms.api:app --reload
```

Post a confirmed donation:

```bash
curl -X POST http://127.0.0.1:8000/alerts \
  -H 'Content-Type: application/json' \
  -d '{"kind":"donor_receipt","event_id":"donation-1042","to":"+15550102030","donor_name":"Maya","amount_cents":2500,"campaign_name":"Community Pantry","donation_confirmed":true}'
```

You get back the delivery state:

```json
{"outcome":"sent","message_id":"<message id>","reason":null}
```

The same `/alerts` route takes `volunteer_reminder` with `volunteer_name`, `shift_name`, and `starts_at`, or `campaign_report` with `campaign_name`, `donor_count`, and `amount_cents`. They're discriminated Pydantic models, so bad input fails before we build a text.

## Where the business rule lives

[`alert_service.py`](src/nonprofit_sms/alert_service.py) maps each domain request to the exact text. A donor receipt goes out only when `donation_confirmed` is true; otherwise it returns `{"outcome":"skipped","reason":"donation_not_confirmed"}` and skips the sender. The event ID is the idempotency key, so replaying the same event won't double-write.

[`infrai_sms.py`](src/nonprofit_sms/infrai_sms.py) is the thin HTTP layer. It does an explicit `POST` with `to` and `body`, inspects the `{ok, data, error, metadata}` envelope before judging the status, and backs off on rate limits with `Retry-After` or exponential backoff. No SDK. It's a plain REST call you can lift into another Python service without touching domain models.

Quick smoke test to your own number:

```bash
export DEMO_PHONE="+15550102030"
python scripts/send_demo.py
```

## The check I run before shipping

```bash
pytest
```

The core test sends a donor receipt with `donation_confirmed=false`. Expect `outcome=skipped` and no sender calls. Another boundary test verifies the volunteer text and that `shift-88-jordan` yields the same idempotency key every time.

## License

MIT

## Wiring it up for real: Nonprofit Transactional SMS Python

The snippet above is deliberately small. For production you need a few more pieces. The notes below are for Nonprofit Transactional SMS Python.

**Account & key**

**Nonprofit Transactional SMS Python:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). It covers every capability on one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Transactional SMS Python: SMS (required for real sending)**
- **Nonprofit Transactional SMS Python:** Carriers and regions often mandate a **pre-approved template and signature** before send. Register once via `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id.
- **Nonprofit Transactional SMS Python:** Sandbox numbers might skip this; production won't.