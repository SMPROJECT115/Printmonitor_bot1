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

## Configuracion local

`C:\PrintMonitor\.secure\update_source.env`:

```
UPDATE_REPO_URL=https://github.com/SMPROJECT115/Printmonitor_bot1.git
UPDATE_REPO_BRANCH=main
```