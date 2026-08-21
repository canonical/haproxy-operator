# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy log formats used when log-hash-client-ip is enabled.

Each format mirrors HAProxy's built-in default for its log type, with only the
client IP replaced by a salted SHA-256 hash.
"""

# TODO(ISD-6248): "demo-salt-value" is a placeholder. Replace with a salt
# sourced from a Juju user secret (IS-only access).
LOG_SALT_PLACEHOLDER = "demo-salt-value"
# Salted SHA-256 hash of the source IP.
LOG_HASHED_CLIENT_IP = f'%[src,concat(,,\\"{LOG_SALT_PLACEHOLDER}\\"),sha2(256),hex]'

# Client port.
LOG_CLIENT_PORT = "%cp"
# Hashed client IP and port, replacing the %ci:%cp client address field.
LOG_HASHED_CLIENT_ADDRESS = f"{LOG_HASHED_CLIENT_IP}:{LOG_CLIENT_PORT}"
# Accept date, with millisecond resolution, enclosed in brackets.
LOG_ACCEPT_DATE = "[%tr]"
# Date of the connection, enclosed in brackets.
LOG_DATE = "[%t]"
# Frontend name, and backend/server names.
LOG_PROXY_NAMES = "%ft %b/%s"
# Timers: request / queue-wait / connect / response / active time.
LOG_HTTP_TIMERS = "%TR/%Tw/%Tc/%Tr/%Ta"
# Timers: queue-wait / connect / total time.
LOG_TCP_TIMERS = "%Tw/%Tc/%Tt"
# HTTP status code and bytes read.
LOG_STATUS_AND_BYTES = "%ST %B"
# Bytes read (TCP mode).
LOG_BYTES = "%B"
# Captured request/response cookies and the termination-state cookie.
LOG_COOKIES = "%CC %CS %tsc"
# Termination state.
LOG_TERMINATION_STATE = "%ts"
# Counters: active/frontend/backend/server/retried connections.
LOG_CONNECTION_COUNTERS = "%ac/%fc/%bc/%sc/%rc"
# Queue sizes: queued in the server / in the backend.
LOG_QUEUE_SIZES = "%sq/%bq"
# Captured request and response headers.
LOG_CAPTURED_HEADERS = "%hr %hs"
# The HTTP request line, quoted.
LOG_REQUEST = "%{+Q}r"
# Frontend name and the id of the socket that accepted the connection.
LOG_FRONTEND_AND_SOCKET = "%[fe_name]/%[so_id]"
# The connection error, and the SSL error detail (renders as (-) for non-SSL
# errors because log-format has no conditionals).
LOG_ERROR_DETAIL = "%[fc_err_str] (%[ssl_fc_err_str])"

HTTP_LOG_FORMAT = (
    f"{LOG_HASHED_CLIENT_ADDRESS} {LOG_ACCEPT_DATE} {LOG_PROXY_NAMES} {LOG_HTTP_TIMERS} "
    f"{LOG_STATUS_AND_BYTES} {LOG_COOKIES} {LOG_CONNECTION_COUNTERS} {LOG_QUEUE_SIZES} "
    f"{LOG_CAPTURED_HEADERS} {LOG_REQUEST}"
)
# error-log-format mirrors HAProxy's default error line with a hashed client IP,
# covering pre-stream errors (SSL handshake, PROXY protocol) that bypass log-format.
ERROR_LOG_FORMAT = (
    f"{LOG_HASHED_CLIENT_ADDRESS} {LOG_ACCEPT_DATE} {LOG_FRONTEND_AND_SOCKET}: {LOG_ERROR_DETAIL}"
)
TCP_LOG_FORMAT = (
    f"{LOG_HASHED_CLIENT_ADDRESS} {LOG_DATE} {LOG_PROXY_NAMES} {LOG_TCP_TIMERS} "
    f"{LOG_BYTES} {LOG_TERMINATION_STATE} {LOG_CONNECTION_COUNTERS} {LOG_QUEUE_SIZES}"
)
