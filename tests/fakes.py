"""Implementaciones en memoria de los puertos: permiten testear casos de uso sin base de datos."""

from __future__ import annotations

import copy
from uuid import UUID

from flota.alertas.domain.repositorios import RepositorioAlertas
from flota.catalogo.domain.repositorios import (
    RepositorioCamiones,
    RepositorioChoferes,
    RepositorioClientes,
    RepositorioProductos,
)
from flota.combustible.domain.repositorios import RepositorioCargas
from flota.monedas.domain.repositorios import RepositorioTiposCambio
from flota.shared.application.eventos import BusEventos
from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajoBase
from flota.shared.domain.dinero import Moneda
from flota.shared.domain.repositorio_auditoria import RepositorioAuditoria
from flota.usuarios.application.puertos import HasherContrasenas
from flota.usuarios.domain.repositorios import RepositorioUsuarios
from flota.viajes.domain.entidades import EstadoViaje
from flota.viajes.domain.repositorios import RepositorioRutas, RepositorioViajes


class _EnMemoria:
    def __init__(self) -> None:
        self.datos: dict[UUID, object] = {}

    def guardar(self, entidad) -> None:
        self.datos[entidad.id] = copy.deepcopy(entidad)  # copia: simula una base real

    def obtener(self, id):
        return copy.deepcopy(self.datos.get(id))

    def listar(self, limite=100, desplazamiento=0):
        return [copy.deepcopy(e) for e in self.datos.values()][
            desplazamiento : desplazamiento + limite
        ]

    def _filtrar(self, condicion):
        return [copy.deepcopy(e) for e in self.datos.values() if condicion(e)]

    def _primero(self, condicion):
        return next(iter(self._filtrar(condicion)), None)


class CamionesFake(_EnMemoria, RepositorioCamiones):
    def obtener_por_patente(self, patente):
        return self._primero(lambda c: c.patente == patente)


class ChoferesFake(_EnMemoria, RepositorioChoferes):
    def obtener_por_dni(self, dni):
        return self._primero(lambda c: c.dni == dni)


class ClientesFake(_EnMemoria, RepositorioClientes):
    pass


class ProductosFake(_EnMemoria, RepositorioProductos):
    def obtener_por_nombre(self, nombre):
        return self._primero(lambda p: p.nombre == nombre)


class RutasFake(_EnMemoria, RepositorioRutas):
    def obtener_por_origen_destino(self, origen, destino):
        return self._primero(lambda r: (r.origen, r.destino) == (origen, destino))


class ViajesFake(_EnMemoria, RepositorioViajes):
    def listar_por_periodo(self, desde, hasta, camion_id=None, chofer_id=None, ruta_id=None):
        return sorted(
            self._filtrar(
                lambda v: (
                    desde <= v.fecha_salida < hasta
                    and (camion_id is None or v.camion_id == camion_id)
                    and (chofer_id is None or v.chofer_id == chofer_id)
                    and (ruta_id is None or v.ruta_id == ruta_id)
                )
            ),
            key=lambda v: v.fecha_salida,
        )

    def buscar_en_curso(self, camion_id):
        return self._primero(
            lambda v: v.camion_id == camion_id and v.estado == EstadoViaje.EN_CURSO
        )

    def buscar_por_camion_y_fecha(self, camion_id, fecha):
        return self._primero(lambda v: v.camion_id == camion_id and v.incluye_fecha(fecha))

    def listar_finalizados_por_ruta(self, ruta_id, antes_de=None, limite=20):
        viajes = self._filtrar(
            lambda v: (
                v.ruta_id == ruta_id
                and v.estado == EstadoViaje.FINALIZADO
                and (antes_de is None or v.fecha_salida < antes_de)
            )
        )
        return sorted(viajes, key=lambda v: v.fecha_salida, reverse=True)[:limite]


