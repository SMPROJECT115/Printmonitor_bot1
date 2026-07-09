# -*- coding: utf-8 -*-
"""
PRINTMONITOR — FIX INCORRECT TIME ZONE (V2)

Fuerza America/Mexico_City (Hora del Centro de Mexico / UTC-6) en:
  - C:\\PrintMonitor\\.secure\\timezone.env
  - C:\\PrintMonitor\\python\\generate_report.py
  - C:\\PrintMonitor\\bot\\telegram_bot.py
  - C:\\PrintMonitor\\bot\\_env.bat  (PRINTMONITOR_TZ / TZ)
  - Zona de Windows: Central Standard Time (Mexico)  [si hay permisos]

Idempotente: marker FIX INCORRECT TIMEZONE V2
"""

from __future__ import print_function

import os
import re
import shutil
import subprocess
import sys
import time

MARKER = "FIX INCORRECT TIMEZONE V2"
MARKER_V1 = "REPORT TIMEZONE FIX V1"
IANA_TZ = "America/Mexico_City"
WINDOWS_TZ = "Central Standard Time (Mexico)"
UTC_OFFSET_HOURS = -6

ROOT = r"C:\PrintMonitor"
TARGET_REPORT = os.path.join(ROOT, "python", "generate_report.py")
TARGET_BOT = os.path.join(ROOT, "bot", "telegram_bot.py")
TARGET_ENV_BAT = os.path.join(ROOT, "bot", "_env.bat")
TARGET_TZ_ENV = os.path.join(ROOT, ".secure", "timezone.env")
UPDATES_DIR = os.path.join(ROOT, "updates")
BACKUP_DIR = os.path.join(ROOT, "logs", "backups")
APPLIED_LOG = os.path.join(ROOT, "logs", "applied_updates.log")
UPDATE_NAME = "fix_incorrect_timezone_update.py"


def log(msg, color=None):
    colors = {
        "g": "\033[92m",
        "c": "\033[96m",
        "y": "\033[93m",
        "r": "\033[91m",
        "x": "\033[0m",
    }
    if color and color in colors and sys.stdout.isatty():
        print("%s%s%s" % (colors[color], msg, colors["x"]))
    else:
        print(msg)
    sys.stdout.flush()


def ensure_dirs():
    for path in (
        os.path.join(ROOT, "python"),
        os.path.join(ROOT, "bot"),
        os.path.join(ROOT, ".secure"),
        os.path.join(ROOT, "logs"),
        BACKUP_DIR,
        UPDATES_DIR,
    ):
        os.makedirs(path, exist_ok=True)


def backup(path):
    if not os.path.isfile(path):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = os.path.basename(path)
    dest = os.path.join(
        BACKUP_DIR,
        "%s.bak_%s" % (name, time.strftime("%Y%m%d_%H%M%S")),
    )
    try:
        shutil.copy2(path, dest)
        log("  Backup: %s" % dest, "c")
        return dest
    except Exception as exc:
        log("  [AVISO] backup fallido: %s" % exc, "y")
        return None


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


# ---------------------------------------------------------------------------
# 1) timezone.env
# ---------------------------------------------------------------------------
def write_timezone_env():
    content = (
        "# PrintMonitor — zona horaria de reportes y bot\n"
        "# FIX INCORRECT TIMEZONE V2\n"
        "# Ejemplos: America/Mexico_City | America/Tijuana | America/Cancun\n"
        "REPORT_TZ=%s\n"
        "PRINTMONITOR_TZ=%s\n"
        "TZ=%s\n"
    ) % (IANA_TZ, IANA_TZ, IANA_TZ)
    write_text(TARGET_TZ_ENV, content)
    log("[OK] timezone.env → %s" % IANA_TZ, "g")


