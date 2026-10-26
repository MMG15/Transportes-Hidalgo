"""Generación y gestión de alertas (CU-06; RF-16, RF-18, RF-20)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from flota.alertas.application.puertos import UoWAlertas
from flota.alertas.domain.entidades import Alerta, EstadoAlerta, TipoAlerta
from flota.alertas.domain.eventos import AlertaEscalada, AlertaGenerada
from flota.combustible.application.consumo import CalculadoraConsumo
from flota.combustible.domain.consumo import ConsumoTramo, FuenteReferencia
from flota.shared.application.comun import obtener_o_fallar

type Reloj = Callable[[], datetime]

TABLA_TRAMOS = "tramos_viaje"
TABLA_CARGAS = "cargas_combustible"
NOMBRE_ESTADO = {"cargado": "cargado", "vacio": "vacío"}


NOMBRE_FUENTE = {
    FuenteReferencia.RUTA: "configurada en la ruta",
    FuenteReferencia.HISTORICO: "promedio histórico de la ruta",
    FuenteReferencia.CAMION: "referencia del camión",
}


def _num(valor: Decimal, decimales: int = 1, signo: bool = False) -> str:
    """Número con coma decimal, como se escribe en Argentina: 59,5 / +25,2."""
    return f"{valor:{'+' if signo else ''}.{decimales}f}".replace(".", ",")


def _texto_desvio(tramo: ConsumoTramo) -> str:
    return (
        f"Consumo {NOMBRE_ESTADO[tramo.estado_carga]} de {_num(tramo.consumo_l100km)} L/100km: "
        f"{_num(tramo.desvio_pct, signo=True)} % sobre la referencia de "
        f"{_num(tramo.referencia.valor)} ({NOMBRE_FUENTE[tramo.referencia.fuente]})"
    )


class EvaluarAlertasViaje:
    """RF-16: genera, actualiza o cierra las alertas de desvío de consumo de cada tramo.

    Se ejecuta cuando se cierra un tramo, cuando termina el viaje y cuando llega una carga
    tarde (eventos `TramoCerrado`, `ViajeFinalizado`, `CargaRegistrada`).
    """

    def __init__(self, uow: UoWAlertas, umbral_desvio_pct: Decimal, reloj: Reloj = datetime.now):
        self._uow = uow
        self._umbral = umbral_desvio_pct
        self._ahora = reloj

    def ejecutar(self, viaje_id: UUID) -> list[Alerta]:
        generadas: list[Alerta] = []
        with self._uow as uow:
            viaje = obtener_o_fallar(uow.viajes, viaje_id, "viaje")
            consumo = CalculadoraConsumo(uow, self._umbral).calcular(viaje)
            for tramo in consumo.tramos:
                if tramo.km_recorridos is None:
                    continue  # tramo abierto: todavía no se puede evaluar
                existente = uow.alertas.buscar_por_origen(
                    TipoAlerta.DESVIO_CONSUMO, TABLA_TRAMOS, tramo.tramo_id
                )
                if tramo.alerta and existente is None:
                    alerta = Alerta(
                        tipo=TipoAlerta.DESVIO_CONSUMO,
                        origen_tabla=TABLA_TRAMOS,
                        origen_id=tramo.tramo_id,
                        descripcion=_texto_desvio(tramo),
                        creada_en=self._ahora(),
                        valor_detectado=tramo.consumo_l100km,
                        valor_referencia=tramo.referencia.valor,
                        camion_id=viaje.camion_id,
                        viaje_id=viaje.id,
                    )
                    uow.alertas.guardar(alerta)
                    uow.registrar_evento(AlertaGenerada(alerta.id))
                    generadas.append(alerta)
                elif tramo.alerta and existente.abierta:
                    existente.actualizar(
                        _texto_desvio(tramo), tramo.consumo_l100km, tramo.referencia.valor
                    )
                    uow.alertas.guardar(existente)
                elif not tramo.alerta and existente and existente.abierta:
                    existente.normalizar(self._ahora())
                    uow.alertas.guardar(existente)
                # Una alerta ya resuelta por una persona no se reabre ni se modifica.
            uow.commit()
        return generadas


class EvaluarAlertasCarga:
    """RF-18: alerta si los litros de una carga superan la capacidad del tanque."""

    def __init__(
        self, uow: UoWAlertas, tolerancia_tanque_pct: Decimal, reloj: Reloj = datetime.now
    ) -> None:
        self._uow = uow
        self._tolerancia = tolerancia_tanque_pct
        self._ahora = reloj

    def ejecutar(self, carga_id: UUID) -> Alerta | None:
        with self._uow as uow:
            carga = obtener_o_fallar(uow.cargas, carga_id, "carga")
            camion = obtener_o_fallar(uow.camiones, carga.camion_id, "camión")
            if not carga.supera_tanque(camion.capacidad_tanque_litros, self._tolerancia):
                return None
            if uow.alertas.buscar_por_origen(TipoAlerta.CAPACIDAD_TANQUE, TABLA_CARGAS, carga.id):
                return None
            alerta = Alerta(
                tipo=TipoAlerta.CAPACIDAD_TANQUE,
                origen_tabla=TABLA_CARGAS,
                origen_id=carga.id,
                descripcion=(
                    f"Carga de {_num(carga.litros, 0)} L en {camion.patente}: el tanque es de "
                    f"{_num(camion.capacidad_tanque_litros, 0)} L"
                ),
                creada_en=self._ahora(),
                valor_detectado=carga.litros,
                valor_referencia=camion.capacidad_tanque_litros,
                camion_id=camion.id,
                viaje_id=carga.viaje_id,
            )
            uow.alertas.guardar(alerta)
            uow.registrar_evento(AlertaGenerada(alerta.id))
            uow.commit()
        return alerta


class AccionAlerta(StrEnum):
    EN_ANALISIS = "en_analisis"
    JUSTIFICAR = "justificar"
    CONFIRMAR = "confirmar"


class ResolverAlerta:
    """CU-06 — RF-20: el Administrativo (o Gerencia) analiza y resuelve una alerta."""

    def __init__(self, uow: UoWAlertas, reloj: Reloj = datetime.now) -> None:
        self._uow = uow
        self._ahora = reloj

    def ejecutar(
        self,
        alerta_id: UUID,
        accion: AccionAlerta,
        comentario: str,
        usuario_id: UUID | None = None,
    ) -> Alerta:
        with self._uow as uow:
            alerta = obtener_o_fallar(uow.alertas, alerta_id, "alerta")
            ahora = self._ahora()
            match AccionAlerta(accion):
                case AccionAlerta.EN_ANALISIS:
                    alerta.poner_en_analisis(comentario, ahora, usuario_id)
                case AccionAlerta.JUSTIFICAR:
                    alerta.justificar(comentario, ahora, usuario_id)
                case AccionAlerta.CONFIRMAR:
                    alerta.confirmar_desvio(comentario, ahora, usuario_id)
                    uow.registrar_evento(AlertaEscalada(alerta.id))
            uow.alertas.guardar(alerta)
            uow.commit()
        return alerta


class ConsultasAlertas:
    def __init__(self, uow: UoWAlertas) -> None:
        self._uow = uow

    def abiertas(self) -> list[Alerta]:
        return self.listar([EstadoAlerta.ABIERTA, EstadoAlerta.EN_ANALISIS])

    def listar(self, estados: list[EstadoAlerta] | None = None, limite: int = 200) -> list[Alerta]:
        with self._uow as uow:
            return uow.alertas.listar_por_estado(estados, limite)

    def contar_abiertas(self) -> int:
        with self._uow as uow:
            return uow.alertas.contar_abiertas()

    def obtener(self, alerta_id: UUID) -> Alerta:
        with self._uow as uow:
            return obtener_o_fallar(uow.alertas, alerta_id, "alerta")
