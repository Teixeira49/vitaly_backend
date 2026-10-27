"""Lectura y escritura de la configuración global del sistema (tabla ``settings``).

El alcance de esta tabla es **global**: no tiene ``school_id`` y, por tanto, no
participa del aislamiento multi-tenant. Solo el rol ``admin_sistema`` puede
modificarla a través de ``/api/v1/admin/settings``.

Principio de diseño: **la configuración nunca desactiva una barrera de negocio**.
Si la fila no existe, está borrada lógicamente, tiene un tipo que no corresponde
o un valor fuera de rango, la lectura cae al valor por defecto declarado en
:data:`SETTING_SPECS` y deja constancia en el log.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException

from app.core.database import supabase
from app.schemas.enums import SettingKey, SettingValueType

logger = logging.getLogger(__name__)

#: Minutos de anticipación aplicados cuando no hay configuración válida (issue #44).
EVENT_MIN_LEAD_TIME_FALLBACK_MINUTES = 5

#: Techo del margen configurable: 7 días expresados en minutos.
EVENT_MIN_LEAD_TIME_MAX_MINUTES = 10080


@dataclass(frozen=True)
class SettingSpec:
    """Contrato de una clave de configuración: tipo, rango y valor por defecto.

    Es la única fuente de verdad para ambos extremos: la lectura cae a
    ``default`` cuando el valor almacenado no la cumple, y la escritura del
    administrador de sistema se rechaza cuando no la cumple.

    Attributes:
        value_type: Tipo de dato admitido para la clave.
        default: Valor aplicado si no hay configuración válida almacenada.
        minimum: Cota inferior inclusiva. Solo para tipos numéricos.
        maximum: Cota superior inclusiva. Solo para tipos numéricos.
        description: Texto sembrado en la columna ``description``.
    """

    value_type: SettingValueType
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    description: Optional[str] = None


#: Claves de configuración soportadas y sus reglas de validación.
SETTING_SPECS: dict[SettingKey, SettingSpec] = {
    SettingKey.EVENT_MIN_LEAD_TIME_MINUTES: SettingSpec(
        value_type=SettingValueType.INTEGER,
        default=EVENT_MIN_LEAD_TIME_FALLBACK_MINUTES,
        minimum=0,
        maximum=EVENT_MIN_LEAD_TIME_MAX_MINUTES,
        description=(
            "Minutos mínimos de anticipación con los que debe programarse el inicio de un "
            "evento escolar, medidos contra el reloj del servidor. Rango válido: 0 a "
            f"{EVENT_MIN_LEAD_TIME_MAX_MINUTES} (7 días). Sin configuración válida se aplican "
            f"{EVENT_MIN_LEAD_TIME_FALLBACK_MINUTES} minutos."
        ),
    ),
}


class SettingsService:
    """Operaciones sobre la configuración global del sistema."""

    # ──────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────

    def _fetch_row(self, key: SettingKey) -> Optional[dict]:
        """Lee la fila vigente de una clave de configuración.

        Args:
            key: Clave a consultar.

        Returns:
            dict | None: Fila de ``settings`` si existe y no está borrada
            lógicamente; ``None`` si no hay configuración almacenada o si la
            consulta falló (el fallo se registra, no se propaga).
        """
        try:
            response = (
                supabase.table("settings")
                .select("key, value, description, updated_at")
                .eq("key", key.value)
                .eq("is_deleted", False)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception(
                "Error al leer la configuración '%s'; se usará el valor por defecto.", key.value
            )
            return None
        return response.data[0] if response.data else None

    def _coerce(self, key: SettingKey, spec: SettingSpec, raw_value: Any) -> Optional[Any]:
        """Valida el JSON almacenado contra el contrato de la clave.

        Args:
            key: Clave de configuración, solo para el mensaje de log.
            spec: Contrato que debe cumplir el valor.
            raw_value: Contenido de la columna ``value``, se espera
                ``{"type": ..., "value": ...}``.

        Returns:
            Any | None: El dato ya tipado, o ``None`` si el JSON está malformado,
            el tipo declarado no coincide o el valor queda fuera de rango.
        """
        if not isinstance(raw_value, dict) or "type" not in raw_value or "value" not in raw_value:
            logger.warning(
                "Configuración '%s' malformada (se esperaba {'type', 'value'}): %r",
                key.value, raw_value,
            )
            return None

        if raw_value["type"] != spec.value_type.value:
            logger.warning(
                "Configuración '%s' declara tipo '%s' pero se esperaba '%s'.",
                key.value, raw_value["type"], spec.value_type.value,
            )
            return None

        value = raw_value["value"]

        if spec.value_type is SettingValueType.INTEGER:
            # bool es subclase de int en Python: no se acepta como entero.
            if isinstance(value, bool) or not isinstance(value, int):
                logger.warning(
                    "Configuración '%s' no contiene un entero: %r", key.value, value
                )
                return None
        elif spec.value_type is SettingValueType.NUMBER:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                logger.warning("Configuración '%s' no contiene un número: %r", key.value, value)
                return None
        elif spec.value_type is SettingValueType.STRING:
            if not isinstance(value, str):
                logger.warning("Configuración '%s' no contiene un texto: %r", key.value, value)
                return None
        elif spec.value_type is SettingValueType.BOOLEAN:
            if not isinstance(value, bool):
                logger.warning("Configuración '%s' no contiene un booleano: %r", key.value, value)
                return None
        elif spec.value_type is SettingValueType.JSON:
            if not isinstance(value, (dict, list)):
                logger.warning(
                    "Configuración '%s' no contiene un objeto ni un arreglo: %r", key.value, value
                )
                return None

        if spec.minimum is not None and value < spec.minimum:
            logger.warning(
                "Configuración '%s' por debajo del mínimo (%s < %s).",
                key.value, value, spec.minimum,
            )
            return None
        if spec.maximum is not None and value > spec.maximum:
            logger.warning(
                "Configuración '%s' por encima del máximo (%s > %s).",
                key.value, value, spec.maximum,
            )
            return None

        return value

    def _as_read_row(self, key: SettingKey, spec: SettingSpec, row: Optional[dict]) -> dict:
        """Compone la representación de una configuración para la API.

        Muestra siempre el valor **que el sistema está aplicando**: si la fila no
        existe, o existe pero su JSON no cumple el contrato (algo que los CHECK
        de la migración ya impiden), devuelve el valor por defecto en lugar de
        romper la respuesta.

        Args:
            key: Clave representada.
            spec: Contrato de la clave.
            row: Fila almacenada, o ``None`` si no hay ninguna.

        Returns:
            dict: ``key``, ``value``, ``description`` y ``updated_at``.
        """
        if row is not None and self._coerce(key, spec, row.get("value")) is not None:
            return row
        if row is not None:
            logger.warning(
                "La fila de '%s' no cumple su contrato; se reporta el valor por defecto.",
                key.value,
            )
        return {
            "key": key.value,
            "value": {"type": spec.value_type.value, "value": spec.default},
            "description": (row or {}).get("description") or spec.description,
            "updated_at": (row or {}).get("updated_at"),
        }

    # ──────────────────────────────────────────────────────────
    # Lectura usada por la lógica de negocio
    # ──────────────────────────────────────────────────────────

    def get_value(self, key: SettingKey) -> Any:
        """Devuelve el valor vigente de una configuración, o su valor por defecto.

        Nunca lanza: cualquier problema (fila ausente, JSON malformado, tipo o
        rango inválidos, error de la base de datos) se registra en el log y se
        resuelve con el valor por defecto del contrato, de modo que la barrera de
        negocio asociada siga activa.

        Args:
            key: Clave a resolver.

        Returns:
            Any: Valor tipado de la configuración.

        Raises:
            KeyError: Si la clave no está declarada en :data:`SETTING_SPECS`
                (error de programación, no de datos).
        """
        spec = SETTING_SPECS[key]
        row = self._fetch_row(key)
        if row is None:
            return spec.default

        value = self._coerce(key, spec, row.get("value"))
        return spec.default if value is None else value

    def get_int(self, key: SettingKey) -> int:
        """Atajo tipado de :meth:`get_value` para configuraciones enteras.

        Args:
            key: Clave a resolver, declarada con ``SettingValueType.INTEGER``.

        Returns:
            int: Valor entero vigente o su valor por defecto.
        """
        return int(self.get_value(key))

    # ──────────────────────────────────────────────────────────
    # Administración (rol admin_sistema)
    # ──────────────────────────────────────────────────────────

    def list_settings(self) -> list[dict]:
        """Lista todas las configuraciones vigentes del sistema.

        Las claves declaradas en :data:`SETTING_SPECS` que aún no tienen fila se
        incluyen con su valor por defecto, para que el administrador vea el
        catálogo completo y no solo lo ya persistido.

        Returns:
            list[dict]: Filas con ``key``, ``value``, ``description`` y
            ``updated_at``. Nunca es ``None``; puede estar vacía solo si no hay
            claves declaradas.

        Raises:
            HTTPException: 500 si la consulta a la base de datos falla.
        """
        try:
            response = (
                supabase.table("settings")
                .select("key, value, description, updated_at")
                .eq("is_deleted", False)
                .execute()
            )
        except Exception:
            logger.exception("Error al listar las configuraciones del sistema.")
            raise HTTPException(
                status_code=500, detail="Ocurrió un error al consultar la configuración."
            )

        stored = {row["key"]: row for row in (response.data or [])}
        return [
            self._as_read_row(key, spec, stored.get(key.value))
            for key, spec in SETTING_SPECS.items()
        ]

    def get_setting(self, key: SettingKey) -> dict:
        """Devuelve una configuración concreta para el administrador de sistema.

        Args:
            key: Clave a consultar.

        Returns:
            dict: ``key``, ``value``, ``description`` y ``updated_at``. Si la
            clave aún no tiene fila, devuelve su valor por defecto con
            ``updated_at`` en ``None``.
        """
        spec = SETTING_SPECS[key]
        return self._as_read_row(key, spec, self._fetch_row(key))

    def upsert_setting(
        self,
        key: SettingKey,
        value_type: SettingValueType,
        value: Any,
        description: Optional[str] = None,
    ) -> dict:
        """Crea o actualiza el valor de una configuración declarada.

        A diferencia de la lectura, aquí los datos inválidos **se rechazan**: el
        administrador debe recibir el motivo exacto, incluido el rango admitido.

        Args:
            key: Clave a escribir. Debe estar declarada en :data:`SETTING_SPECS`.
            value_type: Tipo declarado por el cliente para el valor.
            value: Dato a persistir.
            description: Descripción a guardar. Si se omite, conserva la
                existente o siembra la del contrato.

        Returns:
            dict: Fila resultante con ``key``, ``value``, ``description`` y
            ``updated_at``.

        Raises:
            HTTPException: 400 si el tipo no coincide con el declarado para la
                clave, o si el valor queda fuera del rango admitido.
            HTTPException: 500 si la escritura en la base de datos falla.
        """
        spec = SETTING_SPECS[key]

        if value_type is not spec.value_type:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La configuración '{key.value}' es de tipo '{spec.value_type.value}'; "
                    f"se recibió '{value_type.value}'."
                ),
            )

        candidate = {"type": value_type.value, "value": value}
        if self._coerce(key, spec, candidate) is None:
            raise HTTPException(
                status_code=400,
                detail=self._invalid_value_message(key, spec),
            )

        existing = self._fetch_row(key)
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "key": key.value,
            "value": candidate,
            "description": description
            or (existing or {}).get("description")
            or spec.description,
            "updated_at": now,
        }

        try:
            if existing is None:
                result = supabase.table("settings").insert(row).execute()
            else:
                result = (
                    supabase.table("settings")
                    .update({k: v for k, v in row.items() if k != "key"})
                    .eq("key", key.value)
                    .execute()
                )
        except Exception:
            logger.exception("Error al guardar la configuración '%s'.", key.value)
            raise HTTPException(
                status_code=500, detail="Ocurrió un error al guardar la configuración."
            )

        if not result.data:
            raise HTTPException(
                status_code=500, detail="Ocurrió un error al guardar la configuración."
            )
        logger.info("Configuración '%s' actualizada a %r.", key.value, candidate)
        return result.data[0]

    def _invalid_value_message(self, key: SettingKey, spec: SettingSpec) -> str:
        """Compone el mensaje de rechazo de un valor inválido para el administrador.

        Args:
            key: Clave rechazada.
            spec: Contrato incumplido.

        Returns:
            str: Mensaje con el tipo esperado y, si aplica, el rango admitido.
        """
        detail = f"El valor de '{key.value}' debe ser de tipo '{spec.value_type.value}'"
        if spec.minimum is not None and spec.maximum is not None:
            detail += f" y estar entre {spec.minimum:g} y {spec.maximum:g}"
        elif spec.minimum is not None:
            detail += f" y ser mayor o igual a {spec.minimum:g}"
        elif spec.maximum is not None:
            detail += f" y ser menor o igual a {spec.maximum:g}"
        return detail + "."


#: Instancia compartida del servicio, importada por servicios y endpoints.
settings_service = SettingsService()
