import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_admin_escuela
from app.services import profile_photo_service
from app.services.imagekit_service import ImageKitService, UploadedImage
from app.services.school_admin_service import school_admin_service


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP_BYTES = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32
HTML_BYTES = b"<!DOCTYPE html><html><script>alert(1)</script></html>"


def _mock_user_table(mock_supabase, current_file_id=None, update_data=None):
    """Wire a MagicMock supabase so select/update on 'user' return the given data."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"photo_file_id": current_file_id}]
    )
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=update_data if update_data is not None else [{"id": 4}]
    )
    return mock_table


@pytest.fixture
def admin_client():
    app.dependency_overrides[get_current_admin_escuela] = lambda: {"sub": "4", "role": "admin_escuela"}
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────
# ImageKitService
# ──────────────────────────────────────────────────────────

def test_imagekit_service_raises_500_when_key_missing(monkeypatch):
    """ImageKitService fails with 500 when the private key is not configured."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "IMAGEKIT_PRIVATE_KEY", None)

    service = ImageKitService()
    with pytest.raises(HTTPException) as exc_info:
        service.upload_profile_image(file_bytes=b"test", extension="png", user_id=1, folder="/vitaly/profiles")
    assert exc_info.value.status_code == 500
    assert "no está configurado" in exc_info.value.detail


def test_imagekit_client_is_built_with_timeout(monkeypatch):
    """The ImageKit client is constructed with the configured timeout and retries."""
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "IMAGEKIT_PRIVATE_KEY", "test_private_key")
    monkeypatch.setattr(get_settings(), "IMAGEKIT_TIMEOUT_SECONDS", 7.5)
    monkeypatch.setattr(get_settings(), "IMAGEKIT_MAX_RETRIES", 1)

    with patch("app.services.imagekit_service.ImageKit") as mock_ctor:
        ImageKitService()._get_client()
        mock_ctor.assert_called_once_with(private_key="test_private_key", timeout=7.5, max_retries=1)


def test_imagekit_service_uploads_successfully(monkeypatch):
    """Upload returns url + file_id and names the file from the given extension."""
    service = ImageKitService()
    mock_client = MagicMock()
    mock_client.files.upload.return_value = MagicMock(
        url="https://ik.imagekit.io/vitaly/profiles/user_1_abc.png", file_id="file_abc"
    )

    with patch.object(service, "_get_client", return_value=mock_client):
        result = service.upload_profile_image(
            file_bytes=PNG_BYTES, extension="png", user_id=1, folder="/vitaly/profiles"
        )

    assert result == UploadedImage(url="https://ik.imagekit.io/vitaly/profiles/user_1_abc.png", file_id="file_abc")
    call_kwargs = mock_client.files.upload.call_args[1]
    assert call_kwargs["file"] == PNG_BYTES
    assert call_kwargs["folder"] == "/vitaly/profiles"
    assert call_kwargs["file_name"].startswith("user_1_")
    assert call_kwargs["file_name"].endswith(".png")


def test_imagekit_upload_error_does_not_leak_exception_details():
    """A failed upload returns a generic 502 without the underlying error text."""
    service = ImageKitService()
    mock_client = MagicMock()
    mock_client.files.upload.side_effect = RuntimeError("secret-internal-detail")

    with patch.object(service, "_get_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            service.upload_profile_image(file_bytes=PNG_BYTES, extension="png", user_id=1, folder="/x")

    assert exc_info.value.status_code == 502
    assert "secret-internal-detail" not in exc_info.value.detail


def test_imagekit_delete_file_is_best_effort():
    """delete_file swallows errors and is a no-op for empty ids."""
    service = ImageKitService()
    mock_client = MagicMock()
    mock_client.files.delete.side_effect = RuntimeError("boom")

    with patch.object(service, "_get_client", return_value=mock_client):
        service.delete_file("file_123", user_id=4)  # must not raise
        service.delete_file(None)

    mock_client.files.delete.assert_called_once_with("file_123")


# ──────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "file_bytes,content_type,expected_ext",
    [
        (JPEG_BYTES, "image/jpeg", "jpg"),
        (JPEG_BYTES, "image/jpg", "jpg"),
        (PNG_BYTES, "image/png", "png"),
        (WEBP_BYTES, "image/webp", "webp"),
    ],
)
def test_validate_accepts_real_images(file_bytes, content_type, expected_ext):
    assert profile_photo_service.validate_profile_photo(file_bytes, content_type) == expected_ext


