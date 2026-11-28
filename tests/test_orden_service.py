import unittest
from datetime import date, datetime

from inventario.domain.entities import AjusteStock, ChequeoFinal, Faltante, ServicioOrden
from inventario.domain.errors import (
    DatosInvalidos,
    OrdenDuplicada,
    OrdenNoEncontrada,
    ProductosNoEncontrados,
    StockInsuficienteOrden,
)
from inventario.domain.tiempo import ZONA_AR
from inventario.repositories.sqlite_repo import (
    SqliteOrdenRepository,
    SqliteProcesoRepository,
    SqliteServicioGeneralRepository,
)
from inventario.services.orden_service import OrdenService
from inventario.services.servicio_general_service import ServicioGeneralService
from tests.helpers import conexion_inicializada, insertar_producto, insertar_usuario, movimientos

FECHA_FIJA = datetime(2026, 11, 19, 15, 30, tzinfo=ZONA_AR)
MSG_CANTIDAD = "La cantidad debe ser un entero entre 1 y 10.000."


class ServiceBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_producto(self.conn, "B-02", "Tuerca", 10)
        self.service = OrdenService(
            SqliteOrdenRepository(self.conn), SqliteProcesoRepository(self.conn),
            SqliteServicioGeneralRepository(self.conn),
            ahora=lambda: FECHA_FIJA,
        )

    def crear(self, numero="OT-0001", fecha="2026-11-20", componentes=(("A-01", 1),)):
        return self.service.crear(numero, fecha, componentes, self.uid)

    def stock(self, codigo):
        return self.conn.execute(
            "SELECT stock FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()[0]

    def assertInvalido(self, mensaje, **kwargs):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.crear(**kwargs)
        self.assertEqual(str(ctx.exception), mensaje)

    def conteos(self):
        return tuple(
            self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("ordenes", "orden_items", "movimientos")
        ) + (self.stock("A-01"), self.stock("B-02"))


class AltaServiceTest(ServiceBase):
    def test_normaliza_numero_y_codigos_y_usa_el_reloj(self):
        orden = self.crear("  ot-0003 ", "2026-11-20", [(" a-01 ", 2)])
        self.assertEqual(orden.numero, "OT-0003")
        self.assertEqual(orden.fecha, date(2026, 11, 20))
        self.assertEqual([(i.codigo, i.cantidad) for i in orden.items], [("A-01", 2)])
        creada = self.conn.execute("SELECT created_at FROM ordenes").fetchone()[0]
        self.assertEqual(creada, "2026-11-19T15:30:00-03:00")
        self.assertEqual(self.stock("A-01"), 3)

    def test_segunda_orden_con_otros_valores(self):
        orden = self.crear("x-9", "2025-01-15", [("b-02", 4), ("a-01", 1)])
        self.assertEqual(orden.numero, "X-9")
        self.assertEqual([(i.codigo, i.cantidad) for i in orden.items], [("A-01", 1), ("B-02", 4)])
        self.assertEqual((self.stock("A-01"), self.stock("B-02")), (4, 6))


class NumeroYFechaTest(ServiceBase):
    def test_numero_invalido(self):
        casos = (
            ("   ", "El campo numero es obligatorio."),
            ("", "El campo numero es obligatorio."),
            (None, "El campo numero es obligatorio."),
            ("X" * 31, "El campo numero admite hasta 30 caracteres."),
            (5, "El campo numero debe ser texto."),
        )
        for numero, mensaje in casos:
            with self.subTest(numero=numero):
                self.assertInvalido(mensaje, numero=numero)

    def test_numero_de_30_caracteres_se_acepta(self):
        self.assertEqual(self.crear("x" * 30).numero, "X" * 30)

    def test_fecha_invalida(self):
        casos = (
            (None, "El campo fecha es obligatorio."),
            ("", "El campo fecha es obligatorio."),
            ("20/11/2026", "La fecha debe tener formato AAAA-MM-DD."),
            ("2026-02-30", "La fecha (2026-02-30) no es una fecha válida."),
        )
        for fecha, mensaje in casos:
            with self.subTest(fecha=fecha):
                self.assertInvalido(mensaje, fecha=fecha)

    def test_fecha_pasada_y_futura_se_aceptan(self):
        self.assertEqual(self.crear("OT-1", "2025-01-15").fecha, date(2025, 1, 15))
        self.assertEqual(self.crear("OT-2", "2099-12-31").fecha, date(2099, 12, 31))


class ComponentesTest(ServiceBase):
    def test_lista_vacia(self):
        self.assertInvalido("La orden requiere al menos un componente.", componentes=[])

    def test_mas_de_100_lineas(self):
        self.assertInvalido(
            "La orden admite hasta 100 componentes.", componentes=[("A-01", 1)] * 101
        )

    def test_100_lineas_se_aceptan(self):
        insertar_producto(self.conn, "G-10", "Granel", 100)
        orden = self.crear(componentes=[("G-10", 1)] * 100)
        self.assertEqual([(i.codigo, i.cantidad) for i in orden.items], [("G-10", 100)])

    def test_componentes_no_es_lista(self):
        self.assertInvalido("El campo componentes debe ser una lista.", componentes="A-01")
        self.assertInvalido("El campo componentes debe ser una lista.", componentes={"A-01": 1})
        self.assertInvalido("El campo componentes es obligatorio.", componentes=None)

    def test_cantidad_invalida_en_la_segunda_linea(self):
        for cantidad in (0, 2.5, "5", True, 10_001):
            with self.subTest(cantidad=cantidad):
                self.assertInvalido(
                    f"Componente 2: {MSG_CANTIDAD}",
                    componentes=[("A-01", 1), ("B-02", cantidad)],
                )

    def test_codigo_invalido_en_la_primera_linea(self):
        self.assertInvalido(
            "Componente 1: El campo codigo es obligatorio.", componentes=[("", 1)]
        )
        self.assertInvalido(
            "Componente 1: El campo codigo admite hasta 50 caracteres.",
            componentes=[("X" * 51, 1)],
        )

    def test_linea_que_no_es_un_par(self):
        self.assertInvalido(
            "Componente 2: debe ser un objeto con codigo y cantidad.",
            componentes=[("A-01", 1), "B-02"],
        )

    def test_cantidad_10000_por_linea_se_acepta_con_stock(self):
        insertar_producto(self.conn, "G-10", "Granel", 10_000)
        self.assertEqual(self.crear(componentes=[("G-10", 10_000)]).items[0].cantidad, 10_000)


class ConsolidacionTest(ServiceBase):
    def test_codigos_repetidos_se_suman(self):
        orden = self.crear(componentes=[("A-01", 2), ("a-01", 1)])
        self.assertEqual([(i.codigo, i.cantidad) for i in orden.items], [("A-01", 3)])
        self.assertEqual(self.stock("A-01"), 2)

    def test_consolidado_excede_stock_informa_solicitado_total(self):
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.crear(componentes=[("A-01", 3), ("A-01", 3)])
        self.assertEqual(ctx.exception.faltantes, (Faltante("A-01", 5, 6),))
        self.assertEqual(self.stock("A-01"), 5)

    def test_total_consolidado_sobre_10000_se_acepta_con_stock(self):
        insertar_producto(self.conn, "G-10", "Granel", 12_000)
        orden = self.crear(componentes=[("G-10", 6_000), ("G-10", 6_000)])
        self.assertEqual([(i.codigo, i.cantidad) for i in orden.items], [("G-10", 12_000)])
        self.assertEqual(self.stock("G-10"), 0)

    def test_total_consolidado_sobre_10000_sin_stock_es_409(self):
        insertar_producto(self.conn, "G-10", "Granel", 11_000)
        with self.assertRaises(StockInsuficienteOrden) as ctx:
            self.crear(componentes=[("G-10", 6_000), ("G-10", 6_000)])
        self.assertEqual(ctx.exception.faltantes, (Faltante("G-10", 11_000, 12_000),))
        self.assertEqual(self.stock("G-10"), 11_000)

    def test_linea_individual_de_10001_sigue_siendo_422(self):
        self.assertInvalido(
            f"Componente 1: {MSG_CANTIDAD}", componentes=[("A-01", 10_001)]
        )


class SinEscrituraTest(ServiceBase):
    def test_validaciones_fallidas_no_escriben(self):
        antes = self.conteos()
        casos = (
            dict(numero=" "),
            dict(fecha="2026-02-30"),
            dict(componentes=[]),
            dict(componentes=[("A-01", 1), ("B-02", 0)]),
            dict(componentes=[("A-01", 1), "B-02"]),
        )
        for kwargs in casos:
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                with self.assertRaises(DatosInvalidos):
                    self.crear(**kwargs)
                self.assertEqual(self.conteos(), antes)
        self.assertEqual(movimientos(self.conn), [])

    def test_rechazos_de_negocio_no_escriben(self):
        self.crear("OT-0001", componentes=[("A-01", 1)])
        antes = self.conteos()
        for tipo, kwargs in (
            (OrdenDuplicada, dict(numero="ot-0001")),
            (ProductosNoEncontrados, dict(numero="OT-2", componentes=[("X-00", 1)])),
            (StockInsuficienteOrden, dict(numero="OT-3", componentes=[("B-02", 11)])),
        ):
            with self.subTest(tipo=tipo.__name__):
                with self.assertRaises(tipo):
                    self.crear(**kwargs)
                self.assertEqual(self.conteos(), antes)


class ListarServiceTest(ServiceBase):
    def sembrar(self, *numero_fecha):
        for numero, fecha in numero_fecha:
            self.crear(numero=numero, fecha=fecha)

    def numeros(self, *args, **kwargs):
        return [o.numero for o in self.service.listar(*args, **kwargs)]

    def test_sin_argumentos_devuelve_de_la_mas_nueva_a_la_mas_vieja(self):
        self.sembrar(("OT-1", "2026-11-18"), ("OT-2", "2026-11-20"), ("OT-3", "2026-11-17"))
        self.assertEqual(self.numeros(), ["OT-2", "OT-1", "OT-3"])

    def test_numero_se_normaliza_y_vacio_es_sin_filtro(self):
        self.sembrar(("OT-0003", "2026-11-18"), ("OT-0004", "2026-11-19"))
        self.assertEqual(self.numeros("  ot-0003 "), ["OT-0003"])
        for vacio in (None, "", "   "):
            with self.subTest(numero=vacio):
                self.assertEqual(self.numeros(vacio), ["OT-0004", "OT-0003"])

    def test_numero_de_31_caracteres_es_invalido(self):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.listar("X" * 31)
        self.assertEqual(str(ctx.exception), "El campo numero admite hasta 30 caracteres.")

    def test_numero_inexistente_lanza_no_encontrada_con_numero_normalizado(self):
        self.sembrar(("OT-0001", "2026-11-17"))
        with self.assertRaises(OrdenNoEncontrada) as ctx:
            self.service.listar("ot-9 ")
        self.assertEqual(str(ctx.exception), "No existe una orden con número 'OT-9'.")

    def test_numero_existente_fuera_del_rango_devuelve_lista_vacia(self):
        self.sembrar(("OT-0001", "2026-11-17"))
        self.assertEqual(self.numeros("OT-0001", desde="2026-11-18"), [])
        self.assertEqual(self.numeros("OT-0001", desde="2026-11-17"), ["OT-0001"])

    def espiar_existe_numero(self):
        """Espia sobre el repositorio SQLite real: registra las llamadas y delega."""
        llamadas = []

        class RepoEspia(SqliteOrdenRepository):
            def existe_numero(repo, numero):
                llamadas.append(numero)
                return super().existe_numero(numero)

        self.service = OrdenService(
            RepoEspia(self.conn), SqliteProcesoRepository(self.conn),
            SqliteServicioGeneralRepository(self.conn), ahora=lambda: FECHA_FIJA,
        )
        return llamadas

    def test_existe_numero_no_se_consulta_sin_numero(self):
        self.sembrar(("OT-0001", "2026-11-17"))
        llamadas = self.espiar_existe_numero()
        self.assertEqual(self.numeros(), ["OT-0001"])
        self.assertEqual(self.numeros(desde="2030-01-01"), [])
        self.assertEqual(llamadas, [])

    def test_existe_numero_no_se_consulta_si_el_filtro_devuelve_resultados(self):
        self.sembrar(("OT-0001", "2026-11-17"))
        llamadas = self.espiar_existe_numero()
        self.assertEqual(self.numeros("ot-0001"), ["OT-0001"])
        self.assertEqual(llamadas, [])

    def test_existe_numero_se_consulta_solo_con_numero_y_resultado_vacio(self):
        self.sembrar(("OT-0001", "2026-11-17"))
        llamadas = self.espiar_existe_numero()
        self.assertEqual(self.numeros("OT-0001", desde="2026-11-18"), [])
        self.assertEqual(llamadas, ["OT-0001"])
        with self.assertRaises(OrdenNoEncontrada):
            self.service.listar("ot-9")
        self.assertEqual(llamadas, ["OT-0001", "OT-9"])

    def test_numero_en_blanco_sin_ordenes_es_lista_vacia(self):
        self.assertEqual(self.numeros("   "), [])

    def test_fecha_invalida_tiene_prioridad_sobre_no_encontrada(self):
        with self.assertRaises(DatosInvalidos):
            self.service.listar("OT-9", desde="19/11/2026")

    def assertListarInvalido(self, mensaje, **kwargs):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.listar(**kwargs)
        self.assertEqual(str(ctx.exception), mensaje)

    def test_mensajes_de_fecha_identicos_a_movimientos(self):
        self.assertListarInvalido(
            "La fecha 'desde' debe tener formato AAAA-MM-DD.", desde="19/11/2026"
        )
        self.assertListarInvalido(
            "La fecha 'hasta' (2026-02-30) no es una fecha válida.", hasta="2026-02-30"
        )
        self.assertListarInvalido(
            "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).",
            desde="2026-11-20",
            hasta="2026-11-19",
        )

    def test_fechas_vacias_son_sin_filtro_y_solo_desde_o_solo_hasta_filtran(self):
        self.sembrar(("OT-1", "2026-11-18"), ("OT-2", "2026-11-19"), ("OT-3", "2026-11-20"))
        self.assertEqual(self.numeros(desde="", hasta=""), ["OT-3", "OT-2", "OT-1"])
        self.assertEqual(self.numeros(desde="2026-11-19"), ["OT-3", "OT-2"])
        self.assertEqual(self.numeros(hasta="2026-11-19"), ["OT-2", "OT-1"])
        self.assertEqual(self.numeros(desde="2026-11-19", hasta="2026-11-19"), ["OT-2"])

    def test_prioridad_de_errores_numero_luego_desde_luego_hasta(self):
        self.assertListarInvalido(
            "El campo numero admite hasta 30 caracteres.", numero="X" * 31, desde="mal"
        )
        self.assertListarInvalido(
            "La fecha 'desde' debe tener formato AAAA-MM-DD.", desde="mal", hasta="peor"
        )


class BorrarServiceTest(ServiceBase):
    def setUp(self):
        super().setUp()
        self.crear("OT-0001", componentes=(("A-01", 2), ("B-02", 4)))  # A-01 3, B-02 6

    def assertInvalidoBorrar(self, mensaje, numero, reintegrar):
        antes = self.conteos()
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.borrar(numero, reintegrar)
        self.assertEqual(str(ctx.exception), mensaje)
        self.assertEqual(self.conteos(), antes)  # la orden sigue y el stock no cambia

    def test_true_reintegra_y_false_no(self):
        res = self.service.borrar("OT-0001", "true")
        self.assertIs(res.reintegrado, True)
        self.assertEqual((self.stock("A-01"), self.stock("B-02")), (5, 10))
        self.crear("OT-0002", componentes=(("A-01", 1),))
        res = self.service.borrar("OT-0002", "false")
        self.assertIs(res.reintegrado, False)
        self.assertEqual(res.reintegros, ())
        self.assertEqual(self.stock("A-01"), 4)

    def test_reintegrar_faltante_o_vacio(self):
        for valor in (None, ""):
            with self.subTest(valor=valor):
                self.assertInvalidoBorrar("El campo reintegrar es obligatorio.", "OT-0001", valor)

    def test_reintegrar_distinto_de_true_false_exactos(self):
        for valor in ("si", "1", "TRUE", " true", "False", "yes", 1, 0):
            with self.subTest(valor=valor):
                self.assertInvalidoBorrar(
                    "El campo reintegrar debe ser true o false.", "OT-0001", valor
                )

    def test_bool_de_python_funciona(self):
        self.assertIs(self.service.borrar("OT-0001", False).reintegrado, False)
        self.crear("OT-0002", componentes=(("A-01", 1),))
        self.assertIs(self.service.borrar("OT-0002", True).reintegrado, True)

    def test_numero_se_normaliza(self):
        res = self.service.borrar("  ot-0001 ", "false")
        self.assertEqual(res.orden.numero, "OT-0001")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0], 0)

    def test_numero_en_blanco_o_nulo(self):
        for valor in ("", "   ", None):
            with self.subTest(valor=valor):
                self.assertInvalidoBorrar("El campo numero es obligatorio.", valor, "true")

    def test_numero_largo_y_limite(self):
        self.assertInvalidoBorrar(
            "El campo numero admite hasta 30 caracteres.", "X" * 31, "true"
        )
        limite = "x" * 30
        self.crear(limite, componentes=(("A-01", 1),))
        res = self.service.borrar(f"  {limite}  ", "false")
        self.assertEqual(res.orden.numero, "X" * 30)

    def test_numero_inexistente_normalizado(self):
        with self.assertRaises(OrdenNoEncontrada) as ctx:
            self.service.borrar("ot-0999", "true")
        self.assertEqual(str(ctx.exception), "No existe una orden con número 'OT-0999'.")

    def test_error_de_reintegrar_gana_sobre_el_de_numero(self):
        self.assertInvalidoBorrar("El campo reintegrar es obligatorio.", "OT-0999", None)
        self.assertInvalidoBorrar(
            "El campo reintegrar debe ser true o false.", "   ", "si"
        )


class OrdenConServicioBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 5)
        self.catalogo = ServicioGeneralService(SqliteServicioGeneralRepository(self.conn))
        self.service = OrdenService(
            SqliteOrdenRepository(self.conn),
            SqliteProcesoRepository(self.conn),
            SqliteServicioGeneralRepository(self.conn),
            ahora=lambda: FECHA_FIJA,
        )

    def crear(self, numero="OT-1", componentes=(("A-01", 1),), **kwargs):
        return self.service.crear(numero, "2026-11-20", componentes, self.uid, **kwargs)

    def stock(self):
        return self.conn.execute("SELECT stock FROM productos WHERE codigo='A-01'").fetchone()[0]

    def ordenes(self):
        return self.conn.execute("SELECT COUNT(*) FROM ordenes").fetchone()[0]

    def assertInvalido(self, mensaje, **kwargs):
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear(**kwargs)
        self.assertEqual(str(cm.exception), mensaje)
        self.assertEqual(self.stock(), 5)


SERVICIO_20 = ServicioOrden(
    "Servicio 20 hs", ("Chequeo de motor", "Chequeo de combustible", "Chequeo eléctrico")
)


class AltaConServicioTest(OrdenConServicioBase):
    def test_clave_con_espacios_y_mayusculas_resuelve_el_snapshot(self):
        self.assertEqual(self.crear(servicio=" Servicio-20-HS ").servicio, SERVICIO_20)

    def test_sin_servicio_ausente_none_o_blanco(self):
        self.assertIsNone(self.crear("OT-1").servicio)
        self.assertIsNone(self.crear("OT-2", servicio=None).servicio)
        self.assertIsNone(self.crear("OT-3", servicio="  ").servicio)
        self.assertIsNone(self.crear("OT-4", servicio="").servicio)

    def test_inexistente_no_toca_el_stock(self):
        self.assertInvalido("El servicio general 'servicio-500-hs' no existe.", servicio="servicio-500-hs")
        self.assertEqual(self.ordenes(), 0)

    def test_clave_larga_se_recorta_a_30_con_puntos(self):
        self.assertInvalido(
            f"El servicio general '{'x' * 30}…' no existe.", servicio="x" * 40
        )

    def test_tipo_invalido(self):
        for valor in (["servicio-20-hs"], 3, {"a": 1}, True):
            with self.subTest(valor=valor):
                self.assertInvalido("El campo servicio debe ser texto.", servicio=valor)

    def test_usa_los_chequeos_actuales_del_catalogo(self):
        self.catalogo.modificar("servicio-20-hs", chequeos=["Uno", "Dos"])
        self.assertEqual(
            self.crear(servicio="servicio-20-hs").servicio, ServicioOrden("Servicio 20 hs", ("Uno", "Dos"))
        )

    def test_servicio_y_procesos_juntos(self):
        orden = self.crear(servicio="servicio-20-hs", procesos=["limpieza"])
        self.assertEqual((orden.servicio, [p.nombre for p in orden.procesos]), (SERVICIO_20, ["Limpieza"]))
        self.assertEqual(self.stock(), 4)

    def test_solo_servicio_sin_componentes_se_rechaza(self):
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear(componentes=[], servicio="servicio-20-hs")
        self.assertEqual(str(cm.exception), "La orden requiere al menos un componente.")


