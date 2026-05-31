import base64
import json
import os
from datetime import datetime, timezone
from typing import Any

import functions_framework
import requests


@functions_framework.cloud_event
def forward_to_loki(cloud_event) -> None:
    """Cloud Logging のログエントリを Grafana Cloud Loki に転送する。

    Pub/Sub push トリガーで起動し、base64 エンコードされた
    Cloud Logging log entry を受け取って Loki push API に送信する。
    """
    raw = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    log_entry = json.loads(raw)

    timestamp_ns = _parse_timestamp_ns(log_entry.get("timestamp"))
    labels = _build_labels(log_entry)
    line = json.dumps(log_entry, ensure_ascii=False)

    _push_to_loki(timestamp_ns, labels, line)


def _parse_timestamp_ns(timestamp_str: str | None) -> str:
    if timestamp_str:
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return str(int(dt.timestamp() * 1_000_000_000))
        except ValueError:
            pass
    return str(int(datetime.now(timezone.utc).timestamp() * 1_000_000_000))


def _build_labels(log_entry: dict) -> dict[str, str]:
    resource = log_entry.get("resource", {})
    resource_labels = resource.get("labels", {})
    resource_type = resource.get("type", "unknown")

    # Cloud Run Service と Job でサービス名のラベルキーが異なる
    service_name = resource_labels.get(
        "service_name",
        resource_labels.get("job_name", "unknown"),
    )

    return {
        "env": os.environ.get("ENVIRONMENT", "prod"),
        "resource_type": resource_type,
        "service_name": service_name,
        "severity": log_entry.get("severity", "DEFAULT"),
        "project_id": resource_labels.get("project_id", ""),
    }


def _push_to_loki(timestamp_ns: str, labels: dict[str, str], line: str) -> None:
    loki_url = os.environ["LOKI_URL"].rstrip("/")
    loki_username = os.environ["LOKI_USERNAME"]
    loki_password = os.environ["LOKI_PASSWORD"]

    payload: Any = {
        "streams": [
            {
                "stream": labels,
                "values": [[timestamp_ns, line]],
            }
        ]
    }

    resp = requests.post(
        f"{loki_url}/loki/api/v1/push",
        json=payload,  # type: ignore[arg-type]
        auth=(loki_username, loki_password),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
