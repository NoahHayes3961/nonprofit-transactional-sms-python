from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .alert_service import AlertRequest, DeliveryResult, deliver_alert
from .infrai_sms import InfraiError, InfraiSmsClient


app = FastAPI(title="Nonprofit transactional SMS")


@app.post("/alerts", response_model=DeliveryResult)
def send_alert(alert: AlertRequest) -> DeliveryResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    try:
        return deliver_alert(alert, InfraiSmsClient(api_key))
    except InfraiError as exc:
        if 400 <= exc.status_code < 500 and exc.status_code != 429:
            status = exc.status_code
        elif exc.status_code == 429:
            status = 503
        else:
            status = 502
        raise HTTPException(status_code=status, detail={"code": exc.code}) from exc
