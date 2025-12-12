# Bind to host:port
import logging

bind = "0.0.0.0:8010"

# Number of worker processes
workers = 5

# Request timeout in seconds
timeout = 120

# Capture stdout/stderr from workers
capture_output = True

# Access and error logs to stdout
accesslog = "-"
errorlog = "-"

access_log_format = (
    "%(t)s " "[pid=%(p)s] " "[user=- sess=%({trace_id}o)s] " "[%(h)s] " "%(r)s %(s)s %(b)s %(L)s %(f)s %(a)s"
)


class ELBHealthCheckFilter(logging.Filter):
    """
    Filter out access logs for ELB health checks with HTTP 200.
    """

    def filter(self, record):
        msg = record.getMessage()
        # Filter out successful health check requests. There are so many
        # entries filling the logs otherwise.
        if "ELB-HealthChecker" in msg and " 200 " in msg:
            return False
        return True


def on_starting(server):
    """Attach the filter when Gunicorn starts"""
    gunicorn_access_logger = logging.getLogger("gunicorn.access")
    gunicorn_access_logger.addFilter(ELBHealthCheckFilter())
