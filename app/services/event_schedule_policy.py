"""Regla de anticipación mínima para programar eventos escolares (issue #44).

El inicio de un evento solo se acepta si ocurre a partir de
``ahora_del_servidor + margen``, donde el margen vive en la configuración global
(``settings.event_min_lead_time_minutes``) y, a falta de configuración válida,
son cinco minutos.

El cliente no participa en el cálculo: ni envía el margen ni aporta el reloj de
referencia. El error resultante identifica el campo ``init_time`` pero no revela
el margen ni el instante mínimo permitido.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.exceptions import FieldValidationError
from app.schemas.enums import SettingKey
from app.services.settings_service import settings_service

logger = logging.getLogger(__name__)

#: Identificador estable del error que consume el frontend. No cambia aunque
#: cambie el texto del mensaje.
EVENT_SCHEDULE_ERROR_TYPE = "event_schedule_unavailable"

#: Mensaje genérico mostrado junto al campo Hora. No revela el margen vigente.
EVENT_SCHEDULE_ERROR_MESSAGE = (
    "El horario seleccionado no está disponible. Por favor, elige otro horario."
)

#: Ruta del campo responsable dentro del cuerpo de la petición.
EVENT_SCHEDULE_ERROR_LOC = ("body", "init_time")


def _now_utc() -> datetime:
    """Reloj del servidor en UTC.

    Aislado en una función para poder congelarlo en las pruebas.

    Returns:
        datetime: Instante actual con zona horaria UTC.
    """
    return datetime.now(timezone.utc)


def to_utc(value: datetime) -> datetime:
    """Normaliza un ``datetime`` a UTC para poder comparar instantes.

    Un valor sin zona horaria se interpreta como UTC: el saneamiento general de
    offsets en los eventos pertenece al issue #9 y no se duplica aquí.

    Args:
        value: Fecha y hora recibida del cliente, con o sin offset.

    Returns:
        datetime: El mismo instante expresado en UTC.
    """
    if value.tzinfo is None:
        logger.warning(
            "init_time recibido sin zona horaria; se interpreta como UTC (ver issue #9)."
        )
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ceil_to_minute(value: datetime) -> datetime:
    """Redondea un instante hacia arriba hasta el siguiente minuto exacto.

    La interfaz solo permite elegir horas con precisión de minutos, así que el
    umbral se eleva al siguiente minuto permitido cuando el reloj del servidor
    trae segundos: a las 15:00:30 con cinco minutos de margen, el primer inicio
    aceptable es 15:06, no 15:05.

    Args:
        value: Instante a redondear.

    Returns:
        datetime: El mismo instante si ya cae en un minuto exacto; el siguiente
        minuto exacto en caso contrario.
    """
    if value.second or value.microsecond:
        return (value + timedelta(minutes=1)).replace(second=0, microsecond=0)
    return value


def get_min_lead_time_minutes() -> int:
    """Devuelve el margen de anticipación vigente, en minutos.

    Returns:
        int: Valor configurado en ``settings``, o cinco minutos si no hay
        configuración válida.
    """
    return settings_service.get_int(SettingKey.EVENT_MIN_LEAD_TIME_MINUTES)


def minimum_allowed_start(now: datetime | None = None) -> datetime:
    """Calcula el primer instante de inicio aceptable.

    Args:
        now: Instante de referencia. Por defecto, el reloj del servidor en UTC.

    Returns:
        datetime: ``now + margen``, redondeado al siguiente minuto exacto.
    """
    reference = now or _now_utc()
    return _ceil_to_minute(reference + timedelta(minutes=get_min_lead_time_minutes()))


def validate_lead_time(init_time: datetime) -> None:
    """Rechaza un inicio de evento que no respete la anticipación mínima.

    Debe invocarse antes de insertar o modificar nada, de modo que un horario
    rechazado no deje eventos ni participaciones creados.

    Args:
        init_time: Fecha y hora de inicio propuesta por el cliente.

    Raises:
        FieldValidationError: 422 asociado a ``body.init_time`` con el tipo
            ``event_schedule_unavailable``. Ni el mensaje ni los metadatos
            revelan el margen vigente ni el umbral calculado.
    """
    threshold = minimum_allowed_start()
    if to_utc(init_time) < threshold:
        logger.info(
            "Inicio de evento rechazado por anticipación insuficiente (umbral interno: %s).",
            threshold.isoformat(),
        )
        raise FieldValidationError(
            loc=EVENT_SCHEDULE_ERROR_LOC,
            msg=EVENT_SCHEDULE_ERROR_MESSAGE,
            error_type=EVENT_SCHEDULE_ERROR_TYPE,
        )
