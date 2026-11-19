# Preguntas Abiertas

Las preguntas del discovery (reactivación de productos, fecha de orden, tipo de clave Supabase, mecanismo de sesión) ya fueron resueltas: ver SU-03, DD-08, DD-05 y DD-04. Cambio de framework Flask a FastAPI resuelto el 2026-11-19 (DD-03, DD-11); pendiente de definir en el Paso 6: servir `static/` con `StaticFiles` y/o ruteo estático de `vercel.json`. Resueltas también el 2026-11-19: contraseña del admin (DD-07), seed por script Python (IN-01), producto repetido en orden (RN-OR-11) y reintegro a producto inactivo (RN-OR-12).

## Inconsistencias detectadas

### IN-01 — Seed del admin en `schema.sql` vs hashing PBKDF2
**Documento A dice**: Paso 5 pide un `schema.sql` con el usuario `admin` inicial.
**Documento B dice**: las contraseñas se hashean con PBKDF2-HMAC-SHA256 con salt (RN-AU-02) y PostgreSQL no lo calcula de forma nativa.
**Impacto**: un `INSERT` del admin en SQL puro obligaría a hardcodear un hash en el repositorio.
**Resolución (confirmada por el usuario 2026-11-19)**: `schema.sql` crea solo estructura y funciones; el admin se inserta con un script Python de seed que reutiliza `security.py` y lee `ADMIN_DEFAULT_PASSWORD` (DD-07).

### IN-02 — "Todo borrado requiere confirmación" vs API REST
**Documento A dice**: todo borrado se confirma (CLI `s/n`, web modal).
**Documento B dice**: la API es stateless y no tiene paso de confirmación propio.
**Impacto**: un `DELETE` directo a la API saltea la confirmación.
**Resolución propuesta**: la confirmación es responsabilidad del adaptador (UI); la API recibe el parámetro explícito `reintegrar` y se asume cliente confiable (usuarios autenticados).

## Preguntas abiertas (priorizadas)

| ID | Prioridad | Pregunta | Bloquea | Decisor |
|----|-----------|----------|---------|---------|
| PA-03 | Media | ¿Cómo se darán de alta usuarios adicionales y cómo se cambia la contraseña de `admin`? (fuera de v1 por ahora) | Paso 5 / posterior | Usuario |
| PA-04 | Media | ¿Se quiere una vista para consultar el historial de `movimientos` (hoy solo se registra)? | Paso 5 | Usuario |
| PA-06 | Baja | ¿El `numero` de orden es numérico o alfanumérico (p. ej. `OT-0001`)? | Paso 3 | Usuario |
| PA-07 | Baja | ¿Se habilita RLS sin políticas como defensa extra sobre Supabase? | Paso 5 | Equipo técnico |
| PA-08 | Baja | ¿Cuántos usuarios y qué volumen de productos/órdenes se esperan (para dimensionar paginación del listado)? | Paso 5 | Usuario |
