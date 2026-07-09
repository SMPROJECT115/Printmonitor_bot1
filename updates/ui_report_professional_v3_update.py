# -*- coding: utf-8 -*-
"""
Update: UI profesional v3 para mensajes Telegram (reportes y captions).
Elimina cajas ━━━━, emojis excesivos y captions poco profesionales.

Idempotente: marker UI_REPORT_PROFESSIONAL_V3
Compatible con pythonw (logs seguros).
"""

from __future__ import print_function

import os
import re
import shutil
import sys
import time

MARKER = "UI_REPORT_PROFESSIONAL_V3"
BOT = r"C:\PrintMonitor\bot\telegram_bot.py"
BACKUP = r"C:\PrintMonitor\logs\backups"
LOG = r"C:\PrintMonitor\logs\ui_v3_update.log"


def _stdio():
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
    except Exception:
        pass
    if sys.stdout is None or not hasattr(sys.stdout, "write"):
        try:
            sys.stdout = open(LOG, "a", encoding="utf-8", errors="replace")
            sys.stderr = sys.stdout
        except Exception:
            pass


_stdio()


def log(msg):
    line = "%s" % msg
    try:
        with open(LOG, "a", encoding="utf-8", errors="replace") as h:
            h.write(line + "\n")
    except Exception:
        pass
    try:
        if sys.stdout is not None:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    except Exception:
        pass


UI_HELPERS = r'''
PROGRESS_FRAMES = ("◉", "◎", "◌", "◎")
# UI Enterprise v3 — limpio, sin cajas pesadas
DIV = "────────────────────────"
DEVELOPER_ID = 8097401689
BRAND = "PrintMonitor Enterprise"
# UI_REPORT_PROFESSIONAL_V3


def _md_escape(text):
    """Escapa caracteres que rompen Markdown legacy de Telegram."""
    if text is None:
        return ""
    text = str(text)
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def user_display(user):
    """Nombre limpio + id para tarjetas."""
    if not user:
        return "Usuario desconocido", "—"
    name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or "Usuario"
    if user.username:
        name = "%s (@%s)" % (name, user.username)
    if user.id == DEVELOPER_ID:
        name = "%s · Developer" % name
    return name, str(user.id)


def card(title, body_lines=None, footer=None):
    """
    Tarjeta profesional para Telegram (Markdown).
    Sin marcos gruesos tipo ━━━━ que saturan el chat.
    """
    parts = ["*%s*" % title, DIV]
    if body_lines:
        for line in body_lines:
            if line is None:
                continue
            parts.append(line)
    if footer:
        if body_lines:
            parts.append("")
        parts.append(DIV)
        if isinstance(footer, (list, tuple)):
            parts.extend(footer)
        else:
            parts.append(footer)
    return "\n".join(parts)


def kv(label, value):
    """Fila etiqueta · valor."""
    return "*%s*  ·  %s" % (label, value)


def sep_block(*lines):
    """Compatibilidad: convierte lineas sueltas en tarjeta limpia."""
    clean = [ln for ln in lines if ln is not None]
    if not clean:
        return DIV
    title = clean[0].strip()
    if title.startswith("*") and title.endswith("*") and len(title) > 2:
        title = title[1:-1]
    body = clean[1:]
    compact = []
    prev_empty = False
    for ln in body:
        empty = (ln == "")
        if empty and prev_empty:
            continue
        compact.append(ln)
        prev_empty = empty
    while compact and compact[0] == "":
        compact.pop(0)
    while compact and compact[-1] == "":
        compact.pop()
    return card(title, compact if compact else None)


def requester_block(user):
    name, uid = user_display(user)
    return [
        "_Solicitado por_",
        _md_escape(name),
        "`%s`" % uid,
    ]


def requester_line(user):
    """Una linea compacta (compat)."""
    name, uid = user_display(user)
    return "Solicitado por  ·  %s  ·  `%s`" % (_md_escape(name), uid)


def format_requester(user):
    return card("Solicitud", requester_block(user))


def report_caption(user, report_date, status="Completado", filename=None, zone="Mexico (UTC-6)"):
    """Caption profesional del PDF de reporte."""
    body = [
        "_Reporte de impresion_",
        "",
        kv("Estado", status),
        kv("Periodo", "`%s`" % report_date),
        kv("Zona", zone),
    ]
    if filename:
        body.append(kv("Archivo", "`%s`" % filename))
    body.append("")
    body.extend(requester_block(user))
    return card(BRAND, body)


WELCOME_TEXT = card(
    BRAND,
    [
        "_Sistema de monitoreo de impresion_",
        "",
        kv("Estado", "Operativo"),
        "",
        "*Comandos*",
        "`/reporte`  —  PDF por fecha",
        "`/ultimoreporte`  —  ultimo PDF",
        "`/estado`  —  salud del sistema",
        "`/papercut`  —  servicio PaperCut",
        "`/test`  —  prueba de conexion",
        "`/log`  —  errores del sistema",
        "`/update`  —  updates remotos",
        "`/github`  —  enlace GitHub",
    ],
)

'''


def backup(path):
    os.makedirs(BACKUP, exist_ok=True)
    dest = os.path.join(
        BACKUP,
        "telegram_bot.py.bak_%s" % time.strftime("%Y%m%d_%H%M%S"),
    )
    try:
        shutil.copy2(path, dest)
        log("Backup: %s" % dest)
    except Exception as exc:
        log("Backup aviso: %s" % exc)


def main():
    log("=== UI REPORT PROFESSIONAL V3 ===")
    if not os.path.isfile(BOT):
        log("ERROR: no existe telegram_bot.py")
        return 1

    with open(BOT, "r", encoding="utf-8", errors="ignore") as h:
        content = h.read()

    if MARKER in content and "def report_caption" in content and "def card(" in content:
        log("UI V3 ya instalada")
        return 0

    backup(BOT)

    # Reemplazar bloque UI antiguo (desde PROGRESS_FRAMES hasta format_requester / WELCOME)
    patterns = [
        # desde PROGRESS_FRAMES hasta antes de def _process_running o ensure_single
        (
            r"PROGRESS_FRAMES\s*=\s*\([^\)]*\)\s*"
            r".*?"
            r"(?=def _process_running|def ensure_single_instance|def safe_send|ENV_PATH\s*=)",
            UI_HELPERS + "\n\n",
        ),
    ]

    new_content = content
    replaced = False
    for pat, repl in patterns:
        new_c, n = re.subn(pat, repl, new_content, count=1, flags=re.DOTALL)
        if n:
            new_content = new_c
            replaced = True
            log("Bloque UI reemplazado por helpers V3")
            break

    if not replaced:
        # Insertar helpers despues de imports de telebot si no hay PROGRESS_FRAMES tipico
        if "def report_caption" not in new_content:
            anchor = "DEVELOPER_ID"
            if "PROGRESS_FRAMES" in new_content:
                # forzar desde PROGRESS_FRAMES hasta WELCOME_TEXT inclusive de forma mas simple
                start = new_content.find("PROGRESS_FRAMES")
                # buscar format_requester function end
                m = re.search(
                    r"def format_requester\(user\):.*?(?=\n\ndef |\n[A-Z_]+\s*=)",
                    new_content[start:],
                    re.DOTALL,
                )
                if start >= 0 and m:
                    end = start + m.end()
                    new_content = new_content[:start] + UI_HELPERS + "\n" + new_content[end:]
                    replaced = True
                    log("Bloque UI insertado (modo B)")
            if not replaced:
                # append helpers near top after TOKEN section is risky; inject before first @bot
                idx = new_content.find("@bot.message_handler")
                if idx > 0 and "def card(" not in new_content:
                    new_content = new_content[:idx] + UI_HELPERS + "\n\n" + new_content[idx:]
                    replaced = True
                    log("Helpers inyectados antes de handlers")

    # Caption del PDF de /reporte
    old_caps = [
        '''caption=sep_block(
                "📄 *PRINTMONITOR REPORT*",
                "",
                requester_line(user),
                "",
                "✅ Reporte generado",
                "📅 Fecha: %s" % report_date,
            )''',
        '''caption=sep_block(
                "📄 *PRINTMONITOR REPORT*",
                "",
                requester_line(user),
                "",
                "✅ Reporte generado",
                "📅 Fecha: %s" % report_date,
            )''',
    ]
    new_cap = '''caption=report_caption(
                user,
                report_date,
                status="Completado",
                filename=os.path.basename(pdf_path),
            )'''
    for old in old_caps:
        if old in new_content:
            new_content = new_content.replace(old, new_cap)
            log("Caption /reporte actualizado")
            replaced = True

    # Variante compacta
    if "PRINTMONITOR REPORT" in new_content and "report_caption(" not in new_content:
        new_content = re.sub(
            r'caption=sep_block\(\s*"📄 \*PRINTMONITOR REPORT\*".*?parse_mode="Markdown",',
            'caption=report_caption(user, report_date, status="Completado", '
            'filename=os.path.basename(pdf_path)),\n            parse_mode="Markdown",',
            new_content,
            count=1,
            flags=re.DOTALL,
        )
        log("Caption /reporte actualizado (regex)")
        replaced = True

    if MARKER not in new_content:
        # asegurar marker
        new_content = new_content.replace(
            "BRAND = \"PrintMonitor Enterprise\"",
            "BRAND = \"PrintMonitor Enterprise\"\n# " + MARKER,
            1,
        )

    with open(BOT, "w", encoding="utf-8", newline="\n") as h:
        h.write(new_content)

    log("UI V3 aplicada en telegram_bot.py")
    log("Reinicie el bot o espere el soft-restart del sistema")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        log("FATAL: %s" % exc)
        raise SystemExit(0)  # no romper cadena de updates
