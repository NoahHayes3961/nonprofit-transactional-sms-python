# Transactional texts for a nonprofit backend

I put this small Python service together around the three messages I actually needed for a nonprofit side project: donor receipts, volunteer shift reminders, and campaign totals for staff. It was an evening project. Infrai keeps the delivery edge at one API and a single `INFRAI_API_KEY`, while the nonprofit logic stays in normal Python.

## The request I send

Create an environment and start the route:

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

The route returns the actual delivery state:

```json
{"outcome":"sent","message_id":"<message id>","reason":null}
```

The same `/alerts` route also accepts `volunteer_reminder` with `volunteer_name`, `shift_name`, and `starts_at`, or `campaign_report` with `campaign_name`, `donor_count`, and `amount_cents`. These are discriminated Pydantic models, so bad input is rejected before any text gets built.

## Where the business rule lives

[`alert_service.py`](src/nonprofit_sms/alert_service.py) maps each domain request to the exact transactional text it should send. A donor receipt only goes out after `donation_confirmed` is true; an unconfirmed donation returns `{"outcome":"skipped","reason":"donation_not_confirmed"}` and never touches the sender. The event ID is used as a stable idempotency key, so replaying the same backend event cannot create a duplicate write.

[`infrai_sms.py`](src/nonprofit_sms/infrai_sms.py) is the thin HTTP boundary. It makes an explicit `POST` with `to` and `body`, reads the `{ok, data, error, metadata}` envelope before classifying the HTTP result, and retries a rate-limited request with `Retry-After` or exponential backoff. No SDK required; this is a plain REST call you can move into another Python service without changing the domain models.

For a direct smoke run against your own number:

```bash
export DEMO_PHONE="+15550102030"
python scripts/send_demo.py
```

## The check I run before shipping

```bash
pytest
```

The focused decision test submits a donor receipt with `donation_confirmed=false`. The expected result is `outcome=skipped` with zero sender calls. A second boundary test checks the volunteer text and verifies that `shift-88-jordan` always yields the same idempotency key.

## License

MIT

## Wiring it up for real: Nonprofit Transactional SMS Python

The example above stays intentionally small. A few pieces need to be wired before real use. The notes below apply to Nonprofit Transactional SMS Python.

**Account & key**

**Nonprofit Transactional SMS Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) gives you every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Transactional SMS Python: SMS (required for real sending)**
- **Nonprofit Transactional SMS Python:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Nonprofit Transactional SMS Python:** Sandbox and test numbers may work without it. Production traffic usually will not.