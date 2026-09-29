import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_doctor
from app.services.doctor_service import doctor_service


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
        assert profile["user_info"]["photo_url"] == "https://ik.imagekit.io/vitaly/profiles/doctors/dr_ricardo.jpg"
        assert profile["doctor_info"]["doc_license_number"] == "MPPS-12345"
        assert len(profile["schools"]) == 1
        assert profile["schools"][0]["school_name"] == "Colegio San Ignacio"


def test_doctor_upload_profile_photo_invalid_type():
    """Rechaza archivos con MIME-type no soportado."""
    with pytest.raises(HTTPException) as exc:
        doctor_service.upload_my_profile_photo(
            user_id=20,
            file_bytes=b"raw_bytes",
            filename="document.txt",
            content_type="text/plain"
        )
    assert exc.value.status_code == 400
    assert "Formato no permitido" in exc.value.detail


def test_doctor_upload_profile_photo_exceeds_size():
    """Rechaza imágenes de más de 5MB."""
    oversized = b"0" * (5 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc:
        doctor_service.upload_my_profile_photo(
            user_id=20,
            file_bytes=oversized,
            filename="big.jpg",
            content_type="image/jpeg"
        )
    assert exc.value.status_code == 400
    assert "tamaño máximo" in exc.value.detail


def test_doctor_upload_profile_photo_success():
    """Valida la subida exitosa de foto para doctor y actualización en BD."""
    fake_url = "https://ik.imagekit.io/vitaly/profiles/doctors/user_20_abc.jpg"

    with patch("app.services.doctor_service.imagekit_service.upload_profile_image", return_value=fake_url):
        with patch("app.services.doctor_service.supabase") as mock_supabase:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_update = MagicMock()
            mock_table.update.return_value = mock_update
            mock_eq = MagicMock()
            mock_update.eq.return_value = mock_eq
            mock_eq.execute.return_value = MagicMock(data=[{"id": 20, "photo_url": fake_url}])

            res = doctor_service.upload_my_profile_photo(
                user_id=20,
                file_bytes=b"\xff\xd8\xff\xe0",
                filename="doctor.jpg",
                content_type="image/jpeg"
            )

            assert res == {"photo_url": fake_url}
            mock_table.update.assert_called_once_with({"photo_url": fake_url})
            mock_update.eq.assert_called_once_with("id", 20)


def test_doctor_delete_profile_photo_success():
    """Valida la eliminación de foto seteando photo_url a None."""
    with patch("app.services.doctor_service.supabase") as mock_supabase:
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq = MagicMock()
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=[{"id": 20, "photo_url": None}])

        res = doctor_service.delete_my_profile_photo(user_id=20)
        assert res == {"photo_url": None}
        mock_table.update.assert_called_once_with({"photo_url": None})
        mock_update.eq.assert_called_once_with("id", 20)


def test_endpoint_doctor_profile_and_photo():
    """Valida los endpoints GET, POST y DELETE de /doctor/profile y /doctor/profile/photo."""
    client = TestClient(app)
    fake_url = "https://ik.imagekit.io/vitaly/profiles/doctors/user_20_uploaded.png"

    app.dependency_overrides[get_current_doctor] = lambda: {
        "sub": "20",
        "role": "doctor"
    }

    try:
        # 1. GET /api/v1/doctor/profile
        with patch.object(
            doctor_service,
            "get_my_profile",
            return_value={"user_info": {"name": "Ricardo", "photo_url": None}}
        ):
            resp = client.get("/api/v1/doctor/profile")
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert resp.json()["data"]["user_info"]["photo_url"] is None

        # 2. POST /api/v1/doctor/profile/photo
        with patch.object(
            doctor_service,
            "upload_my_profile_photo",
            return_value={"photo_url": fake_url}
        ):
            files = {
                "file": ("avatar.png", io.BytesIO(b"fake_bytes"), "image/png")
            }
            resp = client.post("/api/v1/doctor/profile/photo", files=files)
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert resp.json()["data"]["photo_url"] == fake_url

        # 3. DELETE /api/v1/doctor/profile/photo
        with patch.object(
            doctor_service,
            "delete_my_profile_photo",
            return_value={"photo_url": None}
        ):
            resp = client.delete("/api/v1/doctor/profile/photo")
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert resp.json()["data"]["photo_url"] is None
    finally:
        app.dependency_overrides.clear()