# ---------------------------------------------------------------------------
# 2) _env.bat — variables para Python al arrancar el bot
# ---------------------------------------------------------------------------
def patch_env_bat():
    block = (
        "\r\n"
        "REM === FIX INCORRECT TIMEZONE V2 ===\r\n"
        "set \"PRINTMONITOR_TZ=%s\"\r\n"
        "set \"TZ=%s\"\r\n"
        "set \"REPORT_TZ=%s\"\r\n"
    ) % (IANA_TZ, IANA_TZ, IANA_TZ)

    if not os.path.isfile(TARGET_ENV_BAT):
        write_text(TARGET_ENV_BAT, "@echo off\r\n" + block.replace("\r\n", "\n"))
        log("[OK] _env.bat creado con TZ Mexico", "g")
        return

    content = read_text(TARGET_ENV_BAT)
    if MARKER in content or "PRINTMONITOR_TZ=" in content:
        # Reescribir bloque limpio
        content = re.sub(
            r"\r?\nREM === FIX INCORRECT TIMEZONE V2 ===.*?(?=\r?\n[^\r\n]|\Z)",
            "",
            content,
            flags=re.DOTALL,
        )
        # quitar lineas sueltas viejas de TZ
        lines = []
        for line in content.splitlines(True):
            if re.match(r"(?i)^\s*set\s+\"?(PRINTMONITOR_TZ|TZ|REPORT_TZ)=", line):
                continue
            if "FIX INCORRECT TIMEZONE" in line:
                continue
            lines.append(line)
        content = "".join(lines)

    backup(TARGET_ENV_BAT)
    if not content.endswith("\n"):
        content += "\r\n"
    content += block
    # mantener CRLF tipico de bat
    content = content.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(TARGET_ENV_BAT, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)
    log("[OK] _env.bat con PRINTMONITOR_TZ / TZ", "g")


