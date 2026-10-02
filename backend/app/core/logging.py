import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.config import settings

# Context variables for distributed request tracing
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)

def get_current_trace_id() -> str:
    tid = trace_id_ctx.get()
    return tid if tid else "no-trace"

def get_current_request_id() -> str:
    rid = request_id_ctx.get()
    return rid if rid else "no-request"

def set_trace_context(trace_id: Optional[str] = None, request_id: Optional[str] = None, user_id: Optional[int] = None) -> tuple[str, str]:
    tid = trace_id or str(uuid.uuid4())
    rid = request_id or str(uuid.uuid4())
    trace_id_ctx.set(tid)
    request_id_ctx.set(rid)
    if user_id is not None:
        user_id_ctx.set(user_id)
    return tid, rid

class JSONFormatter(logging.Formatter):
    """
    Standard CloudWatch / Datadog / ELK compatible JSON log formatter.
    Serializes log records into structured JSON with trace correlation.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", get_current_trace_id()),
            "request_id": getattr(record, "request_id", get_current_request_id()),
        }

        # Include user context if present
        uid = user_id_ctx.get()
        if uid is not None:
            log_data["user_id"] = uid

        # Include custom extra metadata passed to logger
        for key, val in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
                "trace_id", "request_id"
            }:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(val)
                    log_data[key] = val
                except (TypeError, OverflowError):
                    log_data[key] = str(val)

        # Include formatted exception traceback if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

class LocalAPMTracker:
    """
    Lightweight in-memory Application Performance Monitoring (APM) tracker.
    Maintains request latencies, status distributions, and error counters for production telemetry.
    """
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.latencies: List[float] = []
        self.total_requests: int = 0
        self.status_counts: Dict[str, int] = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
        self.recent_errors: List[Dict[str, Any]] = []

    def record_request(self, duration_ms: float, status_code: int, path: str, method: str, trace_id: str):
        self.total_requests += 1
        self.latencies.append(duration_ms)
        if len(self.latencies) > self.max_samples:
            self.latencies.pop(0)

        # Group status
        status_bucket = f"{status_code // 100}xx"
        self.status_counts[status_bucket] = self.status_counts.get(status_bucket, 0) + 1

        if status_code >= 400:
            error_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2)
            }
            self.recent_errors.append(error_entry)
            if len(self.recent_errors) > 50:
                self.recent_errors.pop(0)

    def get_metrics(self) -> Dict[str, Any]:
        if not self.latencies:
            p50 = p95 = p99 = avg = 0.0
        else:
            sorted_lat = sorted(self.latencies)
            n = len(sorted_lat)
            p50 = sorted_lat[int(n * 0.50)]
            p95 = sorted_lat[int(min(n - 1, n * 0.95))]
            p99 = sorted_lat[int(min(n - 1, n * 0.99))]
            avg = sum(sorted_lat) / n

        return {
            "total_requests": self.total_requests,
            "status_distribution": self.status_counts,
            "latency_ms": {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "avg": round(avg, 2)
            },
            "error_rate_pct": round((self.status_counts.get("5xx", 0) / max(1, self.total_requests)) * 100, 2),
            "recent_errors": self.recent_errors[-10:]
        }

apm_tracker = LocalAPMTracker()

def setup_logging():
    """
    Initializes root and ARSA loggers with either JSON or standard formatting.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate lines
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if settings.LOG_FORMAT.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        text_format = "%(asctime)s [%(levelname)s] [%(name)s] [trace=%(trace_id)s] %(message)s"
        class TraceContextTextFormatter(logging.Formatter):
            def format(self, record):
                if not hasattr(record, "trace_id"):
                    record.trace_id = get_current_trace_id()
                return super().format(record)
        handler.setFormatter(TraceContextTextFormatter(text_format))

    root_logger.addHandler(handler)

    # Configure app loggers
    for logger_name in ["arsa", "arsa.api", "arsa.pipeline", "arsa.agent", "arsa.backup"]:
        sub_logger = logging.getLogger(logger_name)
        sub_logger.setLevel(log_level)

def init_apm(app=None):
    """
    Initializes Sentry APM integration if SENTRY_DSN is configured.
    """
    logger = logging.getLogger("arsa.apm")
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                send_default_pii=False
            )
            logger.info(f"Sentry APM initialized in '{settings.ENVIRONMENT}' environment with trace sampling {settings.SENTRY_TRACES_SAMPLE_RATE}")
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry APM: {e}")
    else:
        logger.info("SENTRY_DSN not configured. Local APM telemetry tracker active.")
