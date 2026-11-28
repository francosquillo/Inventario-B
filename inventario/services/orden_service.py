"""Alta de ordenes de trabajo: validacion, normalizacion y consolidacion de componentes."""
from typing import NamedTuple

from inventario.domain.chequeo_final import NOMBRES_CHEQUEO_FINAL
from inventario.domain.entities import ChequeoFinal, DatosOrden, ProcesoOrden, ServicioOrden
from inventario.domain.errors import DatosInvalidos, OrdenNoEncontrada
from inventario.domain.tiempo import ahora_argentina
from inventario.services.fechas import parsear_fecha, parsear_filtro_fecha, validar_rango
from inventario.services.normalizacion import (
    MENSAJE_NOMBRE_PROCESO_LARGO,
    MENSAJE_PRECIO,
    PROCESO_NOMBRE_MAX,
    normalizar_codigo,
    normalizar_texto_opcional,
    validar_cantidad,
    validar_celular,
    validar_precio,
)

NUMERO_MAX = 30
COMPONENTES_MAX = 100
MENSAJE_NUMERO_OBLIGATORIO = "El campo numero es obligatorio."
MENSAJE_NUMERO_LARGO = f"El campo numero admite hasta {NUMERO_MAX} caracteres."
MENSAJE_NUMERO_TIPO = "El campo numero debe ser texto."
MENSAJE_FECHA_OBLIGATORIA = "El campo fecha es obligatorio."
MENSAJE_FECHA_FORMATO = "La fecha debe tener formato AAAA-MM-DD."
MENSAJE_FECHA_INVALIDA = "La fecha ({valor}) no es una fecha válida."
MENSAJE_COMPONENTES_OBLIGATORIO = "El campo componentes es obligatorio."
MENSAJE_COMPONENTES_TIPO = "El campo componentes debe ser una lista."
MENSAJE_SIN_COMPONENTES = "La orden requiere al menos un componente."
MENSAJE_DEMASIADOS = f"La orden admite hasta {COMPONENTES_MAX} componentes."
MENSAJE_REINTEGRAR_OBLIGATORIO = "El campo reintegrar es obligatorio."
MENSAJE_REINTEGRAR_VALOR = "El campo reintegrar debe ser true o false."
MENSAJE_LINEA_TIPO = "debe ser un objeto con codigo y cantidad."
CLIENTE_MAX = 80
EMBARCACION_MAX = 60
MENSAJE_CLIENTE_LARGO = f"El cliente admite hasta {CLIENTE_MAX} caracteres."
MENSAJE_PRECIO_SERVICIO = (
    "El precio del servicio general" + MENSAJE_PRECIO.removeprefix("El precio")
)
MENSAJE_PRECIO_SIN_SERVICIO = (
    "No se puede indicar el precio del servicio general sin elegir uno."
)
MENSAJE_FECHA_EGRESO_ANTERIOR = "La fecha de egreso no puede ser anterior a la de ingreso."
PERSONALIZADOS_MAX = 10
CLAVE_ERROR_MAX = 30
MENSAJE_PROCESOS_TIPO = "El campo procesos debe ser una lista de textos."
MENSAJE_PERSONALIZADOS_TIPO = "El campo procesos_personalizados debe ser una lista de textos."
MENSAJE_SERVICIO_TIPO = "El campo servicio debe ser texto."
MENSAJE_CHEQUEO_TIPO = "El campo chequeo_final debe ser una lista de claves."
MENSAJE_NUMERO_INMUTABLE = "El número de la orden no se puede cambiar."
MENSAJE_CONSERVAR_TIPO = "El campo conservar_servicio debe ser true o false."
MENSAJE_CONSERVAR_Y_ELEGIR = (
    "No se puede elegir un servicio general y conservar el actual a la vez."
)
MENSAJE_PERSONALIZADOS_DEMASIADOS = (
    f"La orden admite hasta {PERSONALIZADOS_MAX} procesos personalizados."
)