class CargasFake(_EnMemoria, RepositorioCargas):
    def listar_por_viajes(self, viaje_ids):
        return self._filtrar(lambda c: c.viaje_id in set(viaje_ids))

    def listar_filtrado(self, camion_id=None, desde=None, hasta=None, limite=100, desplazamiento=0):
        return self._filtrar(lambda c: camion_id is None or c.camion_id == camion_id)

    def existe_duplicado(self, carga):
        def igual(c):
            if carga.referencia_externa:
                return c.referencia_externa == carga.referencia_externa
            return (c.camion_id, c.fecha, c.litros) == (carga.camion_id, carga.fecha, carga.litros)

        return bool(self._filtrar(igual))


class TiposCambioFake(_EnMemoria, RepositorioTiposCambio):
    def __init__(self, cargas: CargasFake) -> None:
        super().__init__()
        self._cargas = cargas

    def obtener_por_fecha(self, fecha, origen, destino=Moneda.ARS):
        return self._primero(
            lambda t: (t.fecha, t.moneda_origen, t.moneda_destino) == (fecha, origen, destino)
        )

    def vigente_al(self, fecha, origen, destino=Moneda.ARS):
        candidatos = self._filtrar(
            lambda t: t.fecha <= fecha and (t.moneda_origen, t.moneda_destino) == (origen, destino)
        )
        return max(candidatos, key=lambda t: t.fecha, default=None)

    def contar_usos(self, tipo_cambio_id):
        return len(
            self._cargas._filtrar(
                lambda c: c.importe is not None and c.importe.tipo_cambio_id == tipo_cambio_id
            )
        )


class AlertasFake(_EnMemoria, RepositorioAlertas):
    def buscar_por_origen(self, tipo, origen_tabla, origen_id):
        return self._primero(
            lambda a: (a.tipo, a.origen_tabla, a.origen_id) == (tipo, origen_tabla, origen_id)
        )

    def listar_por_estado(self, estados=None, limite=200):
        lista = self._filtrar(lambda a: not estados or a.estado in estados)
        return sorted(lista, key=lambda a: a.creada_en, reverse=True)[:limite]

    def contar_abiertas(self):
        return len(self._filtrar(lambda a: a.abierta))


class UsuariosFake(_EnMemoria, RepositorioUsuarios):
    def obtener_por_email(self, email):
        return self._primero(lambda u: u.email == email.strip().lower())


class AuditoriaFake(_EnMemoria, RepositorioAuditoria):
    def listar_filtrado(self, tabla=None, registro_id=None, usuario_id=None, limite=200):
        lista = self._filtrar(
            lambda r: (
                (tabla is None or r.tabla == tabla)
                and (registro_id is None or r.registro_id == registro_id)
                and (usuario_id is None or r.usuario_id == usuario_id)
            )
        )
        return sorted(lista, key=lambda r: r.fecha, reverse=True)[:limite]


class HasherFake(HasherContrasenas):
    """Argon2 es lento a propósito (dificulta adivinar contraseñas): en tests no hace falta."""

    def hash(self, contrasena):
        return f"hash:{contrasena}"

    def verificar(self, contrasena, hash_guardado):
        return hash_guardado == f"hash:{contrasena}"


class UnidadDeTrabajoFake(UnidadDeTrabajoBase):
    """Unidad de trabajo en memoria. Con `bus`, publica los eventos como la real."""

    def __init__(self, bus: BusEventos | None = None) -> None:
        super().__init__(bus)
        self.camiones = CamionesFake()
        self.choferes = ChoferesFake()
        self.clientes = ClientesFake()
        self.productos = ProductosFake()
        self.rutas = RutasFake()
        self.viajes = ViajesFake()
        self.cargas = CargasFake()
        self.tipos_cambio = TiposCambioFake(self.cargas)
        self.alertas = AlertasFake()
        self.usuarios = UsuariosFake()
        self.auditoria = AuditoriaFake()
        self.commits = 0
        self.eventos_publicados: list = []

    def registrar_evento(self, evento) -> None:
        super().registrar_evento(evento)
        self.eventos_publicados.append(evento)

    def _confirmar(self) -> None:
        self.commits += 1

    def _descartar(self) -> None:
        pass
