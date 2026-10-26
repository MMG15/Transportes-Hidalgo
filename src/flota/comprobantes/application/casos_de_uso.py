"""Recepción y validación de comprobantes de combustible (CU-02; RF-02, RF-04, RF-06, RF-07)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.combustible.domain.entidades import CargaCombustible, EstadoValidacion, OrigenDato
from flota.comprobantes.application.puertos import UoWComprobantes
from flota.comprobantes.domain.entidades import (
    CanalIngreso,
    Comprobante,
    EstadoComprobante,
    TipoComprobante,
    validar_archivo,
)
from flota.comprobantes.domain.eventos import ComprobantePendiente, ComprobanteRecibido
from flota.shared.application.archivos import AlmacenArchivos
from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.auditoria import AccionAuditoria
from flota.shared.domain.errores import ReglaNegocioViolada

type Reloj = Callable[[], datetime]

TABLA = "comprobantes"
SIN_LECTURA = "Sin lectura automática: completar los datos mirando la imagen"


@dataclass(frozen=True)
class ArchivoRecibido:
    contenido: bytes
    tipo_mime: str


class RecibirComprobante:
    """RF-01 / RF-02 — RF-07: guarda la imagen original y registra el comprobante.

    Publica `ComprobanteRecibido`: la lectura con IA lo procesa en segundo plano. Si no hay
    lectura automática configurada, queda pendiente para cargarlo a mano (CU-02).
    """

    def __init__(
        self,
        uow: UoWComprobantes,
        almacen: AlmacenArchivos,
        lectura_automatica: bool = False,
        reloj: Reloj = datetime.now,
    ) -> None:
        self._uow = uow
        self._almacen = almacen
        self._lectura_automatica = lectura_automatica
        self._ahora = reloj

    def ejecutar(
        self,
        archivo: ArchivoRecibido,
        tipo: TipoComprobante = TipoComprobante.COMBUSTIBLE,
        canal: CanalIngreso = CanalIngreso.PANEL,
        chofer_id: UUID | None = None,
        camion_id: UUID | None = None,
    ) -> Comprobante:
        extension = validar_archivo(archivo.tipo_mime, len(archivo.contenido))
        clave = self._almacen.guardar(archivo.contenido, extension, f"comprobantes/{tipo.value}")
        comprobante = Comprobante(
            tipo=tipo,
            canal=canal,
            archivo=clave,
            tipo_mime=archivo.tipo_mime,
            recibido_en=self._ahora(),
            chofer_id=chofer_id,
            camion_id=camion_id,
        )
        if not self._lectura_automatica:
            comprobante.marcar_pendiente([SIN_LECTURA])
        with self._uow as uow:
            uow.comprobantes.guardar(comprobante)
            uow.auditar(TABLA, comprobante.id, AccionAuditoria.ALTA, despues=comprobante)
            uow.registrar_evento(ComprobanteRecibido(comprobante.id))
            if comprobante.estado == EstadoComprobante.PENDIENTE:
                uow.registrar_evento(ComprobantePendiente(comprobante.id))
            uow.commit()
        return comprobante


class ValidarComprobanteCombustible:
    """CU-02 — RF-04, RF-06, RF-55: Administración confirma o corrige los datos mirando la
    imagen y se registra la carga, vinculada al comprobante.

    También lo usa la lectura con IA cuando los datos son válidos (CU-01): en ese caso la carga
    queda "validada por IA".
    """

    def __init__(self, uow: UoWComprobantes, reloj: Reloj = datetime.now) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self, comprobante_id: UUID, datos: DatosCarga, por_ia: bool = False
    ) -> CargaCombustible:
        with self._uow as uow:  # una sola transacción: la carga y el comprobante, o nada
            comprobante = obtener_o_fallar(uow.comprobantes, comprobante_id, "comprobante")
            if not comprobante.abierto:
                raise ReglaNegocioViolada(f"El comprobante ya está {comprobante.estado.value}")
            origen = (
                OrigenDato.TELEGRAM
                if comprobante.canal == CanalIngreso.TELEGRAM
                else OrigenDato.TICKET
            )
            estado = EstadoValidacion.VALIDADA_IA if por_ia else EstadoValidacion.VALIDADA
            datos = replace(
                datos, origen=origen, estado_validacion=estado, comprobante_id=comprobante.id
            )
            # La carga se registra con todas sus reglas (tanque, duplicados, moneda, fecha).
            carga = RegistrarCargaCombustible(uow, self._reloj).registrar_en(uow, datos)

            antes = replace(comprobante)
            comprobante.marcar_procesado(carga.id)
            uow.comprobantes.guardar(comprobante)
            # RF-55: queda registrado qué se corrigió respecto de lo que leyó la IA.
            uow.auditar(TABLA, comprobante.id, AccionAuditoria.MODIFICACION, antes, comprobante)
            uow.commit()
        return carga


class DescartarComprobante:
    """CU-02 E1: ticket ilegible, inválido o ajeno a la empresa."""

    def __init__(self, uow: UoWComprobantes) -> None:
        self._uow = uow

    def ejecutar(self, comprobante_id: UUID, motivo: str) -> Comprobante:
        with self._uow as uow:
            comprobante = obtener_o_fallar(uow.comprobantes, comprobante_id, "comprobante")
            antes = replace(comprobante)
            comprobante.descartar(motivo)
            uow.comprobantes.guardar(comprobante)
            uow.auditar(TABLA, comprobante.id, AccionAuditoria.BAJA, antes, comprobante)
            uow.commit()
        return comprobante


class ConsultasComprobantes:
    def __init__(self, uow: UoWComprobantes) -> None:
        self._uow = uow

    def pendientes(self, tipo: TipoComprobante | None = None) -> list[Comprobante]:
        estados = [EstadoComprobante.PENDIENTE, EstadoComprobante.RECIBIDO]
        with self._uow as uow:
            return uow.comprobantes.listar_por_estado(estados, tipo)

    def contar_pendientes(self) -> int:
        with self._uow as uow:
            return uow.comprobantes.contar_por_estado(EstadoComprobante.PENDIENTE)

    def obtener(self, comprobante_id: UUID) -> Comprobante:
        with self._uow as uow:
            return obtener_o_fallar(uow.comprobantes, comprobante_id, "comprobante")


class LeerArchivoComprobante:
    """RF-07: la imagen original, para verla junto a los datos (CU-02 paso 2)."""

    def __init__(self, uow: UoWComprobantes, almacen: AlmacenArchivos) -> None:
        self._uow = uow
        self._almacen = almacen

    def ejecutar(self, comprobante_id: UUID) -> tuple[bytes, str]:
        comprobante = ConsultasComprobantes(self._uow).obtener(comprobante_id)
        return self._almacen.leer(comprobante.archivo), comprobante.tipo_mime
