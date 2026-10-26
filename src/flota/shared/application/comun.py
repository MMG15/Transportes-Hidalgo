from uuid import UUID

from flota.shared.domain.errores import NoEncontrado
from flota.shared.domain.repositorio import Repositorio


def obtener_o_fallar[E](repo: Repositorio[E], id: UUID, nombre: str) -> E:
    entidad = repo.obtener(id)
    if entidad is None:
        raise NoEncontrado(f"No existe el {nombre} con id {id}")
    return entidad
