"""Implementaciones en memoria de los puertos: permiten testear casos de uso sin base de datos."""

from __future__ import annotations

import copy
from uuid import UUID

from flota.catalogo.domain.repositorios import (
    RepositorioCamiones,
    RepositorioChoferes,
    RepositorioClientes,
    RepositorioProductos,
)
from flota.combustible.domain.repositorios import RepositorioCargas
from flota.shared.application.unidad_de_trabajo import UnidadDeTrabajoBase
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


class UnidadDeTrabajoFake(UnidadDeTrabajoBase):
    def __init__(self) -> None:
        self.camiones = CamionesFake()
        self.choferes = ChoferesFake()
        self.clientes = ClientesFake()
        self.productos = ProductosFake()
        self.rutas = RutasFake()
        self.viajes = ViajesFake()
        self.cargas = CargasFake()
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass
