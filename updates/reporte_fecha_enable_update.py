# -*- coding: utf-8 -*-
"""
Update: habilita /reporte con solicitud de fecha YYYY-MM-DD (ej: 2026-05-21).
Idempotente — no duplica si ya esta instalado.
"""

from __future__ import print_function

import os
import re
import sys

BOT_FILE = r"C:\PrintMonitor\bot\telegram_bot.py"
MARKER = "REPORTE_FECHA_YYYY_MM_DD_V1"


def _read(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def _write(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def already_enabled(content):
    return (
        MARKER in content
        or (
            "def reporte_command" in content
            and "def process_report_date" in content
            and "register_next_step_handler" in content
            and "%Y-%m-%d" in content
            and "2026-05-21" in content
        )
    )


REPORTE_BLOCK = '''

# %s
@bot.message_handler(commands=["reporte"])
def reporte_command(message):
    cleanup_command(message)
    msg = safe_send(
        message.chat.id,
        sep_block(
            "📄 *GENERAR REPORTE PDF*",
            "",
            requester_line(message.from_user),
            "",
            "📅 Envie la fecha en formato:",
            "`YYYY-MM-DD`",
            "",
            "📝 Ejemplo: `2026-05-21`",
        ),
        message,
        parse_mode="Markdown",
    )
    if msg:
        bot.register_next_step_handler(msg, lambda m: process_report_date(m, message.from_user))


def process_report_date(message, requester_user=None):
    report_date = (message.text or "").strip()

    try:
        datetime.strptime(report_date, "%%Y-%%m-%%d")
    except ValueError:
        safe_send(
            message.chat.id,
            sep_block(
                "❌ *Fecha invalida*",
                "",
                "Use formato `YYYY-MM-DD`",
                "Ejemplo: `2026-05-21`",
            ),
            message,
            parse_mode="Markdown",
        )
        return

    user = requester_user or message.from_user
    progress_msg = safe_send(
        message.chat.id,
        sep_block(
            "🔄 *Generando reporte PDF...*",
            "",
            requester_line(user),
            "",
            "░░░░░░░░░░ 0%%",
        ),
        message,
        parse_mode="Markdown",
    )
    if not progress_msg:
        return

    def generate():
        return subprocess.run(
            [sys.executable, REPORT_SCRIPT, report_date],
            capture_output=True,
            text=True,
        )

    result = run_progress_animation(
        message.chat.id,
        progress_msg.message_id,
        "Generando reporte PDF",
        generate,
        report_date,
    )

    if result.returncode != 0:
        try:
            bot.edit_message_text(
                sep_block(
                    "❌ *Error al generar reporte*",
                    "",
                    requester_line(user),
                    "",
                    "📅 Fecha: `%%s`" %% report_date,
                    "",
                    "Detalle:",
                    "`%%s`" %% (result.stderr or result.stdout or "Error desconocido")[:500],
                ),
                message.chat.id,
                progress_msg.message_id,
                parse_mode="Markdown",
            )
        except Exception:
            safe_send(message.chat.id, "❌ Error al generar reporte", message)
        return

    pdf_path = latest_pdf()
    if not pdf_path:
        try:
            bot.edit_message_text("❌ No se genero el archivo PDF", message.chat.id, progress_msg.message_id)
        except Exception:
            pass
        return

    try:
        bot.edit_message_text(
            sep_block(
                "✅ *PDF generado correctamente*",
                "",
                requester_line(user),
                "",
                "📅 Fecha: `%%s`" %% report_date,
            ),
            message.chat.id,
            progress_msg.message_id,
            parse_mode="Markdown",
        )
    except Exception:
        pass

    time.sleep(0.5)
    with open(pdf_path, "rb") as pdf:
        bot.send_document(
            message.chat.id,
            pdf,
            caption=sep_block(
                "📄 *PRINTMONITOR REPORT*",
                "",
                requester_line(user),
                "",
                "✅ Reporte generado",
                "📅 Fecha: %%s" %% report_date,
            ),
            parse_mode="Markdown",
        )

''' % MARKER


def remove_old_reporte_blocks(content):
    patterns = [
        r"@bot\.message_handler\(commands=\[['\"]reporte['\"]\]\).*?(?=\n@bot\.message_handler|\n# =+|\Z)",
        r"def process_report_date\(.*?(?=\n@bot\.message_handler|\ndef [a-z_]+\(|\n# =+|\Z)",
    ]
    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.DOTALL)
    return content


def ensure_helpers(content):
    if "def requester_line" not in content and "def requester_lines" not in content:
        helper = '''

def requester_line(user):
    if not user:
        return "👤 *Solicitado por:* Usuario desconocido"
    uid = user.id
    name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or "Usuario"
    username = (" @%s" % user.username) if user.username else ""
    return "👤 *Solicitado por:* %s%s · 🆔 `%s`" % (name, username, uid)

'''
        anchor = "def sep_block"
        if anchor in content:
            pos = content.find(anchor)
            end = content.find("\n\n", pos)
            if end == -1:
                end = pos
            content = content[:end] + helper + content[end:]
    if "REPORT_SCRIPT" not in content:
        content = content.replace(
            'PDF_FOLDER = r"C:\\PrintMonitor\\reports\\pdf"',
            'PDF_FOLDER = r"C:\\PrintMonitor\\reports\\pdf"\n'
            'REPORT_SCRIPT = r"C:\\PrintMonitor\\python\\generate_report.py"',
        )
    return content


def main():
    if not os.path.isfile(BOT_FILE):
        print("ERROR: No existe %s" % BOT_FILE)
        return 1

    content = _read(BOT_FILE)
    if already_enabled(content):
        if MARKER not in content:
            content = content.rstrip() + "\n# %s\n" % MARKER
            _write(BOT_FILE, content)
        print("OK: /reporte con fecha YYYY-MM-DD ya habilitado")
        return 0

    content = remove_old_reporte_blocks(content)
    content = ensure_helpers(content)

    anchor = '@bot.message_handler(commands=["ultimoreporte"])'
    if anchor not in content:
        anchor = '@bot.message_handler(commands=["update"])'
    if anchor in content:
        pos = content.find(anchor)
        content = content[:pos] + REPORTE_BLOCK + "\n\n" + content[pos:]
    else:
        content = content.rstrip() + "\n" + REPORTE_BLOCK + "\n"

    _write(BOT_FILE, content)
    print("OK: /reporte habilitado — formato fecha YYYY-MM-DD (ej: 2026-05-21)")
    return 0


if __name__ == "__main__":
    sys.exit(main())