class PrioridadDelServicioTest(OrdenConServicioBase):
    def test_componentes_vacios_ganan_al_servicio_inexistente(self):
        self.assertInvalido(
            "La orden requiere al menos un componente.", componentes=[], servicio="servicio-500-hs"
        )

    def test_servicio_inexistente_gana_al_proceso_inexistente(self):
        self.assertInvalido(
            "El servicio general 'servicio-500-hs' no existe.",
            servicio="servicio-500-hs", procesos=["pintura"],
        )

    def test_servicio_inexistente_gana_al_numero_duplicado(self):
        self.crear("OT-1")
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear("OT-1", servicio="servicio-500-hs")
        self.assertEqual(str(cm.exception), "El servicio general 'servicio-500-hs' no existe.")

    def test_servicio_inexistente_gana_a_los_personalizados_invalidos(self):
        self.assertInvalido(
            "El servicio general 'servicio-500-hs' no existe.",
            servicio="servicio-500-hs", procesos_personalizados=["  "],
        )

    def test_servicio_valido_y_proceso_inexistente_informa_el_proceso(self):
        self.assertInvalido("El proceso 'pintura' no existe.", servicio="servicio-20-hs", procesos=["pintura"])


MSG_PRECIO = "El precio debe ser un entero de centavos entre 0 y 99.999.999.999."
MSG_PRECIO_SERVICIO = (
    "El precio del servicio general debe ser un entero de centavos entre 0 y 99.999.999.999."
)
MSG_CELULAR = (
    "El celular admite solo números, espacios, +, - y paréntesis (de 6 a 20 caracteres)."
)


