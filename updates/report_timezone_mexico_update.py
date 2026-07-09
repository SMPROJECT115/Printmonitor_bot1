# -*- coding: utf-8 -*-
"""
Update: corrige zona horaria del reporte PDF.
Fuerza America/Mexico_City (Hora del Centro de Mexico / UTC-6).

- Reemplaza C:\\PrintMonitor\\python\\generate_report.py
- Escribe C:\\PrintMonitor\\.secure\\timezone.env
- Ajusta /estado del bot para mostrar hora Mexico

Idempotente (marker REPORT TIMEZONE FIX V1).
"""

from __future__ import print_function

import os
import shutil
import sys
import time

MARKER = "REPORT TIMEZONE FIX V1"
TARGET_REPORT = r"C:\PrintMonitor\python\generate_report.py"
TARGET_TZ_ENV = r"C:\PrintMonitor\.secure\timezone.env"
TARGET_BOT = r"C:\PrintMonitor\bot\telegram_bot.py"
BACKUP_DIR = r"C:\PrintMonitor\logs\backups"


# Contenido completo del generador (misma version que python/generate_report.py del paquete)
# Se carga desde el propio archivo embebido abajo si no hay copia junto al update.
def _embedded_generate_report():
    # Preferir copia del paquete instalador / updates sibling
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python", "generate_report.py"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_report_tz.py"),
        r"C:\PrintMonitor\python\generate_report.py",
    ]
    for path in candidates:
        path = os.path.normpath(path)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
                if MARKER in text or "America/Mexico_City" in text:
                    return text
            except Exception:
                pass
    return GENERATE_REPORT_SOURCE


