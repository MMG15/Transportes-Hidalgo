"""Registro de todas las tablas del sistema.

Importar este módulo carga los modelos ORM de todos los módulos en `Base.metadata`.
Lo usan Alembic (para comparar con la base) y los tests (para crear las tablas).
"""

from flota.alertas.infrastructure import modelos as _alertas  # noqa: F401
from flota.catalogo.infrastructure import modelos as _catalogo  # noqa: F401
from flota.combustible.infrastructure import modelos as _combustible  # noqa: F401
from flota.monedas.infrastructure import modelos as _monedas  # noqa: F401
from flota.shared.infrastructure import auditoria as _auditoria  # noqa: F401
from flota.shared.infrastructure.db import Base
from flota.usuarios.infrastructure import modelos as _usuarios  # noqa: F401
from flota.viajes.infrastructure import modelos as _viajes  # noqa: F401

__all__ = ["Base"]
