"""Bus de eventos y unidad de trabajo: los eventos se publican sólo si la operación se confirma."""

from dataclasses import dataclass

from flota.shared.application.eventos import BusEventos
from flota.shared.domain.eventos import Evento
from tests.fakes import UnidadDeTrabajoFake


@dataclass(frozen=True)
class Algo(Evento):
    numero: int


def test_publica_a_los_suscriptos_del_tipo():
    recibidos = []
    bus = BusEventos()
    bus.suscribir(Algo, recibidos.append)
    bus.publicar(Algo(1))
    assert recibidos == [Algo(1)]


def test_un_manejador_que_falla_no_frena_a_los_demas(caplog):
    recibidos = []
    bus = BusEventos()

    def roto(evento):
        raise RuntimeError("se rompió")

    bus.suscribir(Algo, roto)
    bus.suscribir(Algo, recibidos.append)
    bus.publicar(Algo(1))

    assert recibidos == [Algo(1)]
    assert "se rompió" in caplog.text


def test_los_eventos_se_publican_despues_del_commit():
    recibidos = []
    bus = BusEventos()
    bus.suscribir(Algo, recibidos.append)
    uow = UnidadDeTrabajoFake(bus)

    with uow:
        uow.registrar_evento(Algo(1))
        assert recibidos == []  # todavía no se confirmó
        uow.commit()
    assert recibidos == [Algo(1)]


def test_sin_commit_los_eventos_se_descartan():
    recibidos = []
    bus = BusEventos()
    bus.suscribir(Algo, recibidos.append)
    uow = UnidadDeTrabajoFake(bus)

    with uow:
        uow.registrar_evento(Algo(1))
        # error de negocio: no se llega al commit
    with uow:
        uow.commit()
    assert recibidos == []
