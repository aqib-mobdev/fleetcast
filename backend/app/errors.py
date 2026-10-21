class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 502, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.field = field


class PlaceNotFound(DomainError):
    def __init__(self, field: str, query: str):
        super().__init__(
            "place_not_found",
            f"No location matched '{query}'.",
            status=422,
            field=field,
        )


class NoRoute(DomainError):
    def __init__(self, detail: str):
        super().__init__("no_route", f"No drivable route found: {detail}", status=422)


class UpstreamError(DomainError):
    pass


class TripExpired(DomainError):
    def __init__(self):
        super().__init__("trip_expired", "Trip not found or expired. Run the analysis again.", status=404)
