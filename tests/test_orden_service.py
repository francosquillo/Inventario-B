import unittest
from datetime import date, datetime

from inventario.domain.entities import Faltante, ServicioOrden
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
