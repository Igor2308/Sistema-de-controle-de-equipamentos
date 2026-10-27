from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from dependencies.dependencies import database
from entidades.models import UsuarioLogin, UsuarioAutenticado
from controllers.auth_controller import fazer_login
from dependencies.auth import get_current_user

auth_routes = APIRouter()


# ====== Realiza o login do usuário ======
@auth_routes.post("/auth/login")
def usuario_login(
    credenciais: UsuarioLogin,
    db: Session = Depends(database.get_db)
):
    try:
        token = fazer_login(
            db,
            credenciais.email,
            credenciais.senha
        )
        return token

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# ====== Realiza o logout ======
@auth_routes.post("/auth/logout")
def logout():
    return {
        "mensagem": "Logout realizado. Remova o token armazenado no cliente."
    }


# ====== Retorna os dados do usuário autenticado ======
@auth_routes.get("/auth/me")
def me(
    usuario: UsuarioAutenticado = Depends(get_current_user)
):
    return usuario