# ---------------------------------------------------------------------------
# 3) generate_report.py — asegurar TZ Mexico robusta
# ---------------------------------------------------------------------------
GENERATE_REPORT_SOURCE = r'''# -*- coding: utf-8 -*-
"""Genera reporte PDF desde logs CSV de PaperCut Print Logger.

Zona horaria: America/Mexico_City (Hora del Centro de Mexico, UTC-6).
FIX INCORRECT TIMEZONE V2
"""

from __future__ import print_function

import csv
import glob
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# =====================================================
# ZONA HORARIA DEL REPORTE (Mexico Centro)
# REPORT TIMEZONE FIX V1
# FIX INCORRECT TIMEZONE V2
# =====================================================
# Prioridad:
#   1) Variable de entorno PRINTMONITOR_TZ / REPORT_TZ / TZ
#   2) Archivo C:\PrintMonitor\.secure\timezone.env
#   3) America/Mexico_City
DEFAULT_TZ_NAME = "America/Mexico_City"
TZ_ENV_FILE = r"C:\PrintMonitor\.secure\timezone.env"
CSV_FOLDERS = (
    r"C:\Program Files (x86)\PaperCut Print Logger\logs\csv\daily",
    r"C:\Program Files\PaperCut Print Logger\logs\csv\daily",
    r"C:\Program Files (x86)\PaperCut Print Logger\logs\csv",
    r"C:\Program Files\PaperCut Print Logger\logs\csv",
)
OUTPUT_FOLDER = r"C:\PrintMonitor\reports\pdf"

# Forzar env de proceso para hijos / librerias
os.environ.setdefault("PRINTMONITOR_TZ", DEFAULT_TZ_NAME)
os.environ.setdefault("TZ", DEFAULT_TZ_NAME)


def _read_tz_name():
    for key in ("PRINTMONITOR_TZ", "REPORT_TZ", "TZ"):
        env = (os.environ.get(key) or "").strip()
        if env and env.upper() not in ("UTC", "GMT", "LOCAL"):
            # No permitir UTC accidental en este producto (Mexico)
            if env in ("America/Mexico_City", "America/Tijuana", "America/Cancun",
                       "America/Monterrey", "America/Mazatlan", "America/Hermosillo",
                       "America/Chihuahua", "America/Merida", "America/Bahia_Banderas"):
                return env
            if env.startswith("America/"):
                return env
    if os.path.isfile(TZ_ENV_FILE):
        try:
            with open(TZ_ENV_FILE, "r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    if key.strip() in ("REPORT_TZ", "PRINTMONITOR_TZ", "TZ"):
                        val = val.strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass
    return DEFAULT_TZ_NAME


def get_report_tz():
    """Timezone de Mexico (o la configurada). Fallback UTC-6 fijo."""
    name = _read_tz_name()
    # Preferir IANA real
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name), name
    except Exception:
        pass
    try:
        import pytz  # type: ignore
        return pytz.timezone(name), name
    except Exception:
        pass
    # Windows sin tzdata: offset fijo Mexico (UTC-6; sin DST federal desde 2022)
    return timezone(timedelta(hours=-6)), name + " (UTC-6 fijo)"


REPORT_TZ, REPORT_TZ_LABEL = get_report_tz()


def now_local():
    """Ahora en zona del reporte (aware)."""
    try:
        return datetime.now(REPORT_TZ)
    except Exception:
        utc_now = datetime.now(timezone.utc)
        try:
            return utc_now.astimezone(REPORT_TZ)
        except Exception:
            return datetime.now().replace(tzinfo=REPORT_TZ)


def today_str():
    return now_local().strftime("%Y-%m-%d")


def parse_csv_datetime(raw):
    """
    Parsea la columna Hora de PaperCut.
    Formatos tipicos:
      2026-05-21 23:15:45
      21/05/2026 23:15:45
      2026-05-21T23:15:45Z
      2026-05-21T23:15:45+00:00
    Si no trae zona, se asume America/Mexico_City (hora local PaperCut).
    """
    text = (raw or "").strip().strip('"')
    if not text:
        return None

    # ISO con Z → convertir a Mexico
    if text.endswith("Z") and "T" in text:
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.astimezone(REPORT_TZ)
        except Exception:
            pass

    # ISO con offset
    try:
        if "T" in text or (len(text) > 19 and ("+" in text[10:] or text.count("-") > 2)):
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                try:
                    return REPORT_TZ.localize(dt) if hasattr(REPORT_TZ, "localize") else dt.replace(tzinfo=REPORT_TZ)
                except Exception:
                    return dt.replace(tzinfo=REPORT_TZ)
            return dt.astimezone(REPORT_TZ)
    except Exception:
        pass

    patterns = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    )
    for fmt in patterns:
        try:
            dt = datetime.strptime(text, fmt)
            try:
                if hasattr(REPORT_TZ, "localize"):
                    return REPORT_TZ.localize(dt)
                return dt.replace(tzinfo=REPORT_TZ)
            except Exception:
                return dt.replace(tzinfo=REPORT_TZ)
        except ValueError:
            continue

    # Solo hora HH:MM:SS
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        s = int(m.group(3) or 0)
        return now_local().replace(hour=h, minute=mi, second=s, microsecond=0)

    return None


def format_time_local(dt):
    if dt is None:
        return ""
    try:
        return dt.astimezone(REPORT_TZ).strftime("%H:%M:%S")
    except Exception:
        return dt.strftime("%H:%M:%S")


def format_datetime_local(dt):
    if dt is None:
        return ""
    try:
        return dt.astimezone(REPORT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def find_csv_for_date(report_date):
    names = (
        "%s.csv" % report_date,
        "papercut-print-log-%s.csv" % report_date,
    )
    try:
        base = datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError:
        base = None

    for folder in CSV_FOLDERS:
        if not os.path.isdir(folder):
            continue
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path

    if base is not None:
        for delta in range(1, 4):
            for sign in (-1, 1):
                d = (base + timedelta(days=sign * delta)).strftime("%Y-%m-%d")
                for folder in CSV_FOLDERS:
                    if not os.path.isdir(folder):
                        continue
                    for name in ("%s.csv" % d, "papercut-print-log-%s.csv" % d):
                        path = os.path.join(folder, name)
                        if os.path.isfile(path):
                            return path

    candidates = []
    for folder in CSV_FOLDERS:
        if not os.path.isdir(folder):
            continue
        candidates.extend(glob.glob(os.path.join(folder, "*.csv")))
        monthly = os.path.join(os.path.dirname(folder), "monthly")
        if os.path.isdir(monthly):
            candidates.extend(glob.glob(os.path.join(monthly, "*.csv")))
    if candidates:
        return max(candidates, key=os.path.getmtime)
    return None


def _read_csv_text(csv_file):
    for enc in ("cp1252", "utf-8", "latin-1"):
        try:
            with open(csv_file, "r", encoding=enc, errors="strict", newline="") as handle:
                return handle.read()
        except Exception:
            continue
    with open(csv_file, "r", encoding="cp1252", errors="ignore", newline="") as handle:
        return handle.read()


def load_rows_for_date(csv_file, report_date):
    """Lee CSV y devuelve filas del dia report_date en zona Mexico."""
    rows = []
    content = _read_csv_text(csv_file)
    reader = csv.reader(content.splitlines())
    header_skipped = False
    for row in reader:
        if not row:
            continue
        first = (row[0] or "").strip()
        if not header_skipped:
            if "PaperCut" in first or first.lower().startswith("hora") or "Time" in first:
                if first.lower().startswith("hora") or first.lower() == "time":
                    header_skipped = True
                continue
            header_skipped = True
        if len(row) < 6:
            continue
        if "Hora" in first or first.lower() == "time":
            continue
        dt = parse_csv_datetime(first)
        if dt is None:
            hora = first.split(" ")[-1] if " " in first else first
            rows.append({
                "dt": None,
                "hora": hora,
                "usuario": row[1].strip() if len(row) > 1 else "",
                "paginas": row[2].strip() if len(row) > 2 else "",
                "copias": row[3].strip() if len(row) > 3 else "",
                "impresora": (row[4].strip() if len(row) > 4 else "")[:22],
                "documento": (row[5].strip() if len(row) > 5 else "")[:24],
                "cliente": (row[6].strip() if len(row) > 6 else "")[:12],
                "duplex": row[7].strip() if len(row) > 7 else "",
                "escala": row[8].strip() if len(row) > 8 else "",
            })
            continue
        day = dt.astimezone(REPORT_TZ).strftime("%Y-%m-%d")
        if day != report_date:
            continue
        rows.append({
            "dt": dt,
            "hora": format_time_local(dt),
            "usuario": row[1].strip() if len(row) > 1 else "",
            "paginas": row[2].strip() if len(row) > 2 else "",
            "copias": row[3].strip() if len(row) > 3 else "",
            "impresora": (row[4].strip() if len(row) > 4 else "")[:22],
            "documento": (row[5].strip() if len(row) > 5 else "")[:24],
            "cliente": (row[6].strip() if len(row) > 6 else "")[:12],
            "duplex": row[7].strip() if len(row) > 7 else "",
            "escala": row[8].strip() if len(row) > 8 else "",
        })
    rows.sort(key=lambda r: (r["dt"] is None, r["dt"] or datetime.min.replace(tzinfo=REPORT_TZ)))
    return rows


def load_rows_for_date_unfiltered(csv_file):
    """Lee filas sin filtrar por dia (archivo ya es del dia)."""
    rows = []
    content = _read_csv_text(csv_file)
    reader = csv.reader(content.splitlines())
    for row in reader:
        if not row or len(row) < 6:
            continue
        first = (row[0] or "").strip()
        if "PaperCut" in first or first.lower().startswith("hora") or first.lower() == "time":
            continue
        dt = parse_csv_datetime(first)
        hora = format_time_local(dt) if dt else (first.split(" ")[-1] if " " in first else first)
        rows.append({
            "dt": dt,
            "hora": hora,
            "usuario": row[1].strip() if len(row) > 1 else "",
            "paginas": row[2].strip() if len(row) > 2 else "",
            "copias": row[3].strip() if len(row) > 3 else "",
            "impresora": (row[4].strip() if len(row) > 4 else "")[:22],
            "documento": (row[5].strip() if len(row) > 5 else "")[:24],
            "cliente": (row[6].strip() if len(row) > 6 else "")[:12],
            "duplex": row[7].strip() if len(row) > 7 else "",
            "escala": row[8].strip() if len(row) > 8 else "",
        })
    rows.sort(key=lambda r: (r["dt"] is None, r["dt"] or datetime.min.replace(tzinfo=timezone.utc)))
    return rows


def main():
    if len(sys.argv) > 1:
        report_date = sys.argv[1].strip()
    else:
        report_date = today_str()

    try:
        datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError:
        print("")
        print("FECHA INVALIDA. Usa formato YYYY-MM-DD")
        print("")
        sys.stdout.flush()
        return 1

    print("")
    print("ZONA HORARIA REPORTE: %s" % REPORT_TZ_LABEL)
    print("FECHA SOLICITADA: %s" % report_date)
    print("AHORA LOCAL: %s" % format_datetime_local(now_local()))
    print("")

    csv_file = find_csv_for_date(report_date)
    if not csv_file:
        print("")
        print("NO SE ENCONTRO CSV")
        print("")
        sys.stdout.flush()
        return 1

    print("CSV DETECTADO:")
    print(csv_file)
    print("")
    print("GENERANDO PDF (horas en zona Mexico)...")
    print("")

    data_rows = load_rows_for_date(csv_file, report_date)
    if not data_rows and report_date in os.path.basename(csv_file):
        data_rows = load_rows_for_date_unfiltered(csv_file)

    if not data_rows:
        print("")
        print("NO SE ENCONTRARON DATOS")
        print("para la fecha %s en zona %s" % (report_date, REPORT_TZ_LABEL))
        print("")
        sys.stdout.flush()
        return 1

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    stamp = now_local().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_path = os.path.join(OUTPUT_FOLDER, "PrintMonitor_Report_%s.pdf" % stamp)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<font size='22'><b>PRINTMONITOR ENTERPRISE</b></font>", styles["Title"]),
        Spacer(1, 10),
        Paragraph(
            "<font size='12'><b>Fecha del reporte:</b> %s</font>" % report_date,
            styles["BodyText"],
        ),
        Paragraph(
            "<font size='10'><b>Zona horaria:</b> %s</font>" % REPORT_TZ_LABEL,
            styles["BodyText"],
        ),
        Paragraph(
            "<font size='10'><b>Generado:</b> %s</font>" % format_datetime_local(now_local()),
            styles["BodyText"],
        ),
        Spacer(1, 12),
    ]

    table_data = [[
        "Hora", "Usuario", "Paginas", "Copias", "Impresora",
        "Documento", "Cliente", "Frente/Reverso", "Escala",
    ]]
    for item in data_rows:
        table_data.append([
            item["hora"],
            item["usuario"],
            item["paginas"],
            item["copias"],
            item["impresora"],
            item["documento"],
            item["cliente"],
            item["duplex"],
            item["escala"],
        ])

    col_widths = [52, 55, 40, 40, 100, 105, 70, 70, 55]
    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#355CFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)
    doc.build(elements)

    print("")
    print("===================================")
    print("PDF GENERADO")
    print("===================================")
    print("")
    print(pdf_path)
    print("Registros: %d" % len(data_rows))
    print("Zona: %s" % REPORT_TZ_LABEL)
    print("")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def patch_generate_report():
    if os.path.isfile(TARGET_REPORT):
        current = read_text(TARGET_REPORT)
        if MARKER in current:
            log("[OK] generate_report.py ya tiene %s" % MARKER, "g")
            # Aun asi reforzar env defaults si faltan
            if 'os.environ.setdefault("PRINTMONITOR_TZ"' not in current:
                backup(TARGET_REPORT)
                write_text(TARGET_REPORT, GENERATE_REPORT_SOURCE)
                log("[OK] generate_report.py reforzado (env defaults)", "g")
            return
        backup(TARGET_REPORT)
    write_text(TARGET_REPORT, GENERATE_REPORT_SOURCE)
    log("[OK] generate_report.py actualizado (Mexico TZ)", "g")


# ---------------------------------------------------------------------------
# 4) telegram_bot.py — helper now_mexico + /estado + timestamps
# ---------------------------------------------------------------------------
HELPER_BLOCK = '''
# =====================================================
# FIX INCORRECT TIMEZONE V2 — hora Mexico en el bot
# =====================================================
_TZ_NAME = "America/Mexico_City"


