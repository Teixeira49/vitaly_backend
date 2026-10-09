import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_doctor
from app.services import profile_photo_service
from app.services.doctor_service import doctor_service
from app.services.imagekit_service import UploadedImage


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _mock_user_table(mock_supabase, current_file_id=None, update_data=None):
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"photo_file_id": current_file_id}]
    )
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=update_data if update_data is not None else [{"id": 20}]
    )
    return mock_table


def test_doctor_get_profile_not_found():
    """Valida que get_my_profile lance 404 si el doctor no existe en la base de datos."""
    with patch("app.services.doctor_service.supabase") as mock_supabase:
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=[])

        with pytest.raises(HTTPException) as exc:
            doctor_service.get_my_profile(user_id=999)
        assert exc.value.status_code == 404
        assert "no encontrado" in exc.value.detail


def test_doctor_get_profile_success():
    """Valida que get_my_profile formatee adecuadamente la respuesta incluyendo photo_url."""
    fake_doctor = {
        "doc_id": 1,
        "user_id": 20,
        "doc_license_number": "MPPS-12345",
        "especially": "Pediatría",
        "experience_years": 1980,
        "user": {
            "id": 20,
            "name": "Ricardo",
            "lastname": "Vargas",
            "email": "dr.vargas@vitaly.app",
            "password": "hashed_secret",
            "photo_url": "https://ik.imagekit.io/vitaly/profiles/doctors/dr_ricardo.jpg",
            "photo_file_id": "file_ricardo",
            "gender": "M",
            "address": "Consultorio 4",
            "biography": "Especialista en pediatría general",
            "identity_number": "V-12345678"
        },
        "doctor_to_school": [
            {
                "school_id": 1,
                "status": 2,
                "school": {
                    "sch_id": 1,
                    "name": "Colegio San Ignacio",
                    "address": "Av. Sta. Teresa",
                    "rif": 123456789
                }
            }
        ]
    }

    with patch("app.services.doctor_service.supabase") as mock_supabase:
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=[fake_doctor])

        profile = doctor_service.get_my_profile(user_id=20)

        assert "password" not in profile["user_info"]
        assert "photo_file_id" not in profile["user_info"]
        assert profile["user_info"]["photo_url"] == "https://ik.imagekit.io/vitaly/profiles/doctors/dr_ricardo.jpg"
        assert profile["doctor_info"]["doc_license_number"] == "MPPS-12345"
        assert len(profile["schools"]) == 1
        assert profile["schools"][0]["school_name"] == "Colegio San Ignacio"


def test_doctor_upload_profile_photo_invalid_type():
    """Rejects unsupported MIME types."""
    with pytest.raises(HTTPException) as exc:
        doctor_service.upload_my_profile_photo(user_id=20, file_bytes=b"raw_bytes", content_type="text/plain")
    assert exc.value.status_code == 400
    assert "Formato no permitido" in exc.value.detail


def test_doctor_upload_profile_photo_exceeds_size():
    """Rejects images over 5 MB."""
    oversized = JPEG_BYTES + b"0" * profile_photo_service.MAX_PROFILE_PHOTO_BYTES
    with pytest.raises(HTTPException) as exc:
        doctor_service.upload_my_profile_photo(user_id=20, file_bytes=oversized, content_type="image/jpeg")
    assert exc.value.status_code == 400
    assert "tamaño máximo" in exc.value.detail