class DatosYPreciosBase(OrdenConServicioBase):
    def setUp(self):
        super().setUp()
        self.conn.execute("UPDATE productos SET stock = 50 WHERE codigo = 'A-01'")
        self.conn.commit()

    def crear(self, numero="OT-1", componentes=(("A-01", 1),), fecha="2026-11-20", **kwargs):
        return self.service.crear(numero, fecha, componentes, self.uid, **kwargs)

    def assertInvalido(self, mensaje, numero="OT-1", componentes=(("A-01", 1),), fecha="2026-11-20", **kwargs):
        antes = self.stock()
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear(numero, componentes, fecha, **kwargs)
        self.assertEqual(str(cm.exception), mensaje)
        self.assertEqual(self.stock(), antes)


class DatosDelClienteTest(DatosYPreciosBase):
    def test_cliente_recortado_con_espacios_internos_y_precio_de_linea(self):
        orden = self.crear(componentes=[("A-01", 2, 1200000)], datos={"cliente": "  Juan  Pérez "})
        self.assertEqual(orden.datos.cliente, "Juan  Pérez")
        self.assertEqual(orden.items[0].precio, 1200000)

    def test_todo_ausente_none_o_blanco_crea_la_orden_sin_datos(self):
        campos = ("cliente", "celular", "casco", "motor", "trailer", "fecha_ingreso", "fecha_egreso")
        variantes = (None, {}, {c: None for c in campos}, {c: "   " for c in campos}, {c: "" for c in campos})
        for n, datos in enumerate(variantes):
            with self.subTest(datos=datos):
                orden = self.crear(f"OT-{n}", datos=datos)
                self.assertEqual(
                    (orden.datos.cliente, orden.datos.celular, orden.datos.casco, orden.datos.motor,
                     orden.datos.trailer, orden.datos.fecha_ingreso, orden.datos.fecha_egreso),
                    (None,) * 7,
                )

    def test_cliente_largo_y_no_texto(self):
        self.assertInvalido("El cliente admite hasta 80 caracteres.", datos={"cliente": "x" * 81})
        self.assertEqual(self.crear("OT-2", datos={"cliente": "x" * 80}).datos.cliente, "x" * 80)
        self.assertInvalido("El campo cliente debe ser texto.", datos={"cliente": 3})

    def test_casco_motor_y_trailer(self):
        for campo in ("casco", "motor", "trailer"):
            with self.subTest(campo=campo):
                self.assertInvalido(f"El campo {campo} admite hasta 60 caracteres.", datos={campo: "x" * 61})
                self.assertInvalido(f"El campo {campo} debe ser texto.", datos={campo: ["a"]})
        orden = self.crear(datos={"casco": "Bermuda 190", "motor": "Mercury 90 HP", "trailer": "AB 123 CD"})
        self.assertEqual(
            (orden.datos.casco, orden.datos.motor, orden.datos.trailer),
            ("Bermuda 190", "Mercury 90 HP", "AB 123 CD"),
        )

    def test_celulares_validos_se_guardan_recortados_sin_normalizar(self):
        casos = (
            ("11 5555-1234", "11 5555-1234"),
            (" +54 9 11 5555-1234 ", "+54 9 11 5555-1234"),
            ("(011) 4555-1234", "(011) 4555-1234"),
        )
        for n, (entrada, guardado) in enumerate(casos):
            with self.subTest(celular=entrada):
                self.assertEqual(self.crear(f"OT-{n}", datos={"celular": entrada}).datos.celular, guardado)

    def test_celulares_invalidos(self):
        for valor in ("11-abc", "12345", "11+5555 1234", "1" * 21, "(((---)))"):
            with self.subTest(celular=valor):
                self.assertInvalido(MSG_CELULAR, datos={"celular": valor})
        self.assertInvalido("El campo celular debe ser texto.", datos={"celular": 1155551234})

    def test_solo_fecha_de_la_orden(self):
        orden = self.crear()
        self.assertEqual(
            (orden.fecha, orden.datos.fecha_ingreso, orden.datos.fecha_egreso),
            (date(2026, 11, 20), None, None),
        )

    def test_ingreso_y_egreso_iguales_o_posteriores_y_sin_relacion_con_la_fecha(self):
        casos = (
            ("2026-11-26", "2026-11-29"),
            ("2026-11-27", "2026-11-27"),
            (None, "2026-11-20"),
            ("2026-11-26", None),
            ("2026-11-30", "2026-12-02"),  # posteriores a la fecha de la orden
            ("2026-01-01", "2026-01-02"),  # anteriores a la fecha de la orden
        )
        for n, (ingreso, egreso) in enumerate(casos):
            with self.subTest(ingreso=ingreso, egreso=egreso):
                orden = self.crear(f"OT-{n}", datos={"fecha_ingreso": ingreso, "fecha_egreso": egreso})
                self.assertEqual(
                    (orden.datos.fecha_ingreso, orden.datos.fecha_egreso),
                    (date.fromisoformat(ingreso) if ingreso else None,
                     date.fromisoformat(egreso) if egreso else None),
                )

    def test_fechas_invalidas(self):
        self.assertInvalido(
            "La fecha de egreso no puede ser anterior a la de ingreso.",
            datos={"fecha_ingreso": "2026-11-27", "fecha_egreso": "2026-11-26"},
        )
        self.assertInvalido(
            "La fecha de egreso (2026-02-30) no es una fecha válida.",
            datos={"fecha_egreso": "2026-02-30"},
        )
        self.assertInvalido(
            "La fecha de ingreso debe tener formato AAAA-MM-DD.", datos={"fecha_ingreso": "30/11/2026"}
        )
        self.assertInvalido(
            "La fecha de ingreso (2026-02-30) no es una fecha válida.",
            datos={"fecha_ingreso": "2026-02-30"},
        )
        self.assertInvalido(
            "La fecha de egreso debe tener formato AAAA-MM-DD.", datos={"fecha_egreso": "mañana"}
        )

    def test_rechazo_por_stock_no_guarda_los_datos(self):
        with self.assertRaises(StockInsuficienteOrden):
            self.crear(componentes=[("A-01", 51)], datos={"cliente": "Juan"})
        self.assertEqual(self.ordenes(), 0)
        self.assertEqual(self.stock(), 50)


