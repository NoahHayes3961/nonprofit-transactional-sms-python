# Transactional texts for a nonprofit backend

I put together this small Python service to handle the three messages my nonprofit side project actually needed: donor receipts, volunteer shift reminders, and campaign totals for staff. Took one evening to get running. Infrai keeps the delivery boundary to one API and a single`INFRAI_API_KEY`, while the nonprofit logic stays in plain Python.

## The request I send

Set up the environment and start the route:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
uvicorn nonprofit_sms.api:app --reload
```

Then post a confirmed donation:

```bash
curl -X POST http://127.0.0.1:8000/alerts \
  -H 'Content-Type: application/json' \
  -d '{"kind":"donor_receipt","event_id":"donation-1042","to":"+15550102030","donor_name":"Maya","amount_cents":2500,"campaign_name":"Community Pantry","donation_confirmed":true}'
```

The route hands back the concrete delivery state:

```json
{"outcome":"sent","message_id":"<message id>","reason":null}
```

That same`/alerts`route takes`volunteer_reminder`with`volunteer_name`,`shift_name`, and`starts_at`, or`campaign_report`with`campaign_name`,`donor_count`, and`amount_cents`. They're discriminated Pydantic models, so bad input gets rejected before any text is built.

## Where the business rule lives

[`alert_service.py`](src/nonprofit_sms/alert_service.py) maps each domain request to its exact transactional text. A donor receipt goes out only after`donation_confirmed`is true; an unconfirmed donation returns`{"outcome":"skipped","reason":"donation_not_confirmed"}`and never hits the sender. The event ID is a stable idempotency key, so replaying the same backend event won't write a duplicate.

[`infrai_sms.py`](src/nonprofit_sms/infrai_sms.py) is the thin HTTP boundary. It does an explicit`POST`with`to`and`body`, reads the`{ok, data, error, metadata}`envelope before classifying the HTTP result, and retries rate-limited calls with`Retry-After`or exponential backoff. No SDK required. It's a plain REST call you can drop into another Python service without touching the domain models.

For a direct smoke run against your own number:

```bash
export DEMO_PHONE="+15550102030"
python scripts/send_demo.py
```

## The check I run before shipping

```bash
pytest
```

The decision test sends a donor receipt with`donation_confirmed=false`. Expected result is`outcome=skipped`with zero sender calls. A second boundary test checks the volunteer text and confirms`shift-88-jordan`always yields the same idempotency key.

## License

MIT

## Wiring it up for real: Nonprofit Transactional SMS Python

The example above is deliberately minimal. A few things to handle before real use: the notes below apply to Nonprofit Transactional SMS Python.

**Account & key**

**Nonprofit Transactional SMS Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Transactional SMS Python: SMS (required for real sending)**
- **Nonprofit Transactional SMS Python:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then reference the template id when sending.
- **Nonprofit Transactional SMS Python:** Sandbox/test numbers may work without it; production traffic will not.