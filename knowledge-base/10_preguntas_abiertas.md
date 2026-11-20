# Preguntas Abiertas

Las preguntas del discovery (reactivación de productos, fecha de orden, tipo de clave Supabase, mecanismo de sesión) ya fueron resueltas: ver SU-03, DD-08, DD-05 y DD-04. Cambio de framework Flask a FastAPI resuelto el 2026-11-19 (DD-03, DD-11); pendiente de definir en el Paso 6: servir `static/` con `StaticFiles` y/o ruteo estático de `vercel.json`. Cambio de alcance 2026-11-19: se elimina la CLI y se construye FastAPI desde el Paso 1 (DD-12); las referencias a la CLI en esta KB son históricas. Resueltas también el 2026-11-19: contraseña del admin (DD-07), seed por script Python (IN-01), producto repetido en orden (RN-OR-11) y reintegro a producto inactivo (RN-OR-12). Resuelta por C-02 (2026-11-20): consulta de movimientos (PA-04), con `GET /api/movimientos` y filtros por `codigo` y `desde`/`hasta`. Resuelta por C-03 (2026-11-20): número de orden (PA-06), texto alfanumérico, sin espacios sobrantes y en mayúsculas, de 1 a 30 caracteres, único sobre el valor normalizado.

## Inconsistencias detectadas

### IN-01 — Seed del admin en `schema.sql` vs hashing PBKDF2
**Documento A dice**: Paso 5 pide un `schema.sql` con el usuario `admin` inicial.
**Documento B dice**: las contraseñas se hashean con PBKDF2-HMAC-SHA256 con salt (RN-AU-02) y PostgreSQL no lo calcula de forma nativa.
**Impacto**: un `INSERT` del admin en SQL puro obligaría a hardcodear un hash en el repositorio.
**Resolución (confirmada por el usuario 2026-11-19)**: `schema.sql` crea solo estructura y funciones; el admin se inserta con un script Python de seed que reutiliza `security.py` y lee `ADMIN_DEFAULT_PASSWORD` (DD-07).

### IN-02 — "Todo borrado requiere confirmación" vs API REST
**Documento A dice**: todo borrado se confirma (modal en la web; la CLI ya no existe, DD-12).
**Documento B dice**: la API es stateless y no tiene paso de confirmación propio.
**Impacto**: un `DELETE` directo a la API saltea la confirmación.
**Resolución propuesta**: la confirmación es responsabilidad del frontend (modal, Paso 5); en Fase 1 la verificación en `/docs` es explícita; la API recibe el parámetro explícito `reintegrar` y se asume cliente confiable (usuarios autenticados).

## Preguntas abiertas (priorizadas)

| ID | Prioridad | Pregunta | Bloquea | Decisor |
|----|-----------|----------|---------|---------|
| PA-03 | Media | ¿Cómo se darán de alta usuarios adicionales y cómo se cambia la contraseña de `admin`? (fuera de v1 por ahora) | Paso 5 / posterior | Usuario |
| PA-07 | Baja | ¿Se habilita RLS sin políticas como defensa extra sobre Supabase? | Paso 5 | Equipo técnico |
| PA-08 | Baja | ¿Cuántos usuarios y qué volumen de productos/órdenes se esperan (para dimensionar paginación del listado)? | Paso 5 | Usuario |
