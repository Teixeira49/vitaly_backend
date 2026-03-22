from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.database import supabase
from app.schemas.responses import APIResponse
from app.schemas.academic_year import AcademicYearCreate

router = APIRouter()

@router.post("", response_model=APIResponse[dict])
def create_academic_year(payload: AcademicYearCreate):
    """
    Crea un nuevo año académico.
    Genera el nombre automáticamente: 'Año escolar [init-year]-[end-year]'.
    Calcula isCurrent si la fecha actual está entre el inicio y el cierre del año.
    No requiere protección con JWT.
    """
    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=400, detail="La fecha de inicio debe ser menor a la fecha de cierre.")

    name = f"Año escolar {payload.start_date.year}-{payload.end_date.year}"
    
    current_date = date.today()
    is_current = payload.start_date <= current_date <= payload.end_date
    
    data = {
        "name": name,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "is_current": is_current,
        "is_active": True,
        "is_deleted": False
    }
    
    try:
        response = supabase.table("academic_year").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="No se devolvieron datos al insertar el año académico.")
            
        return APIResponse(data=response.data[0], message="Año académico creado exitosamente")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el año académico: {str(e)}")

@router.patch("/sync-current", response_model=APIResponse[dict])
def sync_current_academic_years():
    """
    Sincroniza el estado 'is_current' de todos los años académicos.
    Si la fecha actual (hoy) se encuentra dentro del rango de start_date 
    y end_date, pasa el is_current a True, de lo contrario pasa a False.
    No requiere JWT.
    """
    current_date = date.today()
    current_date_str = current_date.isoformat()
    
    try:
        response = supabase.table("academic_year").select("id, start_date, end_date, is_current").execute()
        years = response.data
        
        if not years:
            return APIResponse(
                data={"updated_records": 0, "current_date": current_date_str}, 
                message="No se encontraron registros de años académicos para sincronizar."
            )
            
        updated_count = 0
        for year in years:
            start_date_str = year.get("start_date")
            end_date_str = year.get("end_date")
            
            if not start_date_str or not end_date_str:
                continue
                
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            
            # Calculamos si debería ser True o False
            expected_current = start_date <= current_date <= end_date
            
            # Actualizamos solo si hubo cambio en el estado
            if year.get("is_current") != expected_current:
                supabase.table("academic_year").update({"is_current": expected_current}).eq("id", year["id"]).execute()
                updated_count += 1
                
        return APIResponse(
            data={"updated_records": updated_count, "current_date": current_date_str}, 
            message="Sincronización de años académicos completada."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al sincronizar años académicos: {str(e)}")