class PreciosTest(DatosYPreciosBase):
    def test_precio_cero_y_ausente(self):
        orden = self.crear(componentes=[("A-01", 1, 0)])
        self.assertEqual(orden.items[0].precio, 0)
        self.assertIsNone(self.crear("OT-2", componentes=[("A-01", 1)]).items[0].precio)
        self.assertIsNone(self.crear("OT-3", componentes=[("A-01", 1, None)]).items[0].precio)

    def test_precio_invalido_de_componente_informa_la_posicion(self):
        for valor in (-1, 10.5, "1500", True, 100000000000):
            with self.subTest(valor=valor):
                self.assertInvalido(
                    f"Componente 2: {MSG_PRECIO}", componentes=[("A-01", 1), ("A-02", 1, valor)]
                )
        self.assertInvalido(f"Componente 1: {MSG_PRECIO}", componentes=[("A-01", 1, 100000000000)])
        self.assertEqual(self.crear("OT-9", componentes=[("A-01", 1, 99999999999)]).items[0].precio, 99999999999)

    def test_repetidos_suman_los_importes_indicados(self):
        orden = self.crear(componentes=[("A-01", 2, 1000), ("a-01", 1), ("A-01", 1, 500)])
        self.assertEqual([(i.codigo, i.cantidad, i.precio) for i in orden.items], [("A-01", 4, 1500)])

    def test_repetidos_sin_ningun_precio_quedan_sin_precio(self):
        orden = self.crear(componentes=[("A-01", 2), ("A-01", 1)])
        self.assertEqual([(i.cantidad, i.precio) for i in orden.items], [(3, None)])

    def test_precio_del_servicio(self):
        self.assertEqual(
            self.crear(servicio="servicio-20-hs", precio_servicio=4500000).servicio.precio, 4500000
        )
        self.assertIsNone(self.crear("OT-2", servicio="servicio-20-hs").servicio.precio)
        self.assertEqual(self.crear("OT-3", servicio="servicio-20-hs", precio_servicio=0).servicio.precio, 0)

    def test_precio_del_servicio_sin_servicio_o_invalido(self):
        self.assertInvalido(
            "No se puede indicar el precio del servicio general sin elegir uno.", precio_servicio=1000
        )
        self.assertInvalido(
            "No se puede indicar el precio del servicio general sin elegir uno.",
            servicio="  ", precio_servicio=1000,
        )
        for valor in (-5, 1.5, "10", True):
            with self.subTest(valor=valor):
                self.assertInvalido(MSG_PRECIO_SERVICIO, servicio="servicio-20-hs", precio_servicio=valor)

    def test_procesos_con_y_sin_precio_en_orden(self):
        orden = self.crear(
            procesos=[{"clave": "limpieza", "precio": 1500000}, "cambio-filtro"],
            procesos_personalizados=[{"nombre": "Pulido", "precio": 800000}],
        )
        self.assertEqual(
            [(p.nombre, p.personalizado, p.precio) for p in orden.procesos],
            [("Limpieza", False, 1500000), ("Cambio filtro", False, None), ("Pulido", True, 800000)],
        )

    def test_clave_repetida_cuenta_la_primera_con_su_precio(self):
        orden = self.crear(procesos=[{"clave": "limpieza", "precio": 1000}, {"clave": "limpieza", "precio": 2000}])
        self.assertEqual([(p.nombre, p.precio) for p in orden.procesos], [("Limpieza", 1000)])

    def test_precio_invalido_de_proceso_y_de_personalizado(self):
        self.assertInvalido(
            f"Proceso 2: {MSG_PRECIO}", procesos=["limpieza", {"clave": "cambio-motor", "precio": -1}]
        )
        self.assertInvalido(
            f"Proceso personalizado 1: {MSG_PRECIO}",
            procesos_personalizados=[{"nombre": "Pulido", "precio": "mil"}],
        )
        self.assertInvalido(
            f"Proceso personalizado 2: {MSG_PRECIO}",
            procesos_personalizados=["Uno", {"nombre": "Dos", "precio": 1.5}],
        )

    def test_objetos_malformados_usan_el_mensaje_de_tipo_existente(self):
        for valor in ({"precio": 100}, {"clave": 5}, {"clave": "limpieza", "otra": 1}, 7):
            with self.subTest(valor=valor):
                self.assertInvalido("El campo procesos debe ser una lista de textos.", procesos=[valor])
        for valor in ({"precio": 100}, {"nombre": None}, {"nombre": "x", "otra": 1}):
            with self.subTest(valor=valor):
                self.assertInvalido(
                    "El campo procesos_personalizados debe ser una lista de textos.",
                    procesos_personalizados=[valor],
                )

    def test_precios_no_tocan_stock_movimientos_ni_catalogos(self):
        self.crear(componentes=[("A-01", 2, 1000)], procesos=[{"clave": "limpieza", "precio": 5}])
        self.assertEqual(self.stock(), 48)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM procesos").fetchone()[0], 3)


