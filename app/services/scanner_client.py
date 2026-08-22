from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ScannerClientError(RuntimeError):
    def __init__(self, message: str, status: int = 503):
        super().__init__(message)
        self.status = status


class ScannerClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, payload=None) -> dict:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            try:
                message = json.loads(exc.read()).get("error")
            except Exception:
                message = None
            raise ScannerClientError(message or "The scanner rejected the request.", exc.code) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ScannerClientError("The scanner service is unavailable.") from exc

    def status(self) -> dict:
        return self.request("GET", "/status")

    def action(self, path: str, payload=None) -> dict:
        return self.request("POST", path, payload or {})

