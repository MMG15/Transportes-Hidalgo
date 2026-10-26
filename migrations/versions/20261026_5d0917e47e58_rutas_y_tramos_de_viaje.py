"""rutas y tramos de viaje (Sesión 4 — RF-09, RF-11, RF-13)

- Nueva tabla `rutas` (consumo de referencia por estado de carga).
- Nueva tabla `tramos_viaje` (cada viaje se divide en tramos cargado / vacío).
- `viajes`: se reemplazan `origen` y `destino` (texto) por `ruta_id`; cliente, producto y
  cantidad pasan a ser opcionales (un viaje puede salir vacío); se agrega `origen_km`.
- `camiones`: se agregan `anio` y `km_actual`.

Migración de DATOS: por cada par (origen, destino) existente se crea una ruta, y cada viaje
recibe un único tramo "cargado" que va de la salida a la llegada (es lo que representaba
el modelo anterior).

Se usa `batch_alter_table` para que la migración funcione también sobre SQLite.

Revision ID: 5d0917e47e58
Revises: 82200f10b10e
Create Date: 2026-10-26 12:07:45.300620

"""

import uuid
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = "5d0917e47e58"
down_revision: str | Sequence[str] | None = "82200f10b10e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Vistas mínimas de las tablas, sólo con las columnas que usa la migración de datos.
# (No se importan los modelos de la aplicación: cambian con el tiempo y la migración no.)
viajes = sa.table(
    "viajes",
    sa.column("id", sa.Uuid()),
    sa.column("origen", sa.String()),
    sa.column("destino", sa.String()),
    sa.column("ruta_id", sa.Uuid()),
    sa.column("fecha_salida", sa.DateTime()),
    sa.column("km_salida", sa.Numeric()),
    sa.column("fecha_llegada", sa.DateTime()),
    sa.column("km_llegada", sa.Numeric()),
)
rutas = sa.table(
    "rutas",
    sa.column("id", sa.Uuid()),
    sa.column("origen", sa.String()),
    sa.column("destino", sa.String()),
    sa.column("pais", sa.String()),
    sa.column("activa", sa.Boolean()),
    sa.column("creado_en", sa.DateTime()),
)
tramos = sa.table(
    "tramos_viaje",
    sa.column("id", sa.Uuid()),
    sa.column("viaje_id", sa.Uuid()),
    sa.column("orden", sa.Integer()),
    sa.column("estado_carga", sa.String()),
    sa.column("fecha_inicio", sa.DateTime()),
    sa.column("km_inicio", sa.Numeric()),
    sa.column("fecha_fin", sa.DateTime()),
    sa.column("km_fin", sa.Numeric()),
)


