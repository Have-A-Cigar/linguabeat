"""Landing pages router — SSR with Jinja2."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)

_APP_URL = "https://linguabeat.ru/app"


def _ctx(request: Request, **extra: object) -> dict:
    return {"request": request, "app_url": _APP_URL, **extra}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", _ctx(request))


@router.get("/method", response_class=HTMLResponse)
async def method(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("method.html", _ctx(request))


@router.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("pricing.html", _ctx(request))


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /app/\n"
        "\n"
        "Sitemap: https://linguabeat.ru/sitemap.xml\n"
    )


@router.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap() -> HTMLResponse:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://linguabeat.ru/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://linguabeat.ru/method</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://linguabeat.ru/pricing</loc>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>"""
    return HTMLResponse(content=xml, media_type="application/xml")
