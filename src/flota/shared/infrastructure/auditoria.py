"""Tabla y repositorio SQL de la auditoría (RF-55)."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Index, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from flota.shared.domain.auditoria import RegistroAuditoria
from flota.shared.domain.repositorio_auditoria import RepositorioAuditoria
from flota.shared.infrastructure.db import Base, RepositorioSql

# JSONB en PostgreSQL (se puede consultar por dentro); JSON común en SQLite.
JsonFlexible = JSON().with_variant(JSONB(), "postgresql")


class AuditoriaModel(Base):
    __tablename__ = "auditoria"
    __table_args__ = (Index("ix_auditoria_registro", "tabla", "registro_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(index=True)
    tabla: Mapped[str] = mapped_column(String(40))
    registro_id: Mapped[uuid.UUID]
    accion: Mapped[str] = mapped_column(String(15))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    usuario_nombre: Mapped[str] = mapped_column(String(120))
    valor_anterior: Mapped[dict | None] = mapped_column(JsonFlexible)
    valor_nuevo: Mapped[dict | None] = mapped_column(JsonFlexible)


class RepositorioAuditoriaSql(
    RepositorioSql[RegistroAuditoria, AuditoriaModel], RepositorioAuditoria
):
    entidad, modelo, orden = RegistroAuditoria, AuditoriaModel, AuditoriaModel.fecha.desc()

    def guardar(self, entidad: RegistroAuditoria) -> None:
        self._s.add(self._a_modelo(entidad))  # siempre es un alta: la auditoría no se modifica
        self._s.flush()

    def listar_filtrado(
        self,
        tabla: str | None = None,
        registro_id: UUID | None = None,
        usuario_id: UUID | None = None,
        limite: int = 200,
    ) -> list[RegistroAuditoria]:
        stmt = select(AuditoriaModel)
        if tabla:
            stmt = stmt.where(AuditoriaModel.tabla == tabla)
        if registro_id:
            stmt = stmt.where(AuditoriaModel.registro_id == registro_id)
        if usuario_id:
            stmt = stmt.where(AuditoriaModel.usuario_id == usuario_id)
        return self._todos(stmt.order_by(self.orden).limit(limite))
