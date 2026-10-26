"""Rutas y ciclo de vida de un viaje (CU-03)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.errores import Duplicado, ReglaNegocioViolada
from flota.viajes.application.puertos import UoWViajes
from flota.viajes.domain.entidades import EstadoCarga, OrigenKm, Pais, Ruta, TramoViaje, Viaje
from flota.viajes.domain.eventos import TramoCerrado, ViajeFinalizado


# ---------- Rutas ----------
@dataclass(frozen=True)
class DatosRuta:
    origen: str
    destino: str
    pais: Pais = Pais.AR
    km_estimados: Decimal | None = None
    ref_l100_cargado: Decimal | None = None
    ref_l100_vacio: Decimal | None = None
    activa: bool = True


class RegistrarRuta:
    """MOD-02 — RF-09: alta de una ruta con su consumo de referencia por estado de carga."""

    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosRuta) -> Ruta:
        ruta = Ruta(**asdict(datos))
        with self._uow as uow:
            if uow.rutas.obtener_por_origen_destino(ruta.origen, ruta.destino):
                raise Duplicado(f"Ya existe la ruta {ruta.nombre}")
            uow.rutas.guardar(ruta)
            uow.commit()
        return ruta


class ActualizarRuta:
    """MOD-02 — RF-11: el Resp. de Sistemas (ROL-02) ajusta las referencias de la ruta."""

    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(self, ruta_id: UUID, datos: DatosRuta) -> Ruta:
        with self._uow as uow:
            obtener_o_fallar(uow.rutas, ruta_id, "ruta")
            ruta = Ruta(**asdict(datos), id=ruta_id)
            otra = uow.rutas.obtener_por_origen_destino(ruta.origen, ruta.destino)
            if otra and otra.id != ruta_id:
                raise Duplicado(f"Ya existe la ruta {ruta.nombre}")
            uow.rutas.guardar(ruta)
            uow.commit()
        return ruta


class ConsultasRutas:
    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def listar(self, solo_activas: bool = False) -> list[Ruta]:
        with self._uow as uow:
            rutas = uow.rutas.listar(limite=1000)
        return [r for r in rutas if r.activa or not solo_activas]

    def obtener(self, ruta_id: UUID) -> Ruta:
        with self._uow as uow:
            return obtener_o_fallar(uow.rutas, ruta_id, "ruta")


# ---------- Viajes ----------
@dataclass(frozen=True)
class DatosInicioViaje:
    camion_id: UUID
    chofer_id: UUID
    ruta_id: UUID
    fecha_salida: datetime
    km_salida: Decimal
    estado_carga: EstadoCarga = EstadoCarga.CARGADO
    cliente_id: UUID | None = None
    producto_id: UUID | None = None
    cantidad: Decimal | None = None
    origen_km: OrigenKm = OrigenKm.MANUAL
    observaciones: str | None = None


class IniciarViaje:
    """CU-03 — RF-09: registra la salida del viaje con su primer tramo (cargado o vacío)."""

    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(self, datos: DatosInicioViaje) -> Viaje:
        viaje = Viaje.iniciar(**asdict(datos))
        with self._uow as uow:
            camion = obtener_o_fallar(uow.camiones, datos.camion_id, "camión")
            chofer = obtener_o_fallar(uow.choferes, datos.chofer_id, "chofer")
            ruta = obtener_o_fallar(uow.rutas, datos.ruta_id, "ruta")
            if datos.cliente_id:
                obtener_o_fallar(uow.clientes, datos.cliente_id, "cliente")
            if datos.producto_id:
                obtener_o_fallar(uow.productos, datos.producto_id, "producto")
            if not camion.activo:
                raise ReglaNegocioViolada(f"El camión {camion.patente} está inactivo")
            if not chofer.activo:
                raise ReglaNegocioViolada(f"El chofer {chofer.nombre} está inactivo")
            if not ruta.activa:
                raise ReglaNegocioViolada(f"La ruta {ruta.nombre} está inactiva")
            # CU-03 E1: un camión no puede tener dos viajes abiertos.
            if uow.viajes.buscar_en_curso(camion.id):
                raise ReglaNegocioViolada(f"El camión {camion.patente} ya tiene un viaje en curso")
            camion.registrar_km(datos.km_salida)
            uow.camiones.guardar(camion)
            uow.viajes.guardar(viaje)
            uow.commit()
        return viaje


class CambiarEstadoCarga:
    """CU-03 — RF-09: cierra el tramo actual y abre uno nuevo (p. ej. descarga -> regreso vacío)."""

    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(
        self, viaje_id: UUID, fecha: datetime, km: Decimal, nuevo_estado: EstadoCarga
    ) -> TramoViaje:
        with self._uow as uow:
            viaje = obtener_o_fallar(uow.viajes, viaje_id, "viaje")
            tramo = viaje.cambiar_estado_carga(fecha, km, nuevo_estado)
            camion = obtener_o_fallar(uow.camiones, viaje.camion_id, "camión")
            camion.registrar_km(km)
            uow.camiones.guardar(camion)
            uow.viajes.guardar(viaje)
            uow.registrar_evento(TramoCerrado(viaje.id))
            uow.commit()
        return tramo


class FinalizarViaje:
    """CU-03 — RF-09, RF-10: cierra el último tramo y el viaje."""

    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def ejecutar(self, viaje_id: UUID, fecha_llegada: datetime, km_llegada: Decimal) -> Viaje:
        with self._uow as uow:
            viaje = obtener_o_fallar(uow.viajes, viaje_id, "viaje")
            viaje.finalizar(fecha_llegada, km_llegada)
            camion = obtener_o_fallar(uow.camiones, viaje.camion_id, "camión")
            camion.registrar_km(km_llegada)
            uow.camiones.guardar(camion)
            uow.viajes.guardar(viaje)
            uow.registrar_evento(ViajeFinalizado(viaje.id))  # lo escucha el módulo de alertas
            uow.commit()
        return viaje


class ConsultasViajes:
    def __init__(self, uow: UoWViajes) -> None:
        self._uow = uow

    def obtener(self, viaje_id: UUID) -> Viaje:
        with self._uow as uow:
            return obtener_o_fallar(uow.viajes, viaje_id, "viaje")

    def listar(
        self,
        desde: datetime,
        hasta: datetime,
        camion_id: UUID | None = None,
        chofer_id: UUID | None = None,
        ruta_id: UUID | None = None,
    ) -> list[Viaje]:
        with self._uow as uow:
            return uow.viajes.listar_por_periodo(desde, hasta, camion_id, chofer_id, ruta_id)
