"""Chequeo final de una orden: lista fija de items (C-06i, design D6)."""

CHEQUEO_FINAL = (
    ("combustible", "Combustible"),
    ("puesta-en-marcha", "Puesta en marcha"),
    ("check-list-y-verificacion-final", "Check-list y verificación final"),
    ("prueba-en-el-lago", "Prueba en el lago"),
    ("limpieza-de-cortesia", "Limpieza de cortesía"),
    ("entrega", "Entrega"),
)

CLAVES_CHEQUEO_FINAL = tuple(clave for clave, _ in CHEQUEO_FINAL)
NOMBRES_CHEQUEO_FINAL = dict(CHEQUEO_FINAL)