def _normalizar_numero(numero):
    if numero is None or (isinstance(numero, str) and not numero.strip()):
        raise DatosInvalidos(MENSAJE_NUMERO_OBLIGATORIO)
    if not isinstance(numero, str):
        raise DatosInvalidos(MENSAJE_NUMERO_TIPO)
    numero = numero.strip().upper()
    if len(numero) > NUMERO_MAX:
        raise DatosInvalidos(MENSAJE_NUMERO_LARGO)
    return numero


def _normalizar_numero_filtro(numero):
    """Filtro opcional: None o en blanco -> sin filtro; si no, la misma normalizacion del alta."""
    if numero is None or (isinstance(numero, str) and not numero.strip()):
        return None
    return _normalizar_numero(numero)


def _parsear_reintegrar(reintegrar):
    """Solo "true"/"false" exactos (minusculas); un bool de Python pasa tal cual."""
    if isinstance(reintegrar, bool):
        return reintegrar
    if reintegrar is None or (isinstance(reintegrar, str) and reintegrar == ""):
        raise DatosInvalidos(MENSAJE_REINTEGRAR_OBLIGATORIO)
    if reintegrar == "true":
        return True
    if reintegrar == "false":
        return False
    raise DatosInvalidos(MENSAJE_REINTEGRAR_VALOR)


def _parsear_fecha(fecha):
    if fecha is None or fecha == "":
        raise DatosInvalidos(MENSAJE_FECHA_OBLIGATORIA)
    return parsear_fecha(fecha, MENSAJE_FECHA_FORMATO, MENSAJE_FECHA_INVALIDA)


