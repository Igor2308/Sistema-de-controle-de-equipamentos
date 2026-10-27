from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
import jwt

from core.security import decodificar_token
from entidades.models import Usuario, NivelAcesso, UsuarioAutenticado
from dependencies.dependencies import database

bearer_scheme = HTTPBearer(auto_error=True)


# ====== Busca o usuário autenticado pelo token ======
def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(database.get_db)
):
    # Decodifica e valida o token JWT
    try:
        payload = decodificar_token(creds.credentials)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Obtém o ID do usuário informado no token
    try:
        id_usuario = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Busca o usuário no banco de dados
    usuario = db.get(Usuario, id_usuario)

    if usuario is None or usuario.status_usuario != "ativo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inválido ou inativo.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Busca o nível de acesso atual do usuário
    nivel = db.get(NivelAcesso, usuario.nivel_acesso)

    if nivel is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem nível de acesso válido."
        )

    # Retorna os dados do usuário autenticado
    return UsuarioAutenticado(
        id_usuario=usuario.id_usuario,
        nome=usuario.nome,
        email=usuario.email,
        roles=[nivel.nome]
    )


# ====== Verifica se o usuário possui a permissão necessária ======
def require_roles(*roles_necessarias: str):

    def _checker(
        user: UsuarioAutenticado = Depends(get_current_user)
    ) -> UsuarioAutenticado:

        if not set(roles_necessarias).intersection(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Acesso negado. Requer uma das permissões: "
                    f"{list(roles_necessarias)}."
                )
            )

        return user

    return _checker