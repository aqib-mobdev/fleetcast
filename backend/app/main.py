import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import DomainError
from app.models import AnalyzeBody, CorridorBody
from app.providers import geocode
from app.services import analysis, corridor

log = logging.getLogger("fleetcast")

app = FastAPI(title="FleetCast API", version="1.0.0", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings().cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": exc.code, "message": exc.message, "field": exc.field}},
        status_code=exc.status,
    )


@app.exception_handler(RequestValidationError)
async def body_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", [])[1:]) or None
    message = first.get("msg", "Invalid request body.")
    return JSONResponse(
        {"error": {"code": "invalid_body", "message": message, "field": field}},
        status_code=422,
    )


@app.exception_handler(Exception)
async def unexpected(_: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        {"error": {"code": "internal_error", "message": "Unexpected server error.", "field": None}},
        status_code=500,
    )


@app.get("/api/health")
async def health() -> dict:
    cfg = settings()
    return {
        "service": "fleetcast",
        "version": "1.0.0",
        "providers": {
            "openrouteservice": bool(cfg.ors_api_key),
            "osrm": cfg.osrm_base_url,
            "open_meteo": cfg.open_meteo_base_url,
            "nominatim": cfg.nominatim_base_url,
        },
        "clock": datetime.now(UTC).isoformat(),
    }


@app.get("/api/places")
async def places(q: str = Query(default="", max_length=200)) -> dict:
    matches = await geocode.suggest(q)
    return {
        "query": q,
        "places": [{"label": m.label, "lat": m.lat, "lon": m.lon} for m in matches],
    }


@app.post("/api/trips/analyze")
async def analyze_trip(body: AnalyzeBody) -> dict:
    return await analysis.analyze(body)


@app.post("/api/trips/corridor")
async def trip_corridor(body: CorridorBody) -> dict:
    return await corridor.build([tuple(point) for point in body.path], body.load_lbs, body.route)


@app.get("/")
async def root() -> dict:
    return {"service": "fleetcast", "docs": "/api/docs", "health": "/api/health"}
