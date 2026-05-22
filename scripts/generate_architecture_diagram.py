#!/usr/bin/env python3
"""Generate a PDF architecture diagram for the SCD Reporting application."""

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate
from reportlab.graphics.shapes import (
    Drawing, Rect, String, Line, Group, Circle, Polygon
)
from reportlab.graphics import renderPDF
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer
import sys
import os

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "SCD-Reporting-Architecture.pdf")

# ── Colours ──────────────────────────────────────────────────────────────────
C_CONTAINER_BG   = colors.HexColor("#e8f4fd")   # light blue – inside container
C_CONTAINER_BD   = colors.HexColor("#2980b9")   # blue border
C_VOLUME_BG      = colors.HexColor("#fef9e7")   # light yellow – shared volume
C_VOLUME_BD      = colors.HexColor("#f39c12")   # amber border
C_EXTERNAL_BG    = colors.HexColor("#fde8e8")   # light red – external service
C_EXTERNAL_BD    = colors.HexColor("#c0392b")   # red border
C_DB_BG          = colors.HexColor("#e8fde8")   # light green – database
C_DB_BD          = colors.HexColor("#27ae60")   # green border
C_CADDY_BG       = colors.HexColor("#f0e8fd")   # light purple – caddy
C_CADDY_BD       = colors.HexColor("#8e44ad")   # purple border
C_APP_BG         = colors.HexColor("#e8f4fd")
C_SECTION_BG     = colors.HexColor("#d6eaf8")
C_SECTION_BD     = colors.HexColor("#1a5276")
C_ARROW          = colors.HexColor("#34495e")
C_LEGEND_TEXT    = colors.HexColor("#2c3e50")
WHITE            = colors.white
BLACK            = colors.black

FONT_TITLE  = "Helvetica-Bold"
FONT_LABEL  = "Helvetica-Bold"
FONT_BODY   = "Helvetica"
FONT_SMALL  = "Helvetica"


