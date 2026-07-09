# PrintMonitor Bot — Updates

Repositorio de updates remotos para PrintMonitor Enterprise.

## Uso

En Telegram, dentro del grupo configurado:

```
/update
```

El bot descarga los archivos de `updates/` y los aplica en `C:\PrintMonitor`.

## Updates disponibles

| Archivo | Descripcion |
|---|---|
| `reporte_fecha_enable_update.py` | Habilita `/reporte` pidiendo fecha `YYYY-MM-DD` (ej: `2026-05-21`) |
| `report_timezone_mexico_update.py` | (V1) Fuerza America/Mexico_City en reportes PDF |
| `fix_incorrect_timezone_update.py` | **(V2.1) Fix Incorrect Time Zone** — compatible con pythonw / Python 3.x — corrige zona horaria en PDF, bot `/estado`, env y Windows |
| `ui_report_professional_v3_update.py` | UI profesional v3: captions y mensajes limpios sin cajas pesadas |

## Fix Incorrect Time Zone (V2)

Corrige horas incorrectas forzando:

- `America/Mexico_City` (UTC-06:00)
- Windows: `Central Standard Time (Mexico)`
- `C:\PrintMonitor\.secure\timezone.env`
- `generate_report.py` y `telegram_bot.py`
- Variables `PRINTMONITOR_TZ` / `TZ` en `_env.bat`

Tras `/update`, reinicie el bot si no se reinicia solo y pruebe:

```
/estado
/reporte
```

## Configuracion local

`C:\PrintMonitor\.secure\update_source.env`:

```
UPDATE_REPO_URL=https://github.com/SMPROJECT115/Printmonitor_bot1.git
UPDATE_REPO_BRANCH=main
```
