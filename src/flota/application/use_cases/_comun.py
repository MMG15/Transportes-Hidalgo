from uuid import UUID

from flota.domain.exceptions import NoEncontrado
from flota.domain.repositories import Repositorio


def obtener_o_fallar[E](repo: Repositorio[E], id: UUID, nombre: str) -> E:
    entidad = repo.obtener(id)
    if entidad is None:
        raise NoEncontrado(f"No existe el {nombre} con id {id}")
    return entidad