def test_upload_my_profile_photo_invalid_mimetype():
    """Rejects declared content types other than JPEG, PNG or WebP."""
    with pytest.raises(HTTPException) as exc_info:
        school_admin_service.upload_my_profile_photo(
            user_id=1, file_bytes=b"%PDF-1.4", content_type="application/pdf"
        )
    assert exc_info.value.status_code == 400
    assert "Formato no permitido" in exc_info.value.detail


def test_upload_rejects_spoofed_content_type():
    """HTML bytes declared as image/png are rejected by the magic-byte check."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik:
        with pytest.raises(HTTPException) as exc_info:
            school_admin_service.upload_my_profile_photo(
                user_id=1, file_bytes=HTML_BYTES, content_type="image/png"
            )
    assert exc_info.value.status_code == 400
    assert "Formato no permitido" in exc_info.value.detail
    mock_ik.upload_profile_image.assert_not_called()


def test_upload_rejects_content_type_mismatch():
    """PNG bytes declared as image/jpeg are rejected."""
    with pytest.raises(HTTPException) as exc_info:
        profile_photo_service.validate_profile_photo(PNG_BYTES, "image/jpeg")
    assert exc_info.value.status_code == 400


def test_upload_my_profile_photo_empty_file():
    """Rejects an empty file."""
    with pytest.raises(HTTPException) as exc_info:
        school_admin_service.upload_my_profile_photo(user_id=1, file_bytes=b"", content_type="image/png")
    assert exc_info.value.status_code == 400
    assert "está vacío" in exc_info.value.detail


def test_upload_my_profile_photo_exceeds_size():
    """Rejects files over 5 MB."""
    oversized = JPEG_BYTES + b"0" * profile_photo_service.MAX_PROFILE_PHOTO_BYTES
    with pytest.raises(HTTPException) as exc_info:
        school_admin_service.upload_my_profile_photo(user_id=1, file_bytes=oversized, content_type="image/jpeg")
    assert exc_info.value.status_code == 400
    assert "tamaño máximo" in exc_info.value.detail


def test_read_upload_capped_reads_at_most_limit_plus_one():
    stream = io.BytesIO(b"0" * (profile_photo_service.MAX_PROFILE_PHOTO_BYTES + 1000))
    data = profile_photo_service.read_upload_capped(stream)
    assert len(data) == profile_photo_service.MAX_PROFILE_PHOTO_BYTES + 1


# ──────────────────────────────────────────────────────────
# ImageKit / DB lifecycle (shared service via school admin)
# ──────────────────────────────────────────────────────────

def test_upload_my_profile_photo_success_first_photo():
    """Uploads to the school admin folder, stores url + file_id, deletes nothing."""
    uploaded = UploadedImage(url="https://ik.imagekit.io/vitaly/profiles/user_4_test.jpg", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        mock_table = _mock_user_table(mock_supabase, current_file_id=None)

        res = school_admin_service.upload_my_profile_photo(
            user_id=4, file_bytes=JPEG_BYTES, content_type="image/jpeg"
        )

    assert res == {"photo_url": uploaded.url}
    mock_ik.upload_profile_image.assert_called_once_with(
        file_bytes=JPEG_BYTES, extension="jpg", user_id=4, folder="/vitaly/profiles"
    )
    mock_table.update.assert_called_once_with({"photo_url": uploaded.url, "photo_file_id": "new_id"})
    mock_table.update.return_value.eq.assert_called_once_with("id", 4)
    mock_ik.delete_file.assert_not_called()


def test_upload_replaces_and_deletes_old_file():
    """When a previous photo exists, its ImageKit file is deleted after the DB update."""
    uploaded = UploadedImage(url="https://ik.imagekit.io/new.png", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        _mock_user_table(mock_supabase, current_file_id="old_id")

        school_admin_service.upload_my_profile_photo(user_id=4, file_bytes=PNG_BYTES, content_type="image/png")

    mock_ik.delete_file.assert_called_once_with("old_id", user_id=4)


def test_upload_deletes_new_file_when_db_update_returns_no_rows():
    """If the DB update affects no rows, the new ImageKit file is rolled back."""
    uploaded = UploadedImage(url="https://ik.imagekit.io/new.png", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        _mock_user_table(mock_supabase, current_file_id="old_id", update_data=[])

        with pytest.raises(HTTPException) as exc_info:
            school_admin_service.upload_my_profile_photo(user_id=4, file_bytes=PNG_BYTES, content_type="image/png")

    assert exc_info.value.status_code == 400
    mock_ik.delete_file.assert_called_once_with("new_id", user_id=4)


def test_upload_db_update_raises_returns_500_and_deletes_new_file():
    """If the DB update raises, the new ImageKit file is deleted and a generic 500 is raised."""
    uploaded = UploadedImage(url="https://ik.imagekit.io/new.png", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        mock_table = _mock_user_table(mock_supabase, current_file_id="old_id")
        mock_table.update.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")

        with pytest.raises(HTTPException) as exc_info:
            school_admin_service.upload_my_profile_photo(user_id=4, file_bytes=PNG_BYTES, content_type="image/png")

    assert exc_info.value.status_code == 500
    assert "db down" not in exc_info.value.detail
    mock_ik.delete_file.assert_called_once_with("new_id", user_id=4)


def test_upload_replace_without_previous_file_id_does_not_delete():
    """A user with a legacy photo_url but NULL photo_file_id: nothing is deleted in ImageKit."""
    uploaded = UploadedImage(url="https://ik.imagekit.io/new.png", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        mock_table = _mock_user_table(mock_supabase, current_file_id=None)

        res = school_admin_service.upload_my_profile_photo(user_id=4, file_bytes=PNG_BYTES, content_type="image/png")

    assert res == {"photo_url": uploaded.url}
    mock_table.update.assert_called_once_with({"photo_url": uploaded.url, "photo_file_id": "new_id"})
    mock_ik.delete_file.assert_not_called()


def test_upload_select_failure_returns_500_without_uploading():
    """If reading the current photo_file_id fails, nothing is uploaded and a generic 500 is raised."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_table = _mock_user_table(mock_supabase)
        mock_table.select.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")

        with pytest.raises(HTTPException) as exc_info:
            school_admin_service.upload_my_profile_photo(user_id=4, file_bytes=PNG_BYTES, content_type="image/png")

    assert exc_info.value.status_code == 500
    assert "db down" not in exc_info.value.detail
    mock_ik.upload_profile_image.assert_not_called()
    mock_ik.delete_file.assert_not_called()