def _parsear_fecha_opcional(valor, etiqueta):
    """Fecha de ingreso/egreso: None o blanco = None; si no, AAAA-MM-DD real."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    return parsear_fecha(
        valor,
        f"La fecha de {etiqueta} debe tener formato AAAA-MM-DD.",
        f"La fecha de {etiqueta} ({{valor}}) no es una fecha válida.",
    )


def _validar_datos(datos):
    """`datos` (dict o None) -> DatosOrden; prioridad: ingreso, egreso, cliente, celular, casco..."""
    datos = datos or {}
    ingreso = _parsear_fecha_opcional(datos.get("fecha_ingreso"), "ingreso")
    egreso = _parsear_fecha_opcional(datos.get("fecha_egreso"), "egreso")
    if ingreso is not None and egreso is not None and egreso < ingreso:
        raise DatosInvalidos(MENSAJE_FECHA_EGRESO_ANTERIOR)
    cliente = normalizar_texto_opcional(
        datos.get("cliente"), "cliente", CLIENTE_MAX, MENSAJE_CLIENTE_LARGO
    )
    celular = validar_celular(datos.get("celular"))
    embarcacion = {
        campo: normalizar_texto_opcional(
            datos.get(campo), campo, EMBARCACION_MAX,
            f"El campo {campo} admite hasta {EMBARCACION_MAX} caracteres.",
        )
        for campo in ("casco", "motor", "trailer")
    }
    return DatosOrden(
        cliente=cliente, celular=celular, fecha_ingreso=ingreso, fecha_egreso=egreso, **embarcacion
    )


def _validar_linea(posicion, linea):
    """Devuelve (codigo, cantidad, precio) validados; el error lleva el numero de linea (desde 1)."""
    try:
        if not isinstance(linea, (tuple, list)) or len(linea) not in (2, 3):
            raise DatosInvalidos(MENSAJE_LINEA_TIPO)
        codigo, cantidad = linea[0], linea[1]
        precio = linea[2] if len(linea) == 3 else None
        return normalizar_codigo(codigo), validar_cantidad(cantidad), validar_precio(precio)
    except DatosInvalidos as exc:
        raise DatosInvalidos(f"Componente {posicion}: {exc}") from None


def _consolidar(componentes):
    """Valida cada linea y suma las repetidas, en orden de primera aparicion.

    El tope de 10.000 rige por linea; el total consolidado solo lo limita el stock.
    """
    if componentes is None:
        raise DatosInvalidos(MENSAJE_COMPONENTES_OBLIGATORIO)
    if not isinstance(componentes, (list, tuple)):
        raise DatosInvalidos(MENSAJE_COMPONENTES_TIPO)
    if not componentes:
        raise DatosInvalidos(MENSAJE_SIN_COMPONENTES)
    if len(componentes) > COMPONENTES_MAX:
        raise DatosInvalidos(MENSAJE_DEMASIADOS)
    totales = {}
    for posicion, linea in enumerate(componentes, start=1):
        codigo, cantidad, precio = _validar_linea(posicion, linea)
        anterior, importe = totales.get(codigo, (0, None))
        if precio is not None:  # el importe consolidado suma solo los indicados
            importe = (importe or 0) + precio
        totales[codigo] = (anterior + cantidad, importe)
    return [(codigo, cantidad, importe) for codigo, (cantidad, importe) in totales.items()]


def _lista_de_textos(valor, mensaje):
    """None -> []; si no es lista (o tupla) de str, DatosInvalidos con `mensaje`."""
    if valor is None:
        return []
    if not isinstance(valor, (list, tuple)) or not all(isinstance(v, str) for v in valor):
        raise DatosInvalidos(mensaje)
    return list(valor)


def _recortar(clave):
    return clave if len(clave) <= CLAVE_ERROR_MAX else clave[:CLAVE_ERROR_MAX] + "…"


def _resolver_servicio(servicio, precio, repo):
    """Clave del catalogo -> ServicioOrden (snapshot de nombre, chequeos y precio); vacio/None = sin servicio."""
    sin_servicio = servicio is None or (isinstance(servicio, str) and not servicio.strip())
    if servicio is not None and not isinstance(servicio, str):
        raise DatosInvalidos(MENSAJE_SERVICIO_TIPO)
    if sin_servicio:
        # El precio solo tiene sentido con servicio; un precio malformado igual se informa como precio.
        validar_precio(precio, MENSAJE_PRECIO_SERVICIO)
        if precio is not None:
            raise DatosInvalidos(MENSAJE_PRECIO_SIN_SERVICIO)
        return None
    clave = servicio.strip().lower()
    encontrado = repo.obtener(clave)
    if encontrado is None:
        raise DatosInvalidos(f"El servicio general '{_recortar(clave)}' no existe.")
    return ServicioOrden(
        encontrado.nombre, tuple(encontrado.chequeos), validar_precio(precio, MENSAJE_PRECIO_SERVICIO)
    )


def _elementos(valor, mensaje, campo_nombre):
    """None -> []; lista de textos u objetos {campo_nombre, precio?} -> [(texto, precio_crudo)]."""
    if valor is None:
        return []
    if not isinstance(valor, (list, tuple)):
        raise DatosInvalidos(mensaje)
    elementos = []
    for v in valor:
        if isinstance(v, str):
            elementos.append((v, None))
        elif (
            isinstance(v, dict)
            and isinstance(v.get(campo_nombre), str)
            and set(v) <= {campo_nombre, "precio"}
        ):
            elementos.append((v[campo_nombre], v.get("precio")))
        else:
            raise DatosInvalidos(mensaje)
    return elementos


def _precio_de(prefijo, posicion, precio):
    try:
        return validar_precio(precio)
    except DatosInvalidos as exc:
        raise DatosInvalidos(f"{prefijo} {posicion}: {exc}") from None


def _resolver_procesos(procesos, catalogo):
    """Claves del catalogo -> ProcesoOrden (sin repetir, primera aparicion con su precio)."""
    elementos = _elementos(procesos, MENSAJE_PROCESOS_TIPO, "clave")
    por_clave = {p.clave: p.nombre for p in catalogo}
    resueltos = {}
    for posicion, (texto, precio) in enumerate(elementos, start=1):
        clave = texto.strip().lower()
        precio = _precio_de("Proceso", posicion, precio)
        if clave not in resueltos:
            resueltos[clave] = precio
    for clave in resueltos:
        if clave not in por_clave:
            raise DatosInvalidos(f"El proceso '{_recortar(clave)}' no existe.")
    return [ProcesoOrden(por_clave[clave], False, precio) for clave, precio in resueltos.items()]


def _validar_personalizados(personalizados, catalogo):
    """Textos libres: recortados, 1-60 caracteres, sin repetir ni coincidir con el catalogo."""
    textos = _elementos(personalizados, MENSAJE_PERSONALIZADOS_TIPO, "nombre")
    if len(textos) > PERSONALIZADOS_MAX:
        raise DatosInvalidos(MENSAJE_PERSONALIZADOS_DEMASIADOS)
    del_catalogo = {p.nombre.casefold() for p in catalogo}
    vistos = set()
    validos = []
    for posicion, (texto, precio) in enumerate(textos, start=1):
        nombre = texto.strip()
        if not nombre:
            raise DatosInvalidos(f"Proceso personalizado {posicion}: El nombre es obligatorio.")
        if len(nombre) > PROCESO_NOMBRE_MAX:
            raise DatosInvalidos(f"Proceso personalizado {posicion}: {MENSAJE_NOMBRE_PROCESO_LARGO}")
        clave = nombre.casefold()
        if clave in del_catalogo:
            raise DatosInvalidos(
                f"Proceso personalizado {posicion}: '{nombre}' ya está en la lista de procesos; "
                "marcalo ahí."
            )
        if clave in vistos:
            raise DatosInvalidos(f"Proceso personalizado {posicion}: '{nombre}' está repetido.")
        vistos.add(clave)
        validos.append(
            ProcesoOrden(nombre, True, _precio_de("Proceso personalizado", posicion, precio))
        )
    return validos


def _resolver_chequeo_final(chequeo_final):
    """Claves de la lista fija (texto u objeto {clave, precio}) -> ChequeoFinal, sin repetir."""
    elementos = _elementos(chequeo_final, MENSAJE_CHEQUEO_TIPO, "clave")
    vistos = {}
    for posicion, (texto, precio) in enumerate(elementos, start=1):
        clave = texto.strip().lower()
        precio = _precio_de("Chequeo final", posicion, precio)
        if clave not in NOMBRES_CHEQUEO_FINAL:
            raise DatosInvalidos(f"El ítem de chequeo final '{_recortar(clave)}' no existe.")
        if clave in vistos:
            raise DatosInvalidos(f"Chequeo final {posicion}: '{clave}' está repetido.")
        vistos[clave] = ChequeoFinal(clave, NOMBRES_CHEQUEO_FINAL[clave], precio)
    return tuple(vistos.values())


def _parsear_conservar(valor):
    """Solo bool (o ausente = False); cualquier otro valor es un error."""
    if valor is None:
        return False
    if isinstance(valor, bool):
        return valor
    raise DatosInvalidos(MENSAJE_CONSERVAR_TIPO)


class ContenidoOrden(NamedTuple):
    """Contenido de una orden ya validado (alta y edicion)."""

    fecha: object
    items: list
    datos: DatosOrden
    servicio: "ServicioOrden | None"
    procesos: tuple
    chequeo_final: tuple


class OrdenService:
    def __init__(self, orden_repo, proceso_repo, servicio_repo, ahora=ahora_argentina):
        self._repo = orden_repo
        self._procesos = proceso_repo
        self._servicios = servicio_repo
        self._ahora = ahora

    def _validar_contenido(
        self, fecha, componentes, datos, servicio, precio_servicio, procesos,
        procesos_personalizados, chequeo_final, conservar_servicio=False,
    ):
        """Validacion compartida por el alta y la edicion (prioridad de design D4)."""
        f_orden = _parsear_fecha(fecha)
        datos_orden = _validar_datos(datos)
        items = _consolidar(componentes)
        if conservar_servicio:
            servicio_orden = self._servicio_a_conservar(servicio, precio_servicio)
        else:
            servicio_orden = _resolver_servicio(servicio, precio_servicio, self._servicios)
        catalogo = self._procesos.listar()
        todos = _resolver_procesos(procesos, catalogo) + _validar_personalizados(
            procesos_personalizados, catalogo
        )
        return ContenidoOrden(
            f_orden, items, datos_orden, servicio_orden, tuple(todos),
            _resolver_chequeo_final(chequeo_final),
        )

    @staticmethod
    def _servicio_a_conservar(servicio, precio):
        """Con `conservar_servicio` solo importa el precio; el repo reutiliza nombre y chequeos."""
        if servicio is not None and not isinstance(servicio, str):
            raise DatosInvalidos(MENSAJE_SERVICIO_TIPO)
        nuevo_precio = validar_precio(precio, MENSAJE_PRECIO_SERVICIO)
        if servicio is not None and servicio.strip():
            raise DatosInvalidos(MENSAJE_CONSERVAR_Y_ELEGIR)
        return ServicioOrden("", (), nuevo_precio)

    def crear(
        self,
        numero,
        fecha,
        componentes,
        usuario_id,
        procesos=None,
        procesos_personalizados=None,
        servicio=None,
        datos=None,
        precio_servicio=None,
        chequeo_final=None,
    ):
        numero = _normalizar_numero(numero)
        c = self._validar_contenido(
            fecha, componentes, datos, servicio, precio_servicio, procesos,
            procesos_personalizados, chequeo_final,
        )
        return self._repo.crear(
            numero,
            c.fecha,
            c.items,
            usuario_id,
            self._ahora(),
            procesos=c.procesos,
            servicio=c.servicio,
            datos=c.datos,
            chequeo_final=c.chequeo_final,
        )

    def editar(
        self,
        numero,
        fecha,
        componentes,
        procesos=None,
        procesos_personalizados=None,
        servicio=None,
        datos=None,
        precio_servicio=None,
        chequeo_final=None,
        conservar_servicio=None,
        numero_cuerpo=None,
    ):
        """Reemplaza el contenido de la orden `numero` (el del cuerpo, si viene, se rechaza)."""
        numero = _normalizar_numero(numero)
        if numero_cuerpo is not None:
            raise DatosInvalidos(MENSAJE_NUMERO_INMUTABLE)
        conservar = _parsear_conservar(conservar_servicio)
        c = self._validar_contenido(
            fecha, componentes, datos, servicio, precio_servicio, procesos,
            procesos_personalizados, chequeo_final, conservar,
        )
        return self._repo.editar(
            numero, c.fecha, c.items, c.procesos, c.servicio, c.datos, c.chequeo_final, conservar
        )

    def listar(self, numero=None, desde=None, hasta=None):
        numero = _normalizar_numero_filtro(numero)
        f_desde = parsear_filtro_fecha("desde", desde)
        f_hasta = parsear_filtro_fecha("hasta", hasta)
        validar_rango(desde, hasta, f_desde, f_hasta)
        ordenes = self._repo.listar(numero, f_desde, f_hasta)
        # Vacio con numero: 404 solo si el numero no existe; si existe, quedo fuera del rango.
        if not ordenes and numero is not None and not self._repo.existe_numero(numero):
            raise OrdenNoEncontrada(numero)
        return ordenes

    def borrar(self, numero, reintegrar):
        # Primero gana el error de `reintegrar`; luego el de `numero`; el 404 lo da el repo.
        valor = _parsear_reintegrar(reintegrar)
        numero = _normalizar_numero(numero)
        return self._repo.borrar(numero, valor)
