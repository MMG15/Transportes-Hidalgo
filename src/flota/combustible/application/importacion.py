"""Importación automática de cargas desde archivos (Excel, CSV de tarjeta de combustible)."""

from __future__ import annotations

from pathlib import Path

from flota.catalogo.domain.entidades import normalizar_patente
from flota.combustible.application.casos_de_uso import DatosCarga, RegistrarCargaCombustible
from flota.combustible.application.dto import ErrorLectura, ResultadoImportacion
from flota.combustible.application.puertos import LectorCargas, UoWCombustible
from flota.combustible.domain.entidades import OrigenDato
from flota.shared.domain.dinero import Moneda
from flota.shared.domain.errores import Duplicado, ErrorDominio


class ImportarCargas:
    """Cada fila se guarda en su propia transacción: una fila con error no frena al resto,
    y reimportar el mismo archivo no duplica datos."""

    def __init__(
        self,
        uow: UoWCombustible,
        lector: LectorCargas,
        origen: OrigenDato = OrigenDato.EXCEL,
    ) -> None:
        self._uow = uow
        self._lector = lector
        self._origen = origen
        self._registrar = RegistrarCargaCombustible(uow)

    def ejecutar(self, ruta: Path) -> ResultadoImportacion:
        resultado = ResultadoImportacion()
        camiones_por_patente: dict[str, object] = {}

        for item in self._lector.leer(ruta):
            resultado.procesadas += 1
            if isinstance(item, ErrorLectura):
                resultado.errores.append(f"Fila {item.numero_fila}: {item.mensaje}")
                continue

            patente = normalizar_patente(item.patente)
            if patente not in camiones_por_patente:
                with self._uow as uow:
                    camiones_por_patente[patente] = uow.camiones.obtener_por_patente(patente)
            camion = camiones_por_patente[patente]
            if camion is None:
                resultado.errores.append(
                    f"Fila {item.numero_fila}: no existe un camión con patente {patente}"
                )
                continue

            try:
                self._registrar.ejecutar(
                    DatosCarga(
                        camion_id=camion.id,
                        fecha=item.fecha,
                        litros=item.litros,
                        precio_litro=item.precio_litro,
                        odometro_km=item.odometro_km,
                        estacion=item.estacion,
                        origen=self._origen,
                        referencia_externa=item.referencia,
                        monto=item.importe,
                        moneda=Moneda(item.moneda),
                    )
                )
                resultado.importadas += 1
            except Duplicado:
                resultado.duplicadas += 1
            except ErrorDominio as error:
                resultado.errores.append(f"Fila {item.numero_fila}: {error}")

        return resultado
