# app/routers/tracking_professional.py - VERSIÓN ACTUALIZADA CON DESCARGA DE REPORTES
"""
Router para sistema de tracking actualizado a usar de_clientes_rpa_v2
Incluye endpoint de descarga de reportes desde de_reportes_rpa
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import os

from app.services.tracking_professional import (
    get_paginas_activas,
    get_clientes_with_filters,
    update_cliente_estado,
    crear_proceso_completo,
    get_estadisticas,
    get_reporte_by_cliente,
    get_ruta_reporte
)

router = APIRouter(prefix="/tracking", tags=["tracking"])


# ===== MODELOS DE REQUEST =====

class ActualizarEstadoClienteRequest(BaseModel):
    estado: str = Field(..., description="Nuevo ESTADO_CONSULTA del cliente")
    mensaje_error: Optional[str] = Field(None, description="Mensaje de error opcional")


class CrearProcesoRequest(BaseModel):
    cliente_id: int = Field(..., description="ID del cliente en de_clientes_rpa_v2")
    paginas_codigos: List[str] = Field(..., min_length=1, description="Códigos de páginas a consultar")
    headless: bool = Field(False, description="Ejecutar en modo headless")
    generate_report: bool = Field(True, description="Generar reporte al finalizar")


# ===== ENDPOINTS BÁSICOS =====

@router.get("/health", summary="Health check del sistema")
def health_check() -> Dict[str, Any]:
    """Health check para verificar que el sistema de tracking funciona"""
    try:
        paginas = get_paginas_activas()
        
        return {
            "status": "healthy",
            "message": "Sistema de tracking funcionando correctamente",
            "timestamp": datetime.now().isoformat(),
            "paginas_disponibles": len(paginas),
            "tabla_clientes": "de_clientes_rpa_v2",
            "campos_disponibles": [
                "CEDULA", "NOMBRES_CLIENTE", "APELLIDOS_CLIENTE",
                "PRODUCTO", "AGENCIA", "ESTADO_CIVIL",
                "CEDULA_CONYUGE", "NOMBRES_CONYUGE", "APELLIDOS_CONYUGE",
                "CEDULA_CODEUDOR", "NOMBRES_CODEUDOR", "APELLIDOS_CODEUDOR"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sistema no saludable: {str(e)}")


@router.get("/paginas", summary="Listar páginas disponibles")
def listar_paginas_disponibles() -> List[Dict[str, Any]]:
    """
    Obtiene todas las páginas activas disponibles para consulta.
    Se usa para mostrar los checkboxes en el frontend.
    """
    try:
        return get_paginas_activas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo páginas: {str(e)}")


# ===== ENDPOINT PRINCIPAL DE CLIENTES =====

@router.get("/clientes", summary="Listar clientes de de_clientes_rpa_v2 con filtros")
def listar_clientes_con_filtros(
    estado: Optional[str] = Query(None, description="Filtrar por ESTADO_CONSULTA (Pendiente, En_Proceso, Procesado, Error)"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    q: Optional[str] = Query(None, description="Búsqueda en NOMBRES_CLIENTE, APELLIDOS_CLIENTE, CEDULA")
) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de clientes de de_clientes_rpa_v2 con filtros opcionales.
    
    Retorna campos:
    - id, ID_SOLICITUD, ESTADO, AGENCIA
    - CEDULA, NOMBRES_CLIENTE, APELLIDOS_CLIENTE, ESTADO_CIVIL
    - ESTADO_CONSULTA (Pendiente, En_Proceso, Procesado, Error)
    - FECHA_CREACION_SOLICITUD, FECHA_CREACION_REGISTRO
    - ID_PRODUCTO, PRODUCTO
    - CEDULA_CONYUGE, NOMBRES_CONYUGE, APELLIDOS_CONYUGE
    - CEDULA_CODEUDOR, NOMBRES_CODEUDOR, APELLIDOS_CODEUDOR
    """
    try:
        return get_clientes_with_filters(
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            q=q
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo clientes: {str(e)}")


# ===== ENDPOINT DE ACTUALIZACIÓN DE ESTADO =====

@router.put("/clientes/{cliente_id}/estado", summary="Actualizar ESTADO_CONSULTA de cliente")
def actualizar_estado_cliente(
    cliente_id: int,
    request: ActualizarEstadoClienteRequest
) -> Dict[str, Any]:
    """
    Actualiza el ESTADO_CONSULTA de un cliente en de_clientes_rpa_v2.
    
    Estados válidos: Pendiente, En_Proceso, Procesado, Error
    """
    try:
        success = update_cliente_estado(
            cliente_id=cliente_id,
            estado=request.estado,
            mensaje_error=request.mensaje_error
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Cliente no encontrado en de_clientes_rpa_v2")
        
        return {
            "success": True,
            "message": f"ESTADO_CONSULTA actualizado a {request.estado}",
            "cliente_id": cliente_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando cliente: {str(e)}")


# ===== ENDPOINTS DE REPORTES =====

@router.get("/clientes/{cliente_id}/reporte", summary="Obtener información del reporte de un cliente")
def obtener_reporte_cliente(cliente_id: int) -> Dict[str, Any]:
    """
    Obtiene la información del reporte más reciente de un cliente.
    """
    try:
        reporte = get_reporte_by_cliente(cliente_id)
        
        if not reporte:
            raise HTTPException(status_code=404, detail="No hay reporte disponible para este cliente")
        
        return {
            "success": True,
            "reporte": reporte
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo reporte: {str(e)}")


@router.get("/clientes/{cliente_id}/reporte/download", summary="Descargar reporte de un cliente")
def descargar_reporte_cliente(cliente_id: int):
    """
    Descarga el archivo DOCX del reporte más reciente de un cliente.
    """
    try:
        ruta = get_ruta_reporte(cliente_id)
        
        if not ruta:
            raise HTTPException(
                status_code=404, 
                detail="No hay reporte disponible para este cliente o el archivo no existe"
            )
        
        if not os.path.exists(ruta):
            raise HTTPException(
                status_code=404, 
                detail="El archivo del reporte no se encuentra en el servidor"
            )
        
        filename = os.path.basename(ruta)
        
        return FileResponse(
            path=ruta,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando reporte: {str(e)}")


# ===== ENDPOINT DE PROCESOS =====

@router.post("/procesos", summary="Crear proceso de consulta")
def crear_proceso(request: CrearProcesoRequest) -> Dict[str, Any]:
    """
    Crea un proceso completo de consulta para un cliente.
    
    El proceso incluirá una consulta para cada página especificada.
    """
    try:
        # Generar job_id único
        job_id = f"job_{datetime.now().timestamp()}"
        
        proceso_id = crear_proceso_completo(
            cliente_id=request.cliente_id,
            job_id=job_id,
            paginas_codigos=request.paginas_codigos,
            headless=request.headless,
            generate_report=request.generate_report
        )
        
        return {
            "success": True,
            "proceso_id": proceso_id,
            "job_id": job_id,
            "cliente_id": request.cliente_id,
            "paginas_solicitadas": request.paginas_codigos,
            "message": "Proceso creado exitosamente"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando proceso: {str(e)}")


# ===== ENDPOINT DE ESTADÍSTICAS =====

@router.get("/estadisticas", summary="Obtener estadísticas del sistema")
def obtener_estadisticas(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Obtiene estadísticas del sistema incluyendo:
    - Contadores de clientes por estado
    - Contadores de procesos
    """
    try:
        return get_estadisticas(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")