def box(d, x, y, w, h, bg, bd, label, sublabels=(), radius=6, label_size=10, sub_size=8):
    """Draw a rounded rectangle with a bold label and optional sub-labels."""
    d.add(Rect(x, y, w, h, rx=radius, ry=radius,
               fillColor=bg, strokeColor=bd, strokeWidth=1.5))
    lines = [label] + list(sublabels)
    total_h = label_size + len(sublabels) * (sub_size + 2) + 6
    ty = y + h/2 + total_h/2 - label_size
    d.add(String(x + w/2, ty, label,
                 fontName=FONT_LABEL, fontSize=label_size,
                 fillColor=BLACK, textAnchor="middle"))
    for i, sl in enumerate(sublabels):
        sy = ty - (i + 1) * (sub_size + 2) - 2
        d.add(String(x + w/2, sy, sl,
                     fontName=FONT_BODY, fontSize=sub_size,
                     fillColor=colors.HexColor("#555555"), textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, label="", bidirectional=False):
    """Draw an arrow between two points with an optional label."""
    d.add(Line(x1, y1, x2, y2, strokeColor=C_ARROW, strokeWidth=1.2))
    # arrowhead at (x2, y2)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    ah = 7
    for sign in ([1, -1] if bidirectional else [-1]):
        bx = x2 - ah * math.cos(angle) if not bidirectional or sign == -1 else x1 + ah * math.cos(angle)
        by = y2 - ah * math.sin(angle) if not bidirectional or sign == -1 else y1 + ah * math.sin(angle)
        px = bx + sign * ah * 0.5 * math.sin(angle)
        py = by - sign * ah * 0.5 * math.cos(angle)
        qx = bx - sign * ah * 0.5 * math.sin(angle)
        qy = by + sign * ah * 0.5 * math.cos(angle)
        tx, ty_ = (x2, y2) if sign == -1 else (x1, y1)
        d.add(Polygon([tx, ty_, px, py, qx, qy],
                      fillColor=C_ARROW, strokeColor=C_ARROW, strokeWidth=0.5))
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        d.add(String(mx + 3, my + 3, label,
                     fontName=FONT_SMALL, fontSize=7,
                     fillColor=C_ARROW, textAnchor="start"))


def dashed_line(d, x1, y1, x2, y2):
    d.add(Line(x1, y1, x2, y2,
               strokeColor=C_ARROW, strokeWidth=1.0,
               strokeDashArray=[4, 3]))


# ── Page setup ────────────────────────────────────────────────────────────────
PW, PH = landscape(A3)   # 1190 x 842  pts  (A3 landscape)
MARGIN = 30

d = Drawing(PW, PH)

# ── Title ──────────────────────────────────────────────────────────────────────
d.add(String(PW / 2, PH - 28, "SCD Reporting — Application Architecture",
             fontName=FONT_TITLE, fontSize=18, fillColor=C_SECTION_BD,
             textAnchor="middle"))
d.add(String(PW / 2, PH - 46, "Container topology, data items, and service boundaries",
             fontName=FONT_BODY, fontSize=10, fillColor=colors.HexColor("#7f8c8d"),
             textAnchor="middle"))


# ═══════════════════════════════════════════════════════════════════════════════
# Layout constants  (origin = bottom-left of drawing)
# ═══════════════════════════════════════════════════════════════════════════════
# We divide the page into three horizontal bands:
#   Top:    External services / clients
#   Middle: Docker Compose services
#   Bottom: Volumes / persistent data

EXT_TOP   = PH - 70
EXT_H     = 110
EXT_Y     = EXT_TOP - EXT_H         # top of external band

DC_TOP    = EXT_Y - 20
DC_H      = 380
DC_Y      = DC_TOP - DC_H           # top of Docker Compose band

VOL_TOP   = DC_Y - 20
VOL_H     = 115
VOL_Y     = VOL_TOP - VOL_H         # top of volumes band


# ── Band labels ────────────────────────────────────────────────────────────────
def band_label(d, x, y, w, h, text):
    d.add(Rect(x, y, w, h, rx=4, ry=4,
               fillColor=colors.HexColor("#ecf0f1"), strokeColor=colors.HexColor("#bdc3c7"),
               strokeWidth=1))
    d.add(String(x + w / 2, y + h / 2 - 5, text,
                 fontName=FONT_TITLE, fontSize=9, fillColor=colors.HexColor("#7f8c8d"),
                 textAnchor="middle"))


band_label(d, MARGIN, EXT_Y,  PW - 2*MARGIN, EXT_H,  "EXTERNAL  ( internet / Fermilab network )")
band_label(d, MARGIN, DC_Y,   PW - 2*MARGIN, DC_H,   "DOCKER COMPOSE  ( host machine )")
band_label(d, MARGIN, VOL_Y,  PW - 2*MARGIN, VOL_H,  "NAMED VOLUMES  ( Docker-managed persistent storage )")


# ═══════════════════════════════════════════════════════════════════════════════
# EXTERNAL SERVICES
# ═══════════════════════════════════════════════════════════════════════════════
ext_w, ext_h = 148, 66
ext_spacing  = (PW - 2*MARGIN - 5*ext_w) / 6
ext_bases    = [MARGIN + ext_spacing + i*(ext_w + ext_spacing) for i in range(5)]
ext_y        = EXT_Y + (EXT_H - ext_h) / 2

EX = {}  # name → (cx, cy)  centre points for arrow anchors

for i, (name, sub, key) in enumerate([
    ("Browser / Client",    ("HTTPS :443",),          "browser"),
    ("Fermilab SSO (OIDC)", ("Keycloak",),             "sso"),
    ("Google OAuth",        ("Social login",),         "google"),
    ("GitHub API",          ("Bug reports",),          "github"),
    ("Anthropic API",       ("AI summaries",),         "anthropic"),
]):
    bx = ext_bases[i]
    box(d, bx, ext_y, ext_w, ext_h, C_EXTERNAL_BG, C_EXTERNAL_BD, name, sub, label_size=9)
    EX[key] = (bx + ext_w/2, ext_y)   # bottom-centre anchor


# ═══════════════════════════════════════════════════════════════════════════════
# DOCKER COMPOSE SERVICES
# ═══════════════════════════════════════════════════════════════════════════════

# ── Caddy container ────────────────────────────────────────────────────────────
caddy_x, caddy_w, caddy_h = MARGIN + 40, 160, DC_H - 40
caddy_y = DC_Y + 20
box(d, caddy_x, caddy_y, caddy_w, caddy_h, C_CADDY_BG, C_CADDY_BD,
    "caddy", ("caddy:2-alpine", "ports 80, 443, 443/udp",
              "TLS termination", "Caddyfile: /etc/caddy/Caddyfile  [ro]",
              "→ /static/*  from volume", "→ /media/*   from volume",
              "reverse_proxy → web:8000"),
    label_size=11, sub_size=8)
caddy_cx = caddy_x + caddy_w/2


# ── Web container ─────────────────────────────────────────────────────────────
web_x = caddy_x + caddy_w + 30
web_w = 480
web_h = DC_H - 40
web_y = DC_Y + 20

# outer web container box
box(d, web_x, web_y, web_w, web_h, C_CONTAINER_BG, C_CONTAINER_BD,
    "web  (Django + Gunicorn)", ("Built from docker/web/Dockerfile",
                                  "python:3.12-slim  •  expose :8000",
                                  "DJANGO_SETTINGS_MODULE: scd_reporting.settings.prod"),
    label_size=11, sub_size=8)

# ─ inner sections inside web container ─
INNER_MARGIN = 12
iw = web_w - 2*INNER_MARGIN
ix = web_x + INNER_MARGIN

# Section: Django Apps
apps_h = 170
apps_y = web_y + INNER_MARGIN + 10
box(d, ix, apps_y, iw, apps_h, C_SECTION_BG, C_SECTION_BD,
    "Django Apps  ( apps/ )", (), label_size=9)

app_items = [
    ("core",     "Dashboard, Bug report, About"),
    ("accounts", "Users, SiteSettings, Auth"),
    ("entries",  "WorkItem"),
    ("reports",  "Reports, AIPromptConfig"),
    ("taxonomy", "Project, Category, WorkGroup,\nLabPriority, Tag"),
    ("audit",    "AuditLogEntry"),
]
app_w = (iw - 2*6 - 5*4) / 6
app_h2 = apps_h - 30
app_y2 = apps_y + 10

for j, (aname, amod) in enumerate(app_items):
    ax = ix + 6 + j*(app_w + 4)
    box(d, ax, app_y2, app_w, app_h2,
        C_APP_BG, C_CONTAINER_BD, aname,
        tuple(amod.split("\n")), label_size=8, sub_size=7)

# Section: Static Assets (baked in)
static_h = 60
static_y = apps_y + apps_h + 8
box(d, ix, static_y, iw, static_h, C_SECTION_BG, C_SECTION_BD,
    "Static Assets  [baked into image]",
    ("Tailwind CSS compiled in Docker build stage (node:20-alpine)",
     "theme/static/css/dist/styles.css  •  theme/static/images/  •  app JS"),
    label_size=9, sub_size=8)

# Section: Templates
tmpl_h = 45
tmpl_y = static_y + static_h + 8
box(d, ix, tmpl_y, iw, tmpl_h, C_SECTION_BG, C_SECTION_BD,
    "Jinja2 / Django Templates  [baked into image]",
    ("apps/*/templates/**  •  apps/core/templates/base.html  •  HTMX partials",),
    label_size=9, sub_size=8)

# Section: Entrypoint
entry_h = 45
entry_y = tmpl_y + tmpl_h + 8
box(d, ix, entry_y, iw, entry_h, C_SECTION_BG, C_SECTION_BD,
    "Entrypoint  (docker/web/entrypoint.sh)",
    ("manage.py migrate  →  collectstatic  →  seed_admin  →  gunicorn",),
    label_size=9, sub_size=8)


web_cx = web_x + web_w/2


# ── PostgreSQL container ───────────────────────────────────────────────────────
pg_x = web_x + web_w + 30
pg_w = 160
pg_h = DC_H - 40
pg_y = DC_Y + 20
box(d, pg_x, pg_y, pg_w, pg_h, C_DB_BG, C_DB_BD,
    "db", ("postgres:16-alpine", "internal only", "POSTGRES_DB: scd",
           "POSTGRES_USER: scd", "POSTGRES_PASSWORD: [env]",
           "", "pgdata volume →", "/var/lib/postgresql/data"),
    label_size=11, sub_size=8)
pg_cx = pg_x + pg_w/2


# ── GitHub Actions (optional side note) ───────────────────────────────────────
# (not a running container; shown as annotation)
ga_x = pg_x + pg_w + 20
ga_w = 140
ga_h = 80
ga_y = DC_Y + 20 + (DC_H - 40 - ga_h) / 2
box(d, ga_x, ga_y, ga_w, ga_h, colors.HexColor("#fff8e1"), colors.HexColor("#f57f17"),
    "CI / Deploy",
    ("GitHub Actions", "builds & pushes image", "passes GIT_COMMIT, GIT_DATE,",
     "GIT_TAG build args"),
    label_size=9, sub_size=7)


# ═══════════════════════════════════════════════════════════════════════════════
# NAMED VOLUMES
# ═══════════════════════════════════════════════════════════════════════════════
vol_items = [
    ("staticfiles",  "collectstatic output",  "web rw  →  caddy ro (/srv/static)"),
    ("media",        "user uploads",           "web rw  →  caddy ro (/srv/media)"),
    ("pgdata",       "PostgreSQL data files",  "db rw only"),
    ("caddy_data",   "TLS certs / ACME state", "caddy rw only"),
    ("caddy_config", "Caddy runtime config",   "caddy rw only"),
]
vol_w = (PW - 2*MARGIN - 40 - 4*12) / 5
vol_spacing = 12
vol_h2 = VOL_H - 30
vol_base_y = VOL_Y + 15

for k, (vname, vdesc, vusers) in enumerate(vol_items):
    vx = MARGIN + 20 + k*(vol_w + vol_spacing)
    bg = C_VOLUME_BG if "caddy" not in vname and "pg" not in vname else (
        C_DB_BG if "pg" in vname else C_CADDY_BG)
    bd = C_VOLUME_BD if "caddy" not in vname and "pg" not in vname else (
        C_DB_BD if "pg" in vname else C_CADDY_BD)
    box(d, vx, vol_base_y, vol_w, vol_h2, bg, bd, vname, (vdesc, vusers),
        label_size=9, sub_size=8)
    # store centre for arrows
    globals()["vol_" + vname.replace("-", "_") + "_cx"] = vx + vol_w/2


# ═══════════════════════════════════════════════════════════════════════════════
# ARROWS  — inter-service and service-to-volume
# ═══════════════════════════════════════════════════════════════════════════════

# Browser → Caddy top
browser_top = EXT_Y + EXT_H/2
caddy_top = DC_TOP
arrow(d, EX["browser"][0], EXT_Y, caddy_cx, DC_TOP, "HTTPS")

# Caddy → web (horizontal, inside DC band)
arrow(d, caddy_x + caddy_w, caddy_y + caddy_h/2,
         web_x,               web_y + web_h/2,  "reverse_proxy :8000")

# web → db
arrow(d, web_x + web_w, web_y + web_h/2,
         pg_x,           pg_y + pg_h/2,  "DATABASE_URL")

# web → staticfiles volume (down)
sv_x = globals()["vol_staticfiles_cx"]
arrow(d, web_cx - 30, web_y,
         sv_x,         VOL_TOP,  "collectstatic")

# web → media volume (down)
mv_x = globals()["vol_media_cx"]
arrow(d, web_cx + 10, web_y,
         mv_x,         VOL_TOP,  "media uploads")

# caddy → staticfiles (volume to caddy — dashed, caddy reads it)
dashed_line(d, caddy_cx, caddy_y,
               sv_x,     VOL_TOP)

# caddy → media volume
dashed_line(d, caddy_cx - 10, caddy_y,
               mv_x,            VOL_TOP)

# pgdata volume ↔ db
pv_x = globals()["vol_pgdata_cx"]
arrow(d, pg_cx, pg_y, pv_x, VOL_TOP, "pgdata")

# caddy_data / caddy_config volumes
cdv_x = globals()["vol_caddy_data_cx"]
ccv_x = globals()["vol_caddy_config_cx"]
arrow(d, caddy_cx + 20, caddy_y, cdv_x, VOL_TOP, "TLS state")
arrow(d, caddy_cx + 40, caddy_y, ccv_x, VOL_TOP, "runtime cfg")

# SSO → web
arrow(d, EX["sso"][0],       EXT_Y,
         web_x + web_w*0.2,  DC_TOP,  "OIDC callback")

# Google → web
arrow(d, EX["google"][0],    EXT_Y,
         web_x + web_w*0.4,  DC_TOP,  "OAuth callback")

# web → GitHub (external)
arrow(d, web_x + web_w*0.6,  DC_TOP,
         EX["github"][0],    EXT_Y,   "bug report POST")

# web → Anthropic (external)
arrow(d, web_x + web_w*0.8,  DC_TOP,
         EX["anthropic"][0], EXT_Y,   "AI summary")

# CI → web image (dashed)
dashed_line(d, ga_x + ga_w/2, ga_y + ga_h, web_x + web_w, web_y + web_h*0.3)


# ═══════════════════════════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════════════════════════
leg_x = PW - MARGIN - 220
leg_y = VOL_Y - 10
leg_w = 215
leg_h = 95

d.add(Rect(leg_x, leg_y, leg_w, leg_h, rx=4, ry=4,
           fillColor=colors.white, strokeColor=colors.HexColor("#bdc3c7"), strokeWidth=1))
d.add(String(leg_x + leg_w/2, leg_y + leg_h - 14, "Legend",
             fontName=FONT_TITLE, fontSize=9, textAnchor="middle", fillColor=BLACK))

legend_items = [
    (C_CONTAINER_BG, C_CONTAINER_BD, "Container / app code  [baked in image]"),
    (C_VOLUME_BG,    C_VOLUME_BD,    "Shared named volume  [linked]"),
    (C_DB_BG,        C_DB_BD,        "Database container / volume"),
    (C_CADDY_BG,     C_CADDY_BD,     "Reverse proxy (Caddy)"),
    (C_EXTERNAL_BG,  C_EXTERNAL_BD,  "External service"),
]
for i, (bg, bd, lbl) in enumerate(legend_items):
    ly = leg_y + leg_h - 26 - i*14
    d.add(Rect(leg_x + 8, ly, 12, 10, fillColor=bg, strokeColor=bd, strokeWidth=1))
    d.add(String(leg_x + 26, ly + 1, lbl,
                 fontName=FONT_SMALL, fontSize=7.5, fillColor=BLACK))

# ── Render ────────────────────────────────────────────────────────────────────
renderPDF.drawToFile(d, OUTPUT, "SCD Reporting Architecture")
print(f"Written: {OUTPUT}")