def upgrade() -> None:
    # 1. Tablas nuevas
    op.create_table(
        "rutas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("origen", sa.String(length=150), nullable=False),
        sa.Column("destino", sa.String(length=150), nullable=False),
        sa.Column("pais", sa.String(length=2), nullable=False),
        sa.Column("km_estimados", sa.Numeric(precision=8, scale=1), nullable=True),
        sa.Column("ref_l100_cargado", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("ref_l100_vacio", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("origen", "destino", name="uq_rutas_origen_destino"),
    )
    op.create_table(
        "tramos_viaje",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("viaje_id", sa.Uuid(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("estado_carga", sa.String(length=10), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=False),
        sa.Column("km_inicio", sa.Numeric(precision=10, scale=1), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.Column("km_fin", sa.Numeric(precision=10, scale=1), nullable=True),
        sa.ForeignKeyConstraint(["viaje_id"], ["viajes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tramos_viaje_viaje_id"), "tramos_viaje", ["viaje_id"], unique=False)

    # 2. Columnas nuevas (ruta_id todavía opcional: se completa en el paso 3)
    with op.batch_alter_table("camiones") as batch:
        batch.add_column(sa.Column("anio", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("km_actual", sa.Numeric(precision=10, scale=1), nullable=True))
    with op.batch_alter_table("viajes") as batch:
        batch.add_column(sa.Column("ruta_id", sa.Uuid(), nullable=True))
        batch.add_column(
            sa.Column("origen_km", sa.String(length=10), nullable=False, server_default="manual")
        )

    # 3. Migración de datos
    conexion = op.get_bind()
    filas = conexion.execute(
        sa.select(
            viajes.c.id,
            viajes.c.origen,
            viajes.c.destino,
            viajes.c.fecha_salida,
            viajes.c.km_salida,
            viajes.c.fecha_llegada,
            viajes.c.km_llegada,
        )
    ).all()
    ruta_por_par: dict[tuple[str, str], uuid.UUID] = {}
    for fila in filas:
        par = (fila.origen.strip(), fila.destino.strip())
        if par not in ruta_por_par:
            ruta_por_par[par] = uuid.uuid4()
            conexion.execute(
                rutas.insert().values(
                    id=ruta_por_par[par],
                    origen=par[0],
                    destino=par[1],
                    pais="AR",
                    activa=True,
                    creado_en=datetime.now(),
                )
            )
        conexion.execute(
            viajes.update().where(viajes.c.id == fila.id).values(ruta_id=ruta_por_par[par])
        )
        conexion.execute(
            tramos.insert().values(
                id=uuid.uuid4(),
                viaje_id=fila.id,
                orden=0,
                estado_carga="cargado",
                fecha_inicio=fila.fecha_salida,
                km_inicio=fila.km_salida,
                fecha_fin=fila.fecha_llegada,
                km_fin=fila.km_llegada,
            )
        )

    # 4. Con los datos completos: ruta obligatoria, columnas viejas afuera
    with op.batch_alter_table("viajes") as batch:
        batch.alter_column("ruta_id", existing_type=sa.Uuid(), nullable=False)
        batch.alter_column("cliente_id", existing_type=sa.Uuid(), nullable=True)
        batch.alter_column("producto_id", existing_type=sa.Uuid(), nullable=True)
        batch.alter_column(
            "cantidad", existing_type=sa.Numeric(precision=10, scale=2), nullable=True
        )
        batch.create_index(batch.f("ix_viajes_ruta_id"), ["ruta_id"], unique=False)
        batch.create_foreign_key("fk_viajes_ruta_id_rutas", "rutas", ["ruta_id"], ["id"])
        batch.drop_column("destino")
        batch.drop_column("origen")


def downgrade() -> None:
    with op.batch_alter_table("viajes") as batch:
        batch.add_column(sa.Column("origen", sa.String(length=150), nullable=True))
        batch.add_column(sa.Column("destino", sa.String(length=150), nullable=True))

    # Se recupera origen/destino desde la ruta. Los tramos se pierden (el modelo viejo no los tenía).
    conexion = op.get_bind()
    for ruta in conexion.execute(sa.select(rutas.c.id, rutas.c.origen, rutas.c.destino)).all():
        conexion.execute(
            viajes.update()
            .where(viajes.c.ruta_id == ruta.id)
            .values(origen=ruta.origen, destino=ruta.destino)
        )

    with op.batch_alter_table("viajes") as batch:
        batch.alter_column("origen", existing_type=sa.String(length=150), nullable=False)
        batch.alter_column("destino", existing_type=sa.String(length=150), nullable=False)
        batch.drop_constraint("fk_viajes_ruta_id_rutas", type_="foreignkey")
        batch.drop_index(batch.f("ix_viajes_ruta_id"))
        batch.drop_column("origen_km")
        batch.drop_column("ruta_id")
    with op.batch_alter_table("camiones") as batch:
        batch.drop_column("km_actual")
        batch.drop_column("anio")
    op.drop_index(op.f("ix_tramos_viaje_viaje_id"), table_name="tramos_viaje")
    op.drop_table("tramos_viaje")
    op.drop_table("rutas")
