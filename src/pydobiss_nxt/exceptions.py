"""Exception hierarchy for pydobiss-nxt.

Every error raised by this library derives from :class:`DobissError`,
so callers can catch a single base class — or narrow down to the
specific failure mode they care about.
"""


class DobissError(Exception):
    """Base class for all pydobiss-nxt errors."""


class DobissConnectionError(DobissError):
    """The NXT server could not be reached.

    Network-level failures: DNS, refused connection, timeout, TLS.
    Transient by nature — the caller may retry later.
    """


class DobissAuthError(DobissError):
    """Authentication with the NXT server failed.

    Wrong credentials or a rejected/expired token that could not be
    refreshed. Not transient — retrying with the same credentials
    will fail again; the user must re-authenticate.
    """


class DobissApiError(DobissError):
    """The NXT server replied, but with an unexpected error.

    HTTP 5xx, malformed JSON, or a payload that does not match the
    documented schema.

    :param message: human-readable description of the failure.
    :param status: HTTP status code, if the failure is tied to a response.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
