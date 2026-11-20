import unittest

from inventario.domain.errors import DatosInvalidos
from inventario.repositories.sqlite_repo import SqliteMovimientoRepository
from inventario.services.movimientos_service import MovimientosService
from tests.helpers import (
    conexion_inicializada,
    insertar_movimiento,
    insertar_producto,
    insertar_usuario,
)


class MovimientosServiceTest(unittest.TestCase):
    def setUp(self):
        self.conn = conexion_inicializada()
        self.addCleanup(self.conn.close)
        uid = insertar_usuario(self.conn, "admin")
        rd = insertar_producto(self.conn, "RD-6204", "Rodamiento", 5)
        a01 = insertar_producto(self.conn, "A-01", "Tornillo", 5)
        insertar_movimiento(self.conn, "2026-11-18T10:00:00-03:00", rd, "ingreso", 1, uid)
        insertar_movimiento(self.conn, "2026-11-19T10:00:00-03:00", a01, "egreso", 2, uid)
        self.service = MovimientosService(SqliteMovimientoRepository(self.conn))

    def codigos(self, **filtros):
        return [m.codigo for m in self.service.listar(**filtros)]

    def test_codigo_en_minusculas_con_espacios_se_normaliza(self):
        self.assertEqual(self.codigos(codigo=" rd-6204 "), ["RD-6204"])
        self.assertEqual(self.codigos(codigo="a-01"), ["A-01"])

    def test_sin_filtros_devuelve_todo_mas_nuevo_primero(self):
        self.assertEqual(self.codigos(), ["A-01", "RD-6204"])

    def test_valores_vacios_son_sin_filtro(self):
        for filtros in (
            {"codigo": ""},
            {"codigo": "   "},
            {"desde": ""},
            {"hasta": ""},
            {"codigo": None, "desde": None, "hasta": None},
        ):
            with self.subTest(filtros=filtros):
                self.assertEqual(len(self.service.listar(**filtros)), 2)

    def test_filtra_por_fechas_inclusivas(self):
        self.assertEqual(self.codigos(desde="2026-11-19"), ["A-01"])
        self.assertEqual(self.codigos(hasta="2026-11-18"), ["RD-6204"])
        self.assertEqual(self.codigos(desde="2026-11-19", hasta="2026-11-19"), ["A-01"])

    def test_formato_de_fecha_invalido(self):
        casos = [
            ({"desde": "19/11/2026"}, "La fecha 'desde' debe tener formato AAAA-MM-DD."),
            ({"hasta": "20261119"}, "La fecha 'hasta' debe tener formato AAAA-MM-DD."),
        ]
        for filtros, mensaje in casos:
            with self.subTest(filtros=filtros):
                with self.assertRaises(DatosInvalidos) as ctx:
                    self.service.listar(**filtros)
                self.assertEqual(str(ctx.exception), mensaje)

    def test_formato_estricto_rechaza_salto_final_y_digitos_unicode(self):
        casos = ["2026-11-19\n", "\uff12\uff10\uff12\uff16-11-19", "2026-11-1\u0669"]
        for valor in casos:
            for nombre in ("desde", "hasta"):
                with self.subTest(valor=valor, nombre=nombre):
                    with self.assertRaises(DatosInvalidos) as ctx:
                        self.service.listar(**{nombre: valor})
                    self.assertEqual(
                        str(ctx.exception),
                        f"La fecha '{nombre}' debe tener formato AAAA-MM-DD.",
                    )

    def test_fecha_inexistente(self):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.listar(hasta="2026-02-30")
        self.assertEqual(
            str(ctx.exception), "La fecha 'hasta' (2026-02-30) no es una fecha válida."
        )

    def test_desde_posterior_a_hasta(self):
        with self.assertRaises(DatosInvalidos) as ctx:
            self.service.listar(desde="2026-11-20", hasta="2026-11-19")
        self.assertEqual(
            str(ctx.exception),
            "La fecha 'desde' (2026-11-20) no puede ser posterior a 'hasta' (2026-11-19).",
        )

    def test_codigo_demasiado_largo(self):
        with self.assertRaises(DatosInvalidos):
            self.service.listar(codigo="x" * 51)


if __name__ == "__main__":
    unittest.main()