def test_delete_my_profile_photo_success():
    """Clears url + file_id in the DB, then deletes the ImageKit file."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_table = _mock_user_table(mock_supabase, current_file_id="old_id")

        res = school_admin_service.delete_my_profile_photo(user_id=4)

    assert res == {"photo_url": None}
    mock_table.update.assert_called_once_with({"photo_url": None, "photo_file_id": None})
    mock_table.update.return_value.eq.assert_called_once_with("id", 4)
    mock_ik.delete_file.assert_called_once_with("old_id", user_id=4)


def test_delete_does_not_touch_imagekit_when_db_update_fails():
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        _mock_user_table(mock_supabase, current_file_id="old_id", update_data=[])

        with pytest.raises(HTTPException) as exc_info:
            school_admin_service.delete_my_profile_photo(user_id=4)

    assert exc_info.value.status_code == 400
    mock_ik.delete_file.assert_not_called()


def test_delete_db_update_raises_returns_500_and_keeps_imagekit_file():
    """If the DB update raises on delete, a generic 500 is raised and ImageKit is untouched."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_table = _mock_user_table(mock_supabase, current_file_id="old_id")
        mock_table.update.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")

        with pytest.raises(HTTPException) as exc_info:
            school_admin_service.delete_my_profile_photo(user_id=4)

    assert exc_info.value.status_code == 500
    assert "db down" not in exc_info.value.detail
    mock_ik.delete_file.assert_not_called()


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────

