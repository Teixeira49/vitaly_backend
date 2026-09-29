import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_admin_escuela
from app.services.imagekit_service import ImageKitService
from app.services.school_admin_service import school_admin_service


def test_imagekit_service_raises_500_when_key_missing(monkeypatch):
    """Verifica que ImageKitService falle con 500 si la clave privada no está configurada."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "IMAGEKIT_PRIVATE_KEY", None)

    service = ImageKitService()
    with pytest.raises(HTTPException) as exc_info:
        service.upload_profile_image(
            file_bytes=b"test",
            original_filename="avatar.png",
            user_id=1
        )
    assert exc_info.value.status_code == 500
    assert "no está configurado" in exc_info.value.detail


def test_imagekit_service_uploads_successfully(monkeypatch):
    """Verifica que ImageKitService llame correctamente al cliente de ImageKit."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "IMAGEKIT_PRIVATE_KEY", "test_private_key")

    service = ImageKitService()

    mock_client = MagicMock()
    mock_upload_resp = MagicMock()
    mock_upload_resp.url = "https://ik.imagekit.io/vitaly/profiles/user_1_abc.png"
    mock_client.files.upload.return_value = mock_upload_resp

    with patch.object(service, "_get_client", return_value=mock_client):
        url = service.upload_profile_image(
            file_bytes=b"test_image_bytes",
            original_filename="my_photo.PNG",
            user_id=1,
            folder="/vitaly/profiles"
        )
        assert url == "https://ik.imagekit.io/vitaly/profiles/user_1_abc.png"
        mock_client.files.upload.assert_called_once()
        call_kwargs = mock_client.files.upload.call_args[1]
        assert call_kwargs["file"] == b"test_image_bytes"
        assert call_kwargs["folder"] == "/vitaly/profiles"
        assert call_kwargs["file_name"].startswith("user_1_")
        assert call_kwargs["file_name"].endswith(".png")


def test_upload_my_profile_photo_invalid_mimetype():
    """Valida que se rechacen archivos que no sean imágenes JPEG, PNG o WebP."""
    with pytest.raises(HTTPException) as exc_info:
        school_admin_service.upload_my_profile_photo(
            user_id=1,
            file_bytes=b"%PDF-1.4",
            filename="document.pdf",
            content_type="application/pdf"
        )
    assert exc_info.value.status_code == 400
    assert "Formato no permitido" in exc_info.value.detail


def test_upload_my_profile_photo_empty_file():
    """Valida que se rechace un archivo con contenido vacío."""
    with pytest.raises(HTTPException) as exc_info:
        school_admin_service.upload_my_profile_photo(
            user_id=1,
            file_bytes=b"",
            filename="empty.png",
            content_type="image/png"
        )
    assert exc_info.value.status_code == 400
    assert "está vacío" in exc_info.value.detail


def test_upload_my_profile_photo_exceeds_size():
    """Valida que se rechacen archivos que superen los 5MB."""
    oversized = b"0" * (5 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc_info:
        school_admin_service.upload_my_profile_photo(
            user_id=1,
            file_bytes=oversized,
            filename="large.jpg",
            content_type="image/jpeg"
        )
    assert exc_info.value.status_code == 400
    assert "tamaño máximo" in exc_info.value.detail


def test_upload_my_profile_photo_success():
    """Valida el flujo exitoso en school_admin_service: subida a ImageKit y update en DB."""
    fake_url = "https://ik.imagekit.io/vitaly/profiles/user_4_test.jpg"

    with patch("app.services.school_admin_service.imagekit_service.upload_profile_image", return_value=fake_url):
        with patch("app.services.school_admin_service.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_update = MagicMock()
            mock_table.update.return_value = mock_update
            mock_eq = MagicMock()
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = MagicMock(data=[{"id": 4, "photo_url": fake_url}])

            res = school_admin_service.upload_my_profile_photo(
                user_id=4,
                file_bytes=b"\xff\xd8\xff\xe0",
                filename="photo.jpg",
                content_type="image/jpeg"
            )

            assert res == {"photo_url": fake_url}
            mock_table.update.assert_called_once_with({"photo_url": fake_url})
            mock_update.eq.assert_called_once_with("id", 4)


def test_endpoint_upload_profile_photo():
    """Valida el endpoint POST /api/v1/school-admin/profile/photo con autenticación mockeada."""
    client = TestClient(app)
    fake_url = "https://ik.imagekit.io/vitaly/profiles/user_4_uploaded.webp"

    # Sobrescribir dependencia get_current_admin_escuela
    app.dependency_overrides[get_current_admin_escuela] = lambda: {
        "sub": "4",
        "role": "admin_escuela"
    }

    try:
        with patch.object(
            school_admin_service,
            "upload_my_profile_photo",
            return_value={"photo_url": fake_url}
        ) as mock_service_call:
            files = {
                "file": ("avatar.webp", io.BytesIO(b"fake_webp_bytes"), "image/webp")
            }
            response = client.post("/api/v1/school-admin/profile/photo", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["photo_url"] == fake_url
            assert "Foto de perfil subida y actualizada exitosamente" in data["message"]

            mock_service_call.assert_called_once_with(
                user_id=4,
                file_bytes=b"fake_webp_bytes",
                filename="avatar.webp",
                content_type="image/webp"
            )
    finally:
        app.dependency_overrides.clear()


def test_delete_my_profile_photo_success():
    """Valida el método delete_my_profile_photo de school_admin_service."""
    with patch("app.services.school_admin_service.supabase") as mock_supabase:
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq = MagicMock()
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=[{"id": 4, "photo_url": None}])

        res = school_admin_service.delete_my_profile_photo(user_id=4)
        assert res == {"photo_url": None}
        mock_table.update.assert_called_once_with({"photo_url": None})
        mock_update.eq.assert_called_once_with("id", 4)


def test_endpoint_delete_profile_photo():
    """Valida el endpoint DELETE /api/v1/school-admin/profile/photo."""
    client = TestClient(app)

    app.dependency_overrides[get_current_admin_escuela] = lambda: {
        "sub": "4",
        "role": "admin_escuela"
    }

    try:
        with patch.object(
            school_admin_service,
            "delete_my_profile_photo",
            return_value={"photo_url": None}
        ) as mock_delete:
            response = client.delete("/api/v1/school-admin/profile/photo")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["photo_url"] is None
            assert "eliminada exitosamente" in data["message"]

            mock_delete.assert_called_once_with(user_id=4)
    finally:
        app.dependency_overrides.clear()

