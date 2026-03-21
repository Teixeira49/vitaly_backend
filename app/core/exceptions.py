from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.responses import APIResponse, ErrorDetail

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [ErrorDetail(loc=err["loc"], msg=err["msg"], type=err["type"]) for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(success=False, message="Validation error", errors=errors).model_dump()
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(success=False, message=str(exc.detail)).model_dump()
    )