def test_doctor_upload_profile_photo_success_replaces_old_file():
    """Uploads to the doctors folder, stores url + file_id and deletes the old file."""
    uploaded = UploadedImage(url="https://ik.imagekit.io/vitaly/profiles/doctors/user_20_abc.jpg", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        mock_table = _mock_user_table(mock_supabase, current_file_id="old_id")

        res = doctor_service.upload_my_profile_photo(user_id=20, file_bytes=JPEG_BYTES, content_type="image/jpeg")

    assert res == {"photo_url": uploaded.url}
    mock_ik.upload_profile_image.assert_called_once_with(
        file_bytes=JPEG_BYTES, extension="jpg", user_id=20, folder="/vitaly/profiles/doctors"
    )
    mock_table.update.assert_called_once_with({"photo_url": uploaded.url, "photo_file_id": "new_id"})
    mock_table.update.return_value.eq.assert_called_once_with("id", 20)
    mock_ik.delete_file.assert_called_once_with("old_id", user_id=20)


def test_doctor_upload_rolls_back_new_file_when_db_fails():
    uploaded = UploadedImage(url="https://ik.imagekit.io/new.jpg", file_id="new_id")

    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_ik.upload_profile_image.return_value = uploaded
        _mock_user_table(mock_supabase, current_file_id="old_id", update_data=[])

        with pytest.raises(HTTPException):
            doctor_service.upload_my_profile_photo(user_id=20, file_bytes=JPEG_BYTES, content_type="image/jpeg")

    mock_ik.delete_file.assert_called_once_with("new_id", user_id=20)


def test_doctor_delete_profile_photo_success():
    """Clears url + file_id and deletes the ImageKit file."""
    with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
            patch.object(profile_photo_service, "supabase") as mock_supabase:
        mock_table = _mock_user_table(mock_supabase, current_file_id="old_id")

        res = doctor_service.delete_my_profile_photo(user_id=20)

    assert res == {"photo_url": None}
    mock_table.update.assert_called_once_with({"photo_url": None, "photo_file_id": None})
    mock_table.update.return_value.eq.assert_called_once_with("id", 20)
    mock_ik.delete_file.assert_called_once_with("old_id", user_id=20)


def test_endpoint_doctor_profile_and_photo():
    """GET/PUT /doctor/profile and POST/DELETE /doctor/profile/photo."""
    client = TestClient(app)
    fake_url = "https://ik.imagekit.io/vitaly/profiles/doctors/user_20_uploaded.png"

    app.dependency_overrides[get_current_doctor] = lambda: {"sub": "20", "role": "doctor"}

    try:
        # 1. GET /api/v1/doctor/profile
        with patch.object(
            doctor_service, "get_my_profile", return_value={"user_info": {"name": "Ricardo", "photo_url": None}}
        ):
            resp = client.get("/api/v1/doctor/profile")
            assert resp.status_code == 200
            assert resp.json()["data"]["user_info"]["photo_url"] is None

        # 2. PUT /api/v1/doctor/profile ignores photo_url
        with patch.object(doctor_service, "update_my_profile", return_value={}) as mock_update:
            resp = client.put(
                "/api/v1/doctor/profile",
                json={"biography": "Hola", "photo_url": "https://evil.example/x.png"},
            )
            assert resp.status_code == 200
            mock_update.assert_called_once_with(user_id=20, payload={"biography": "Hola"})

        # 3. POST /api/v1/doctor/profile/photo
        with patch.object(
            doctor_service, "upload_my_profile_photo", return_value={"photo_url": fake_url}
        ) as mock_upload:
            files = {"file": ("avatar.png", io.BytesIO(PNG_BYTES), "image/png")}
            resp = client.post("/api/v1/doctor/profile/photo", files=files)
            assert resp.status_code == 200
            assert resp.json()["data"]["photo_url"] == fake_url
            mock_upload.assert_called_once_with(user_id=20, file_bytes=PNG_BYTES, content_type="image/png")

        # 4. DELETE /api/v1/doctor/profile/photo calls ImageKit delete
        with patch.object(profile_photo_service, "imagekit_service") as mock_ik, \
                patch.object(profile_photo_service, "supabase") as mock_supabase:
            _mock_user_table(mock_supabase, current_file_id="old_id")
            resp = client.delete("/api/v1/doctor/profile/photo")
            assert resp.status_code == 200
            assert resp.json()["data"]["photo_url"] is None
            mock_ik.delete_file.assert_called_once_with("old_id", user_id=20)
    finally:
        app.dependency_overrides.clear()
