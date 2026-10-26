"""Tipo de cambio ARS ↔ CLP (CU-13) y conversión de importes (RF-40)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from flota.monedas.application.puertos import UoWMonedas
from flota.monedas.domain.entidades import TipoCambio, convertir_a_pesos
from flota.shared.application.comun import obtener_o_fallar
from flota.shared.domain.auditoria import AccionAuditoria
from flota.shared.domain.dinero import Dinero, ImporteGasto, Moneda
from flota.shared.domain.errores import Duplicado, ReglaNegocioViolada


class CargarCotizacion:
    """CU-13 (paso 4) — RF-39: carga manual de la cotización del día (respaldo de la automática)."""

    def __init__(self, uow: UoWMonedas) -> None:
        self._uow = uow

    def ejecutar(
        self,
        fecha: date,
        cotizacion: Decimal,
        origen: Moneda = Moneda.CLP,
        fuente: str = "manual",
    ) -> TipoCambio:
        tipo = TipoCambio(fecha=fecha, cotizacion=cotizacion, moneda_origen=origen, fuente=fuente)
        with self._uow as uow:
            if uow.tipos_cambio.obtener_por_fecha(fecha, origen):
                raise Duplicado(
                    f"Ya hay una cotización {origen} → ARS para el {fecha:%d/%m/%Y}; "
                    "para cambiarla usá «corregir»"
                )
            uow.tipos_cambio.guardar(tipo)
            uow.auditar("tipos_cambio", tipo.id, AccionAuditoria.ALTA, despues=tipo)
            uow.commit()
        return tipo


class CorregirCotizacion:
    """CU-13 E1 — RF-41: corregir una cotización.

    Si ya se usó en gastos, hay que confirmarlo explícitamente. Los gastos ya convertidos NO
    cambian: guardan la cotización que se les aplicó.
    """

    def __init__(self, uow: UoWMonedas) -> None:
        self._uow = uow

    def ejecutar(
        self, tipo_cambio_id: UUID, cotizacion: Decimal, fuente: str, confirmar: bool = False
    ) -> TipoCambio:
        with self._uow as uow:
            tipo = obtener_o_fallar(uow.tipos_cambio, tipo_cambio_id, "tipo de cambio")
            usos = uow.tipos_cambio.contar_usos(tipo.id)
            if usos and not confirmar:
                raise ReglaNegocioViolada(
                    f"La cotización ya se aplicó a {usos} gasto(s). Confirmá la corrección: "
                    "esos gastos conservan la cotización original."
                )
            antes = replace(tipo)  # copia del estado anterior, para la auditoría
            tipo.corregir(cotizacion, fuente)
            uow.tipos_cambio.guardar(tipo)
            uow.auditar("tipos_cambio", tipo.id, AccionAuditoria.MODIFICACION, antes, tipo)
            uow.commit()
        return tipo


class ConsultasTiposCambio:
    def __init__(self, uow: UoWMonedas) -> None:
        self._uow = uow

    def recientes(self, dias: int = 60) -> list[TipoCambio]:
        desde = date.today() - timedelta(days=dias)
        with self._uow as uow:
            todos = uow.tipos_cambio.listar(limite=1000)
        return sorted((t for t in todos if t.fecha >= desde), key=lambda t: t.fecha, reverse=True)

    def vigente(self, origen: Moneda = Moneda.CLP) -> TipoCambio | None:
        with self._uow as uow:
            return uow.tipos_cambio.vigente_al(date.today(), origen)


def importe_en_pesos(uow: UoWMonedas, monto: Dinero, fecha: date) -> ImporteGasto:
    """Servicio de aplicación (TASK-05 del BPMN): busca la cotización vigente y convierte.

    Lo usan combustible, peajes y viáticos. Debe llamarse dentro de un `with uow:` abierto.
    """
    tipo = None if monto.moneda == Moneda.ARS else uow.tipos_cambio.vigente_al(fecha, monto.moneda)
    return convertir_a_pesos(monto, tipo, fecha)
