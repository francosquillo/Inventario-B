"""Fuente de tiempo del dominio: hora local de Argentina con offset fijo (sin zoneinfo)."""
from datetime import datetime, timedelta, timezone

# Argentina no tiene horario de verano; evita depender de `tzdata` en Windows.
ZONA_AR = timezone(timedelta(hours=-3), "ART")


def ahora_argentina():
    """Instante actual en Argentina, sin microsegundos."""
    return datetime.now(ZONA_AR).replace(microsecond=0)
