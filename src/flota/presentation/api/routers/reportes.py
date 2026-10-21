from datetime import date
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response

from flota.application.use_cases.reportes import ExportarReporteConsumo, GenerarReporteConsumo
from flota.infrastructure.excel.generador_excel import crear_plantilla_importacion
from flota.presentation.api.dependencias import Config, Generador, UoW
from flota.presentation.api.schemas import ReporteLeer

router = APIRouter(tags=["Reportes"])
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _respuesta_excel(contenido: bytes, nombre: str) -> Response:
    return Response(
        contenido,
        media_type=MIME_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/reportes/consumo", response_model=ReporteLeer)
def reporte_consumo(
    uow: UoW, config: Config, desde: date, hasta: date, camion_id: UUID | None = None
):
    reporte = GenerarReporteConsumo(uow, config.umbral_desvio_pct).ejecutar(desde, hasta, camion_id)
    return ReporteLeer.model_validate(reporte)


@router.get("/reportes/consumo.xlsx", response_class=Response)
def reporte_consumo_excel(
    uow: UoW,
    config: Config,
    generador: Generador,
    desde: date,
    hasta: date,
    camion_id: UUID | None = None,
):
    buffer = BytesIO()
    generar = GenerarReporteConsumo(uow, config.umbral_desvio_pct)
    ExportarReporteConsumo(generar, generador).ejecutar(desde, hasta, buffer, camion_id)
    return _respuesta_excel(buffer.getvalue(), f"consumo_{desde}_{hasta}.xlsx")


@router.get("/plantillas/importacion.xlsx", response_class=Response)
def plantilla_importacion():
    buffer = BytesIO()
    crear_plantilla_importacion(buffer)
    return _respuesta_excel(buffer.getvalue(), "plantilla_cargas.xlsx")
