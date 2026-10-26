"""Bases para los esquemas Pydantic de la API de todos los módulos."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, PlainSerializer

# Los Decimal se envían como número en el JSON (por defecto Pydantic los manda como texto).
Numero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

Limite = Query(100, ge=1, le=1000)
Desplazamiento = Query(0, ge=0)


class Esquema(BaseModel):
    """Esquema de salida: se construye desde una entidad con `model_validate(entidad)`."""

    model_config = ConfigDict(from_attributes=True)
