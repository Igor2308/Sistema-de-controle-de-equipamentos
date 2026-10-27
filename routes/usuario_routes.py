
from fastapi import APIRouter, Depends, HTTPException, status

from sqlmodel import Session

from db.db import get_db

from entidades.models import UsuarioAutenticado

from entidades.schemas import (
    UsuarioResposta,
    UsuarioCriar,
    UsuarioAtualizar
)

from dependencies.auth import get_current_user, require_roles

from controllers.usuario_controller import (
    cadastrar_usuario,
    buscar_usuarios,
    buscar_usuario,
    atualizar_usuario,
    deletar_usuario
)

usuario_router = APIRouter()


# Cadastra um novo usuário como usuário comum
@usuario_router.post(
    "/usuarios",
    response_model=UsuarioResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastro_usuario(
    usuario: UsuarioCriar,
    db: Session = Depends(get_db)
):
    try:
        # Impede cadastro público com privilégios elevados
        usuario.nivel_acesso = 1

        return cadastrar_usuario(
            usuario,
            db
        )

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Lista usuários: somente Administrador
@usuario_router.get(
    "/usuarios",
    response_model=list[UsuarioResposta]
)
def buscar_usuarios_route(
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(
        require_roles("Administrador")
    )
):
    try:
        return buscar_usuarios(db)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Lista apenas ID e nome dos usuários: Gestor e Administrador
# (o Gestor precisa dos nomes para exibir solicitantes e empréstimos)
# Precisa vir antes de /usuarios/{usuario_id}
@usuario_router.get("/usuarios/nomes")
def buscar_nomes_usuarios(
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(
        require_roles("Gestor", "Administrador")
    )
):
    try:
        return [
            {"id_usuario": u.id_usuario, "nome": u.nome}
            for u in buscar_usuarios(db)
        ]

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Consulta um usuário: somente Administrador
@usuario_router.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResposta
)
def buscar_usuario_route(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(
        require_roles("Administrador")
    )
):
    try:
        return buscar_usuario(
            db,
            usuario_id
        )

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Atualiza um usuário: somente Administrador
@usuario_router.put(
    "/usuarios/{usuario_id}",
    response_model=UsuarioResposta
)
def atualizar_usuario_route(
    usuario_id: int,
    usuario: UsuarioAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(
        require_roles("Administrador")
    )
):
    try:
        return atualizar_usuario(
            db,
            usuario_id,
            usuario
        )

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Deleta um usuário: somente Administrador
@usuario_router.delete("/usuarios/{usuario_id}")
def deletar_usuario_route(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_atual: UsuarioAutenticado = Depends(
        require_roles("Administrador")
    )
):
    try:
        deletar_usuario(
            db,
            usuario_id
        )

        return {
            "mensagem": "Usuário deletado com sucesso."
        }

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