class PrioridadDeDatosYPreciosTest(DatosYPreciosBase):
    def test_fecha_invalida_gana_a_ingreso_invalido(self):
        self.assertInvalido(
            "La fecha (2026-02-30) no es una fecha válida.",
            fecha="2026-02-30", datos={"fecha_ingreso": "30/11/2026"},
        )

    def test_cliente_largo_gana_a_componentes_vacios(self):
        self.assertInvalido(
            "El cliente admite hasta 80 caracteres.", componentes=[], datos={"cliente": "x" * 81}
        )

    def test_egreso_anterior_gana_al_cliente_largo(self):
        self.assertInvalido(
            "La fecha de egreso no puede ser anterior a la de ingreso.",
            datos={"fecha_ingreso": "2026-11-27", "fecha_egreso": "2026-11-20", "cliente": "x" * 81},
        )

    def test_cliente_gana_al_celular_y_este_al_casco(self):
        self.assertInvalido(
            "El cliente admite hasta 80 caracteres.", datos={"cliente": "x" * 81, "celular": "1"}
        )
        self.assertInvalido(MSG_CELULAR, datos={"celular": "1", "casco": "x" * 61})
        self.assertInvalido(
            "El campo casco admite hasta 60 caracteres.", datos={"casco": "x" * 61, "motor": "x" * 61}
        )

    def test_precio_de_componente_gana_a_servicio_inexistente(self):
        self.assertInvalido(
            f"Componente 1: {MSG_PRECIO}", componentes=[("A-01", 1, -1)], servicio="servicio-500-hs"
        )

    def test_precio_de_servicio_gana_a_proceso_inexistente(self):
        self.assertInvalido(
            MSG_PRECIO_SERVICIO, servicio="servicio-20-hs", precio_servicio=-1, procesos=["pintura"]
        )

    def test_precio_de_proceso_invalido_gana_al_numero_duplicado(self):
        self.crear("OT-1")
        with self.assertRaises(DatosInvalidos) as cm:
            self.crear("OT-1", procesos=[{"clave": "limpieza", "precio": -1}])
        self.assertEqual(str(cm.exception), f"Proceso 1: {MSG_PRECIO}")