def _get_mexico_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(_TZ_NAME)
    except Exception:
        pass
    try:
        import pytz  # type: ignore
        return pytz.timezone(_TZ_NAME)
    except Exception:
        pass
    from datetime import timezone, timedelta
    return timezone(timedelta(hours=-6))


def now_mexico():
    """Datetime aware en America/Mexico_City."""
    from datetime import datetime as _dt
    try:
        return _dt.now(_get_mexico_tz())
    except Exception:
        from datetime import timezone as _tz, timedelta as _td
        return _dt.now(_tz(_td(hours=-6)))


def now_mexico_str(fmt="%Y-%m-%d %H:%M:%S"):
    return now_mexico().strftime(fmt) + " (Mexico)"

'''


def patch_telegram_bot():
    if not os.path.isfile(TARGET_BOT):
        log("[AVISO] telegram_bot.py no encontrado — se omite", "y")
        return

    content = read_text(TARGET_BOT)
    changed = False

    if MARKER not in content:
        backup(TARGET_BOT)
        # Insertar helper tras imports de datetime
        if "from datetime import datetime" in content:
            content = content.replace(
                "from datetime import datetime",
                "from datetime import datetime\n" + HELPER_BLOCK,
                1,
            )
            changed = True
        else:
            # insertar al inicio tras docstring
            content = HELPER_BLOCK + "\n" + content
            changed = True
    else:
        log("[OK] Bot ya tiene helper de zona Mexico", "g")

    # Reemplazar bloque REPORT_TZ_ESTADO_V1 o datetime.now del /estado
    estado_new = (
        "now = now_mexico_str()  # FIX INCORRECT TIMEZONE V2"
    )

    # Variante V1 (multi-linea)
    v1_pattern = re.compile(
        r"# REPORT_TZ_ESTADO_V1\n"
        r"    try:\n"
        r"        from zoneinfo import ZoneInfo\n"
        r"        _tz = ZoneInfo\('America/Mexico_City'\)\n"
        r"        now = datetime\.now\(_tz\)\.strftime\('%Y-%m-%d %H:%M:%S'\) \+ ' \(Mexico\)'\n"
        r"    except Exception:\n"
        r"        from datetime import timezone, timedelta\n"
        r"        _tz = timezone\(timedelta\(hours=-6\)\)\n"
        r"        now = datetime\.now\(_tz\)\.strftime\('%Y-%m-%d %H:%M:%S'\) \+ ' \(Mexico UTC-6\)'",
        re.MULTILINE,
    )
    if v1_pattern.search(content):
        content = v1_pattern.sub(estado_new, content, count=1)
        changed = True
        log("[OK] /estado actualizado a now_mexico_str()", "g")
    elif 'now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")' in content:
        content = content.replace(
            'now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")',
            estado_new,
            1,
        )
        changed = True
        log("[OK] /estado parcheado a hora Mexico", "g")
    elif "now = now_mexico_str()" in content:
        log("[OK] /estado ya usa now_mexico_str()", "g")
    else:
        log("[AVISO] No se encontro bloque /estado tipico", "y")

    # Timestamps de archivos de log
    old_ts = 'timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")'
    new_ts = 'timestamp = now_mexico().strftime("%Y-%m-%d_%H-%M-%S")  # FIX INCORRECT TIMEZONE V2'
    if old_ts in content:
        content = content.replace(old_ts, new_ts)
        changed = True
        log("[OK] timestamps de log en hora Mexico", "g")

    # Asegurar env al inicio del proceso bot (despues de imports)
    env_force = (
        "\n# FIX INCORRECT TIMEZONE V2 — env de proceso\n"
        "os.environ.setdefault('PRINTMONITOR_TZ', 'America/Mexico_City')\n"
        "os.environ.setdefault('TZ', 'America/Mexico_City')\n"
    )
    if "os.environ.setdefault('PRINTMONITOR_TZ'" not in content and \
       'os.environ.setdefault("PRINTMONITOR_TZ"' not in content:
        # insertar despues del helper o tras import os
        if "import os" in content:
            content = content.replace("import os\n", "import os\n" + env_force, 1)
            changed = True
            log("[OK] env PRINTMONITOR_TZ forzado en bot", "g")

    if changed:
        write_text(TARGET_BOT, content)
        log("[OK] telegram_bot.py guardado", "g")
    else:
        # Asegurar marker si helper ya estaba
        if MARKER not in content:
            write_text(TARGET_BOT, content)
        log("[OK] telegram_bot.py sin cambios adicionales", "g")


# ---------------------------------------------------------------------------
# 5) Windows timezone
# ---------------------------------------------------------------------------
def set_windows_timezone():
    try:
        # Consultar actual
        proc = subprocess.run(
            ["tzutil", "/g"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        current = (proc.stdout or "").strip()
        log("  Windows TZ actual: %s" % (current or "?"), "c")
        if current == WINDOWS_TZ:
            log("[OK] Windows ya esta en %s" % WINDOWS_TZ, "g")
            return True
        proc2 = subprocess.run(
            ["tzutil", "/s", WINDOWS_TZ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc2.returncode == 0:
            log("[OK] Windows TZ → %s" % WINDOWS_TZ, "g")
            return True
        log("[AVISO] No se pudo cambiar TZ de Windows (ejecute como Admin): %s"
            % ((proc2.stderr or proc2.stdout or "").strip()[:200]), "y")
        return False
    except Exception as exc:
        log("[AVISO] tzutil: %s" % exc, "y")
        return False


# ---------------------------------------------------------------------------
# 6) tzdata (Python zoneinfo en Windows)
# ---------------------------------------------------------------------------
def ensure_tzdata():
    try:
        import zoneinfo  # noqa: F401
        from zoneinfo import ZoneInfo
        ZoneInfo(IANA_TZ)
        log("[OK] zoneinfo + %s disponible" % IANA_TZ, "g")
        return True
    except Exception:
        pass
    try:
        log("  Instalando paquete tzdata...", "c")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "tzdata"],
            capture_output=True,
            timeout=120,
        )
        from zoneinfo import ZoneInfo
        ZoneInfo(IANA_TZ)
        log("[OK] tzdata instalado", "g")
        return True
    except Exception as exc:
        log("[AVISO] tzdata no disponible; se usara UTC-6 fijo: %s" % exc, "y")
        return False


# ---------------------------------------------------------------------------
# 7) Reiniciar bot
# ---------------------------------------------------------------------------
def restart_bot():
    # Tarea programada clasica
    for task in ("PrintMonitor_TelegramBot", "PrintMonitor_Bot", "PrintMonitor"):
        try:
            subprocess.run(
                ["schtasks", "/End", "/TN", task],
                capture_output=True,
                timeout=20,
            )
            subprocess.run(
                ["schtasks", "/Run", "/TN", task],
                capture_output=True,
                timeout=20,
            )
        except Exception:
            pass

    # stop via detener_bot + start
    detener = os.path.join(ROOT, "bot", "detener_bot.bat")
    start = os.path.join(ROOT, "bot", "start_bot.bat")
    try:
        if os.path.isfile(detener):
            subprocess.run(
                ["cmd", "/c", detener],
                capture_output=True,
                timeout=30,
                cwd=os.path.join(ROOT, "bot"),
            )
        # No lanzar start_bot con splash interactivo en silencio;
        # intentar proceso python del bot directamente
        bot_py = TARGET_BOT
        if os.path.isfile(bot_py):
            # matar instancias previas por pid file
            pid_file = os.path.join(ROOT, "logs", "bot.pid")
            if os.path.isfile(pid_file):
                try:
                    pid = int(read_text(pid_file).strip().split()[0])
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/F"],
                        capture_output=True,
                        timeout=15,
                    )
                except Exception:
                    pass
            env = os.environ.copy()
            env["PRINTMONITOR_TZ"] = IANA_TZ
            env["TZ"] = IANA_TZ
            env["REPORT_TZ"] = IANA_TZ
            subprocess.Popen(
                [sys.executable, bot_py],
                cwd=os.path.join(ROOT, "bot"),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            log("[OK] Bot reiniciado con TZ Mexico", "g")
            return
    except Exception as exc:
        log("[AVISO] reinicio bot: %s — reinicie manualmente" % exc, "y")
        if os.path.isfile(start):
            log("  Ejecute: %s" % start, "c")


# ---------------------------------------------------------------------------
# 8) Copiar update a PrintMonitor\updates + log
# ---------------------------------------------------------------------------
def install_as_update():
    dest = os.path.join(UPDATES_DIR, UPDATE_NAME)
    try:
        shutil.copy2(os.path.abspath(__file__), dest)
        log("[OK] Copia en updates: %s" % dest, "g")
    except Exception as exc:
        log("[AVISO] no se copio a updates: %s" % exc, "y")

    # Marcar aplicado
    try:
        existing = ""
        if os.path.isfile(APPLIED_LOG):
            existing = read_text(APPLIED_LOG)
        if UPDATE_NAME not in existing and "fix_incorrect_timezone" not in existing:
            with open(APPLIED_LOG, "a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write("%s\n" % UPDATE_NAME)
            log("[OK] Registrado en applied_updates.log", "g")
        else:
            log("[OK] Ya estaba en applied_updates.log", "g")
    except Exception as exc:
        log("[AVISO] applied log: %s" % exc, "y")


# ---------------------------------------------------------------------------
# 9) Diagnostico
# ---------------------------------------------------------------------------
def diagnose():
    log("")
    log("--- DIAGNOSTICO ---", "c")
    try:
        from datetime import datetime, timezone, timedelta
        try:
            from zoneinfo import ZoneInfo
            mx = datetime.now(ZoneInfo(IANA_TZ))
            log("  Mexico now : %s" % mx.strftime("%Y-%m-%d %H:%M:%S %z"))
        except Exception:
            mx = datetime.now(timezone(timedelta(hours=UTC_OFFSET_HOURS)))
            log("  Mexico now : %s (fallback UTC-6)" % mx.strftime("%Y-%m-%d %H:%M:%S"))
        log("  Local now  : %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        log("  UTC now    : %s" % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        log("  ENV TZ     : %s" % os.environ.get("PRINTMONITOR_TZ", "(no set)"))
        if os.path.isfile(TARGET_TZ_ENV):
            log("  timezone.env: %s" % read_text(TARGET_TZ_ENV).replace("\n", " | ").strip())
    except Exception as exc:
        log("  diagnostico: %s" % exc, "y")
    log("-------------------", "c")
    log("")


def main():
    print("")
    print("==========================================")
    print("  PRINTMONITOR FIX INCORRECT TIME ZONE")
    print("  Marker: %s" % MARKER)
    print("  Zona:   %s (UTC%+d)" % (IANA_TZ, UTC_OFFSET_HOURS))
    print("==========================================")
    print("")

    if not os.path.isdir(ROOT):
        log("ERROR: No existe %s" % ROOT, "r")
        log("Instale PrintMonitor antes de aplicar este fix.", "r")
        return 1

    ensure_dirs()

    log("1/7  timezone.env", "c")
    write_timezone_env()

    log("2/7  _env.bat", "c")
    patch_env_bat()

    log("3/7  generate_report.py", "c")
    patch_generate_report()

    log("4/7  telegram_bot.py", "c")
    patch_telegram_bot()

    log("5/7  Windows timezone", "c")
    set_windows_timezone()

    log("6/7  tzdata / zoneinfo", "c")
    ensure_tzdata()

    log("7/7  registrar update + reiniciar bot", "c")
    install_as_update()
    restart_bot()

    diagnose()

    log("FIX INSTALADO CORRECTAMENTE", "g")
    log("Pruebe: /estado  y  /reporte", "c")
    print("")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("ERROR FATAL: %s" % exc)
        raise SystemExit(1)
