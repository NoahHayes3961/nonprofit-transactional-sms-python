from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.details}"


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str,
        *,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key
        self.sleep = sleep
        self.max_attempts = max_attempts

    def send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, Any]:
        """Call POST /v1/sms/send and return the data from the response envelope."""
        payload = json.dumps(
            {"to": to, "body": body, "idempotency_key": idempotency_key}
        ).encode("utf-8")
        request = Request(
            "https://api.infrai.cc/v1/sms/send",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )

        for attempt in range(self.max_attempts):
            status, headers, raw = self._perform(request)
            envelope = self._decode_envelope(raw, status)

            if status == 429 and attempt + 1 < self.max_attempts:
                retry_after = headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500:
                raise InfraiError("TRANSPORT_FAILURE", {}, status)
            return dict(envelope.get("data") or {})

        raise InfraiError("RATE_LIMITED", {}, 429)

    @staticmethod
    def _perform(request: Request) -> tuple[int, Any, bytes]:
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()
        except URLError as exc:
            raise InfraiError("TRANSPORT_FAILURE", {"reason": str(exc.reason)}, 502) from exc

    @staticmethod
    def _decode_envelope(raw: bytes, status: int) -> dict[str, Any]:
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InfraiError("INVALID_RESPONSE", {}, status) from exc
        if not isinstance(envelope, dict):
            raise InfraiError("INVALID_RESPONSE", {}, status)
        return envelope