def test_endpoint_upload_profile_photo(admin_client):
    """POST /school-admin/profile/photo forwards bytes and content type to the service."""
    fake_url = "https://ik.imagekit.io/vitaly/profiles/user_4_uploaded.webp"

    with patch.object(
        school_admin_service, "upload_my_profile_photo", return_value={"photo_url": fake_url}
    ) as mock_service_call:
        files = {"file": ("avatar.webp", io.BytesIO(WEBP_BYTES), "image/webp")}
        response = admin_client.post("/api/v1/school-admin/profile/photo", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["photo_url"] == fake_url
    assert "Foto de perfil subida y actualizada exitosamente" in data["message"]
    mock_service_call.assert_called_once_with(user_id=4, file_bytes=WEBP_BYTES, content_type="image/webp")


def test_endpoint_upload_rejects_oversized_file(admin_client):
    """An upload over 5 MB is rejected before reaching ImageKit or the DB."""
    oversized = JPEG_BYTES + b"0" * profile_photo_service.MAX_PROFILE_PHOTO_BYTES

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        files = {"file": ("big.jpg", io.BytesIO(oversized), "image/jpeg")}
        response = admin_client.post("/api/v1/school-admin/profile/photo", files=files)

    assert response.status_code == 400
    mock_ik.upload_profile_image.assert_not_called()
    mock_supabase.table.assert_not_called()


def test_endpoint_upload_rejects_spoofed_file(admin_client):
    """HTML uploaded as image/png is rejected end-to-end."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase"):
        files = {"file": ("evil.png", io.BytesIO(HTML_BYTES), "image/png")}
        response = admin_client.post("/api/v1/school-admin/profile/photo", files=files)

    assert response.status_code == 400
    mock_ik.upload_profile_image.assert_not_called()


def test_endpoint_delete_profile_photo(admin_client):
    """DELETE /school-admin/profile/photo clears the photo and deletes it in ImageKit."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        _mock_user_table(mock_supabase, current_file_id="old_id")
        response = admin_client.delete("/api/v1/school-admin/profile/photo")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["photo_url"] is None
    assert "eliminada exitosamente" in data["message"]
    mock_ik.delete_file.assert_called_once_with("old_id", user_id=4)


def test_endpoint_update_profile_ignores_photo_url(admin_client):
    """PUT /school-admin/profile never forwards photo_url to the service."""
    with patch.object(school_admin_service, "update_my_profile", return_value={}) as mock_update:
        response = admin_client.put(
            "/api/v1/school-admin/profile",
            json={"name": "Ana", "photo_url": "https://evil.example/x.png"},
        )

    assert response.status_code == 200
    mock_update.assert_called_once_with(user_id=4, payload={"name": "Ana"})


def test_get_profile_hides_photo_file_id():
    """get_my_profile never exposes photo_file_id or password."""
    fake_admin = {
        "id": 1,
        "user": {"id": 4, "password": "hash", "photo_url": "https://x", "photo_file_id": "file_1"},
        "school": {"name": "Colegio"},
    }
    with patch("app.services.school_admin_service.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[fake_admin]
        )
        profile = school_admin_service.get_my_profile(user_id=4)

    assert "photo_file_id" not in profile["user_info"]
    assert "password" not in profile["user_info"]
    assert profile["user_info"]["photo_url"] == "https://x"