GENERATE_REPORT_SOURCE = r'''# -*- coding: utf-8 -*-
"""Genera reporte PDF desde logs CSV de PaperCut Print Logger.

Zona horaria: America/Mexico_City (Hora del Centro de Mexico, UTC-6).
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
# =====================================================
DEFAULT_TZ_NAME = "America/Mexico_City"
TZ_ENV_FILE = r"C:\PrintMonitor\.secure\timezone.env"
CSV_FOLDERS = (
    r"C:\Program Files (x86)\PaperCut Print Logger\logs\csv\daily",
    r"C:\Program Files\PaperCut Print Logger\logs\csv\daily",
    r"C:\Program Files (x86)\PaperCut Print Logger\logs\csv",
    r"C:\Program Files\PaperCut Print Logger\logs\csv",
)
OUTPUT_FOLDER = r"C:\PrintMonitor\reports\pdf"


def _read_tz_name():
    env = (os.environ.get("PRINTMONITOR_TZ") or "").strip()
    if env:
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
    name = _read_tz_name()
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name), name
    except Exception:
        pass
    try:
        import pytz
        return pytz.timezone(name), name
    except Exception:
        pass
    return timezone(timedelta(hours=-6)), name + " (UTC-6 fijo)"


REPORT_TZ, REPORT_TZ_LABEL = get_report_tz()


def now_local():
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
    text = (raw or "").strip().strip('"')
    if not text:
        return None
    if text.endswith("Z") and "T" in text:
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.astimezone(REPORT_TZ)
        except Exception:
            pass
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
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M",
        "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S",
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
    names = ("%s.csv" % report_date, "papercut-print-log-%s.csv" % report_date)
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
                "dt": None, "hora": hora,
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
            "dt": dt, "hora": format_time_local(dt),
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


def load_rows_for_date_unfiltered(csv_file):
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
            "dt": dt, "hora": hora,
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
        pdf_path, pagesize=letter,
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<font size='22'><b>PRINTMONITOR ENTERPRISE</b></font>", styles["Title"]),
        Spacer(1, 10),
        Paragraph("<font size='12'><b>Fecha del reporte:</b> %s</font>" % report_date, styles["BodyText"]),
        Paragraph("<font size='10'><b>Zona horaria:</b> %s</font>" % REPORT_TZ_LABEL, styles["BodyText"]),
        Paragraph("<font size='10'><b>Generado:</b> %s</font>" % format_datetime_local(now_local()), styles["BodyText"]),
        Spacer(1, 12),
    ]
    table_data = [["Hora", "Usuario", "Paginas", "Copias", "Impresora", "Documento", "Cliente", "Frente/Reverso", "Escala"]]
    for item in data_rows:
        table_data.append([
            item["hora"], item["usuario"], item["paginas"], item["copias"],
            item["impresora"], item["documento"], item["cliente"], item["duplex"], item["escala"],
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


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _backup(path):
    if not os.path.isfile(path):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = os.path.basename(path)
    dest = os.path.join(
        BACKUP_DIR,
        "%s.bak_%s" % (name, time.strftime("%Y%m%d_%H%M%S")),
    )
    try:
        shutil.copy2(path, dest)
        print("Backup: %s" % dest)
    except Exception as exc:
        print("[AVISO] backup: %s" % exc)


def patch_bot_estado():
    """Muestra hora Mexico en /estado si el bot existe."""
    if not os.path.isfile(TARGET_BOT):
        return
    with open(TARGET_BOT, "r", encoding="utf-8", errors="ignore") as handle:
        content = handle.read()
    if "REPORT_TZ_ESTADO_V1" in content:
        print("Bot /estado ya con zona Mexico")
        return
    old = 'now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")'
    new = (
        "# REPORT_TZ_ESTADO_V1\n"
        "    try:\n"
        "        from zoneinfo import ZoneInfo\n"
        "        _tz = ZoneInfo('America/Mexico_City')\n"
        "        now = datetime.now(_tz).strftime('%Y-%m-%d %H:%M:%S') + ' (Mexico)'\n"
        "    except Exception:\n"
        "        from datetime import timezone, timedelta\n"
        "        _tz = timezone(timedelta(hours=-6))\n"
        "        now = datetime.now(_tz).strftime('%Y-%m-%d %H:%M:%S') + ' (Mexico UTC-6)'"
    )
    if old in content:
        _backup(TARGET_BOT)
        content = content.replace(old, new, 1)
        _write(TARGET_BOT, content)
        print("[OK] Bot /estado ajustado a hora Mexico")
    else:
        print("[AVISO] No se encontro bloque /estado tipico; se omite parche bot")


def main():
    print("")
    print("===================================")
    print("UPDATE: ZONA HORARIA REPORTE (MEXICO)")
    print("===================================")
    print("")

    if os.path.isfile(TARGET_REPORT):
        with open(TARGET_REPORT, "r", encoding="utf-8", errors="ignore") as handle:
            current = handle.read()
        if MARKER in current:
            print("UPDATE YA APLICADO en generate_report.py")
            # Aun asi asegurar timezone.env
            _write(TARGET_TZ_ENV, "REPORT_TZ=America/Mexico_City\n")
            print("[OK] timezone.env OK")
            patch_bot_estado()
            print("")
            print("Listo (idempotente).")
            return 0
        _backup(TARGET_REPORT)

    source = _embedded_generate_report()
    if MARKER not in source and "America/Mexico_City" not in source:
        source = GENERATE_REPORT_SOURCE

    _write(TARGET_REPORT, source if MARKER in source or "America/Mexico_City" in source else GENERATE_REPORT_SOURCE)
    print("[OK] generate_report.py actualizado")

    _write(
        TARGET_TZ_ENV,
        "# Zona horaria de reportes PrintMonitor\n"
        "# Ejemplos: America/Mexico_City | America/Tijuana | America/Cancun\n"
        "REPORT_TZ=America/Mexico_City\n",
    )
    print("[OK] %s" % TARGET_TZ_ENV)

    patch_bot_estado()

    # Probar import basico
    try:
        import runpy
        # no ejecutar main
        print("[OK] Archivo escrito: %s" % TARGET_REPORT)
    except Exception:
        pass

    print("")
    print("Reinicie el bot y genere /reporte con fecha YYYY-MM-DD")
    print("Las horas del PDF usaran America/Mexico_City (UTC-6).")
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
