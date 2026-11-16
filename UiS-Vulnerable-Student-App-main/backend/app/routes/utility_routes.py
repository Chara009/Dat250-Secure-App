import ipaddress
import socket
import traceback
from urllib.parse import urlparse

import traceback
import requests
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.auth import get_user_from_session
from app.config import APP_ENV

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ALLOWED_SCHEMES = {"http", "https"}


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 80)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status", response_class=HTMLResponse)
def status(request: Request):
    user = get_user_from_session(request)
    return templates.TemplateResponse(
        "status.html",
        {"request": request, "user": user, "env": APP_ENV, "python": "3.11", "service": "backend"},
    )


@router.get("/resources/import", response_class=HTMLResponse)
def import_resource_get(request: Request, url: str = ""):
    user = get_user_from_session(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    
    body = ""
    error = ""
    if url:
        if not is_safe_url(url):
            error = "This URL is not allowed. Only public http or https addresses can be imported."
        else:
            try:
                r = requests.get(url, timeout=5, allow_redirects=False)
                if r.is_redirect:
                    error = "Redirects are not allowed for imported resources."
                else:
                    body = r.text[:2000]
            except requests.RequestException:
                error = "Could not fetch the resource."
    return templates.TemplateResponse(
        "resource_import.html",
        {"request": request, "user": user, "body": body, "url": url, "error": error},
    )


@router.post("/resources/import", response_class=HTMLResponse)
def import_resource_post(request: Request, url: str = Form(...)):
    return import_resource_get(request, url)


@router.get("/error", response_class=HTMLResponse)
def trigger_error(request: Request):
    try:
        x = 1 / 0
        return {"x": x}
    except Exception:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "details": traceback.format_exc()},
            status_code=500,
        )
