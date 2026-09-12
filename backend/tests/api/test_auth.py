import pytest
from httpx import AsyncClient

from tests.conftest import make_auth_headers, TEST_ORG_ID
from app.models.user import User


pytestmark = pytest.mark.asyncio


class TestLogin:
    """POST /api/v1/auth/login"""

    async def test_login_success(self, client: AsyncClient, teacher_user: User):
        """Успешный логин возвращает access_token."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": teacher_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 200
        body = response.json()        
        assert "accessToken" in body
        assert body["tokenType"] == "bearer"
        assert len(body["accessToken"]) > 20

    async def test_login_wrong_password(self, client: AsyncClient, teacher_user: User):
        """Неверный пароль → 400."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": teacher_user.email,
                "password": "wrong_password",
            },
        )
        assert response.status_code == 400
        assert "Incorrect" in response.json()["detail"]

    async def test_login_unknown_email(self, client: AsyncClient):
        """Несуществующий email → 400."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nobody@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400

    async def test_login_inactive_user(
        self, client: AsyncClient, db, teacher_user: User
    ):
        """Неактивный пользователь → 400."""
        teacher_user.is_active = False
        db.add(teacher_user)
        await db.flush()

        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": teacher_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "Inactive" in response.json()["detail"]

    async def test_login_missing_fields(self, client: AsyncClient):
        """Пустой запрос → 422 Unprocessable Entity."""
        response = await client.post("/api/v1/auth/login", data={})
        assert response.status_code == 422


class TestMe:
    """GET /api/v1/auth/me"""

    async def test_me_success(self, client: AsyncClient, teacher_user: User):
        """Авторизованный запрос возвращает данные пользователя."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=make_auth_headers(teacher_user),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == teacher_user.email
        assert body["role"] == teacher_user.role.value
        assert "hashed_password" not in body  # пароль не утекает

    async def test_me_no_token(self, client: AsyncClient):
        """Запрос без токена → 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        """Невалидный токен → 403."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert response.status_code == 403

    async def test_me_wrong_org_isolated(
        self, client: AsyncClient, other_org_user: User
    ):
        """
        Пользователь из другой организации получает свои данные —
        убеждаемся что org_id не подменяется.
        """
        response = await client.get(
            "/api/v1/auth/me",
            headers=make_auth_headers(other_org_user),
        )
        assert response.status_code == 200
        assert response.json()["orgId"] == str(other_org_user.org_id)