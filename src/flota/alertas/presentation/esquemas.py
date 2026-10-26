"""Esquemas Pydantic de alertas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from flota.alertas.application.casos_de_uso import AccionAlerta
from flota.alertas.domain.entidades import EstadoAlerta, TipoAlerta
from flota.shared.presentation.esquemas import Esquema, Numero


class AlertaLeer(Esquema):
    id: UUID
    tipo: TipoAlerta
    nombre_tipo: str
    estado: EstadoAlerta
    descripcion: str
    creada_en: datetime
    valor_detectado: Numero | None
    valor_referencia: Numero | None
    camion_id: UUID | None
    viaje_id: UUID | None
    origen_tabla: str
    origen_id: UUID
    comentario: str | None
    resuelta_en: datetime | None
    escalada: bool


class AlertaResolver(BaseModel):
    accion: AccionAlerta
    comentario: str = Field(
        min_length=1, examples=["El chofer cargó para dos días por un corte de ruta"]
    )