MSG_CHEQUEO_TIPO = "El campo chequeo_final debe ser una lista de claves."
MSG_PRECIO_CHEQUEO = "El precio debe ser un entero de centavos entre 0 y 99.999.999.999."
MSG_PRECIO_SERVICIO_EDICION = "El precio del servicio general" + MSG_PRECIO_CHEQUEO.removeprefix(
    "El precio"
)


class EdicionServiceBase(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        self.uid = insertar_usuario(self.conn)
        insertar_producto(self.conn, "A-01", "Tornillo", 10)
        insertar_producto(self.conn, "B-02", "Tuerca", 10)
        self.service = OrdenService(
            SqliteOrdenRepository(self.conn),
            SqliteProcesoRepository(self.conn),
            SqliteServicioGeneralRepository(self.conn),
            ahora=lambda: FECHA_FIJA,
        )
        self.service.crear("OT-0043", "2026-11-27", [("A-01", 2)], self.uid)  # stock A-01 = 8

    def stock(self, codigo="A-01"):
        return self.conn.execute(
            "SELECT stock FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()[0]

    def editar(self, numero="OT-0043", fecha="2026-11-28", componentes=(("A-01", 2),), **kwargs):
        return self.service.editar(numero, fecha, componentes, **kwargs)

    def foto(self):
        return [
            tuple(f)
            for t in ("ordenes", "orden_items", "orden_chequeo_final", "orden_servicio", "productos")
            for f in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")
        ]

    def assertInvalido(self, mensaje, **kwargs):
        antes = self.foto()
        with self.assertRaises(DatosInvalidos) as cm:
            self.editar(**kwargs)
        self.assertEqual(str(cm.exception), mensaje)
        self.assertEqual(self.foto(), antes)


class EdicionServiceTest(EdicionServiceBase):
    def test_normaliza_numero_consolida_y_normaliza_el_chequeo(self):
        resultado = self.service.editar(
            "  ot-0043 ", fecha="2026-11-28", componentes=[("A-01", 2, 1300000)],
            chequeo_final=[{"clave": " Entrega ", "precio": 500000}],
        )
        orden = resultado.orden
        self.assertEqual(orden.numero, "OT-0043")
        self.assertEqual(orden.fecha, date(2026, 11, 28))
        self.assertEqual(orden.items[0].precio, 1300000)
        self.assertEqual(orden.chequeo_final, (ChequeoFinal("entrega", "Entrega", 500000),))
        self.assertEqual(resultado.ajustes, ())
        self.assertEqual(self.stock(), 8)

    def test_otro_numero_otros_valores_y_ajustes(self):
        self.service.crear("OT-7", "2026-11-01", [("B-02", 1)], self.uid)
        resultado = self.service.editar("ot-7", "2026-11-02", [("b-02", 2), ("B-02", 3)])
        self.assertEqual([(i.codigo, i.cantidad) for i in resultado.orden.items], [("B-02", 5)])
        self.assertEqual(resultado.ajustes, (AjusteStock("B-02", "Tuerca", 1, 5, 5, False),))

    def test_orden_inexistente(self):
        with self.assertRaises(OrdenNoEncontrada):
            self.editar("OT-9999")

    def test_conservar_servicio_con_precio_sin_elegir_servicio_es_valido(self):
        self.conn.execute(
            "INSERT INTO orden_servicio (orden_id, nombre) SELECT id, 'Servicio 20 hs' FROM ordenes"
        )
        self.conn.commit()
        resultado = self.editar(conservar_servicio=True, precio_servicio=4500000)
        self.assertEqual(resultado.orden.servicio, ServicioOrden("Servicio 20 hs", (), 4500000))

    def test_conservar_servicio_en_orden_sin_servicio(self):
        self.assertInvalido(
            "La orden no tiene un servicio general para conservar.", conservar_servicio=True
        )

    def test_servicio_del_catalogo_reemplaza_y_none_lo_quita(self):
        resultado = self.editar(servicio="servicio-20-hs", precio_servicio=100)
        self.assertEqual(resultado.orden.servicio.nombre, "Servicio 20 hs")
        self.assertEqual(len(resultado.orden.servicio.chequeos), 3)
        self.assertIsNone(self.editar().orden.servicio)

    def test_numero_en_el_cuerpo_se_rechaza(self):
        for valor in ("OT-0044", "OT-0043", 5, ""):
            with self.subTest(valor=valor):
                self.assertInvalido(
                    "El número de la orden no se puede cambiar.", numero_cuerpo=valor
                )

    def test_numero_en_el_cuerpo_none_se_ignora(self):
        self.editar(numero_cuerpo=None)

    def test_conservar_y_elegir_a_la_vez(self):
        self.assertInvalido(
            "No se puede elegir un servicio general y conservar el actual a la vez.",
            servicio="servicio-20-hs", conservar_servicio=True,
        )

    def test_conservar_servicio_debe_ser_booleano(self):
        for valor in ("si", 1, "true", 0):
            with self.subTest(valor=valor):
                self.assertInvalido(
                    "El campo conservar_servicio debe ser true o false.", conservar_servicio=valor
                )

    def test_componentes_vacios_y_egreso_anterior_como_en_el_alta(self):
        self.assertInvalido("La orden requiere al menos un componente.", componentes=[])
        self.assertInvalido(
            "La fecha de egreso no puede ser anterior a la de ingreso.",
            datos={"fecha_ingreso": "2026-11-29", "fecha_egreso": "2026-11-26"},
        )

    def test_lineas_repetidas_se_consolidan(self):
        resultado = self.editar(componentes=[("A-01", 2, 1000), ("a-01", 1, 500)])
        self.assertEqual(
            [(i.codigo, i.cantidad, i.precio) for i in resultado.orden.items], [("A-01", 3, 1500)]
        )
        self.assertEqual(self.stock(), 7)


class ChequeoFinalServiceTest(EdicionServiceBase):
    """Validacion del chequeo final, tambien en el alta (C-06i, spec chequeo-final-ordenes)."""

    def test_clave_inexistente(self):
        self.assertInvalido(
            "El ítem de chequeo final 'lavado' no existe.", chequeo_final=["lavado"]
        )

    def test_clave_larga_se_recorta_en_el_mensaje(self):
        self.assertInvalido(
            f"El ítem de chequeo final '{'x' * 30}…' no existe.", chequeo_final=["x" * 40]
        )

    def test_repetida_sin_distinguir_mayusculas(self):
        self.assertInvalido(
            "Chequeo final 2: 'entrega' está repetido.", chequeo_final=["Entrega", "entrega"]
        )

    def test_precio_invalido_lleva_la_posicion(self):
        for precio in (-1, 1.5, "10", True, 100000000000):
            with self.subTest(precio=precio):
                self.assertInvalido(
                    f"Chequeo final 2: {MSG_PRECIO_CHEQUEO}",
                    chequeo_final=[
                        {"clave": "combustible", "precio": 800000},
                        {"clave": "entrega", "precio": precio},
                    ],
                )

    def test_tipo_invalido(self):
        casos = (
            "combustible", 5, {"clave": "entrega"}, [5],
            [{"clave": "entrega", "x": 1}], [{"precio": 5}],
        )
        for valor in casos:
            with self.subTest(valor=valor):
                self.assertInvalido(MSG_CHEQUEO_TIPO, chequeo_final=valor)

    def test_none_o_vacio_es_sin_chequeo(self):
        for valor in (None, []):
            with self.subTest(valor=valor):
                self.assertEqual(self.editar(chequeo_final=valor).orden.chequeo_final, ())

    def test_claves_en_cualquier_orden_se_guardan_con_y_sin_precio(self):
        orden = self.editar(
            chequeo_final=[
                "entrega",
                {"clave": "combustible", "precio": 800000},
                {"clave": "prueba-en-el-lago", "precio": None},
            ]
        ).orden
        self.assertEqual(
            [(c.clave, c.precio) for c in orden.chequeo_final],
            [("combustible", 800000), ("prueba-en-el-lago", None), ("entrega", None)],
        )

    def test_el_alta_tambien_valida_y_guarda_el_chequeo(self):
        orden = self.service.crear(
            "OT-9", "2026-11-28", [("B-02", 1)], self.uid,
            chequeo_final=["entrega", {"clave": "combustible", "precio": 800000}],
        )
        self.assertEqual([c.clave for c in orden.chequeo_final], ["combustible", "entrega"])
        self.assertEqual(orden.subtotal_servicios, 800000)
        antes = self.stock("B-02")
        with self.assertRaises(DatosInvalidos) as cm:
            self.service.crear(
                "OT-10", "2026-11-28", [("B-02", 1)], self.uid, chequeo_final=["lavado"]
            )
        self.assertEqual(str(cm.exception), "El ítem de chequeo final 'lavado' no existe.")
        self.assertEqual(self.stock("B-02"), antes)


class PrioridadDeEdicionTest(EdicionServiceBase):
    def test_numero_en_blanco_gana_a_fecha_invalida(self):
        with self.assertRaises(DatosInvalidos) as cm:
            self.service.editar("  ", "2026-02-30", [("A-01", 1)])
        self.assertEqual(str(cm.exception), "El campo numero es obligatorio.")

    def test_numero_en_cuerpo_gana_a_fecha_invalida(self):
        self.assertInvalido(
            "El número de la orden no se puede cambiar.", fecha="2026-02-30", numero_cuerpo="X"
        )

    def test_fecha_invalida_gana_a_orden_inexistente(self):
        with self.assertRaises(DatosInvalidos) as cm:
            self.service.editar("OT-9999", "2026-02-30", [("A-01", 1)])
        self.assertEqual(str(cm.exception), "La fecha (2026-02-30) no es una fecha válida.")

    def test_chequeo_invalido_gana_a_producto_inexistente(self):
        self.assertInvalido(
            "El ítem de chequeo final 'lavado' no existe.",
            componentes=[("ZZ-99", 1)], chequeo_final=["lavado"],
        )

    def test_procesos_invalidos_ganan_al_chequeo_invalido(self):
        self.assertInvalido(
            "El proceso 'pintura' no existe.", procesos=["pintura"], chequeo_final=["lavado"]
        )

    def test_precio_del_servicio_gana_a_conservar_y_elegir(self):
        self.assertInvalido(
            MSG_PRECIO_SERVICIO_EDICION,
            servicio="servicio-20-hs", conservar_servicio=True, precio_servicio=-1,
        )

    def test_producto_inexistente_gana_a_stock_insuficiente(self):
        with self.assertRaises(ProductosNoEncontrados):
            self.editar(componentes=[("A-01", 500), ("ZZ-99", 1)])

    def test_stock_insuficiente_informa_la_cantidad_adicional(self):
        with self.assertRaises(StockInsuficienteOrden) as cm:
            self.editar(componentes=[("A-01", 12)])
        self.assertEqual(cm.exception.faltantes, (Faltante("A-01", 8, 10),))
        self.assertEqual(self.stock(), 8)
