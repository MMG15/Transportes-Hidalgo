"""moneda y alertas (Sesión 5 — RF-16, RF-18, RF-20, RF-39 a RF-41)

- Nueva tabla `tipos_cambio` (cotización diaria CLP -> ARS).
- Nueva tabla `alertas` (todas las alertas, con estado y resolución).
- `cargas_combustible`: el importe pasa de `precio_litro` a un importe completo
  (monto original, moneda, cotización, monto en ARS, tipo de cambio aplicado).

Migración de DATOS: las cargas existentes tenían precio por litro en pesos argentinos;
su importe pasa a ser litros × precio, en ARS, con cotización 1.

Revision ID: 619242b605d9
Revises: 5d0917e47e58
Create Date: 2026-10-26 13:09:59.312104

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "619242b605d9"
down_revision: str | Sequence[str] | None = "5d0917e47e58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

cargas = sa.table(
    "cargas_combustible",
    sa.column("litros", sa.Numeric()),
    sa.column("precio_litro", sa.Numeric()),
    sa.column("monto_original", sa.Numeric()),
    sa.column("moneda", sa.String()),
    sa.column("cotizacion", sa.Numeric()),
    sa.column("monto_ars", sa.Numeric()),
)


def upgrade() -> None:
    op.create_table(
        "alertas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("origen_tabla", sa.String(length=40), nullable=False),
        sa.Column("origen_id", sa.Uuid(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.Column("valor_detectado", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("valor_referencia", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("camion_id", sa.Uuid(), nullable=True),
        sa.Column("viaje_id", sa.Uuid(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("resuelta_en", sa.DateTime(), nullable=True),
        sa.Column("escalada", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alertas_camion_id"), "alertas", ["camion_id"], unique=False)
    op.create_index(op.f("ix_alertas_creada_en"), "alertas", ["creada_en"], unique=False)
    op.create_index(op.f("ix_alertas_estado"), "alertas", ["estado"], unique=False)
    op.create_index(
        "ix_alertas_origen", "alertas", ["tipo", "origen_tabla", "origen_id"], unique=False
    )
    op.create_table(
        "tipos_cambio",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("moneda_origen", sa.String(length=3), nullable=False),
        sa.Column("moneda_destino", sa.String(length=3), nullable=False),
        sa.Column("cotizacion", sa.Numeric(precision=14, scale=6), nullable=False),
        sa.Column("fuente", sa.String(length=60), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fecha", "moneda_origen", "moneda_destino", name="uq_tipos_cambio_dia"),
    )
    op.create_index(op.f("ix_tipos_cambio_fecha"), "tipos_cambio", ["fecha"], unique=False)

    with op.batch_alter_table("cargas_combustible") as batch:
        batch.add_column(sa.Column("monto_original", sa.Numeric(14, 2), nullable=True))
        batch.add_column(sa.Column("moneda", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("cotizacion", sa.Numeric(14, 6), nullable=True))
        batch.add_column(sa.Column("monto_ars", sa.Numeric(14, 2), nullable=True))
        batch.add_column(sa.Column("tipo_cambio_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column(
                "revisar_cotizacion", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )

    # Datos: precio por litro (ARS) -> importe completo. Una sola sentencia UPDATE.
    importe = sa.func.round(cargas.c.litros * cargas.c.precio_litro, 2)
    op.execute(
        cargas.update()
        .where(cargas.c.precio_litro.is_not(None))
        .values(monto_original=importe, moneda="ARS", cotizacion=1, monto_ars=importe)
    )

    with op.batch_alter_table("cargas_combustible") as batch:
        batch.create_index(
            batch.f("ix_cargas_combustible_tipo_cambio_id"), ["tipo_cambio_id"], unique=False
        )
        batch.create_foreign_key(
            "fk_cargas_tipo_cambio", "tipos_cambio", ["tipo_cambio_id"], ["id"]
        )
        batch.drop_column("precio_litro")


def downgrade() -> None:
    with op.batch_alter_table("cargas_combustible") as batch:
        batch.add_column(sa.Column("precio_litro", sa.Numeric(12, 2), nullable=True))
    # Sólo se puede volver a "precio por litro en ARS": se usa el monto convertido.
    op.execute(
        cargas.update()
        .where(cargas.c.monto_ars.is_not(None))
        .values(precio_litro=sa.func.round(cargas.c.monto_ars / cargas.c.litros, 2))
    )
    with op.batch_alter_table("cargas_combustible") as batch:
        batch.drop_constraint("fk_cargas_tipo_cambio", type_="foreignkey")
        batch.drop_index(batch.f("ix_cargas_combustible_tipo_cambio_id"))
        for columna in (
            "revisar_cotizacion",
            "tipo_cambio_id",
            "monto_ars",
            "cotizacion",
            "moneda",
            "monto_original",
        ):
            batch.drop_column(columna)
    op.drop_index(op.f("ix_tipos_cambio_fecha"), table_name="tipos_cambio")
    op.drop_table("tipos_cambio")
    op.drop_index("ix_alertas_origen", table_name="alertas")
    op.drop_index(op.f("ix_alertas_estado"), table_name="alertas")
    op.drop_index(op.f("ix_alertas_creada_en"), table_name="alertas")
    op.drop_index(op.f("ix_alertas_camion_id"), table_name="alertas")
    op.drop_table("alertas")
