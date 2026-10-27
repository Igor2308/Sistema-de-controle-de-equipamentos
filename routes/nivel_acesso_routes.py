from fastapi import APIRouter, Depends, HTTPException, status

from sqlmodel import Session

from db.db import get_db
from dependencies.auth import require_roles

from entidades.models import NivelAcesso

from controllers.nivel_acesso_controller import (
    cadastrar_nivel_acesso,
    buscar_niveis_acesso,
    buscar_nivel_acesso,
    atualizar_nivel_acesso,
    deletar_nivel_acesso
)

nivel_acesso_router = APIRouter()


# Cadastra um novo nível de acesso

@nivel_acesso_router.post("/nivel_acesso")
def cadastro_nivel_acesso(
    nivel: NivelAcesso,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return cadastrar_nivel_acesso(nivel, db)

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


# Busca todos os níveis de acesso

@nivel_acesso_router.get("/nivel_acesso")
def buscar_niveis(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return buscar_niveis_acesso(db)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Busca um nível de acesso pelo ID

@nivel_acesso_router.get("/nivel_acesso/{nivel_id}")
def buscar_nivel(
    nivel_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return buscar_nivel_acesso(
            db,
            nivel_id
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


# Atualiza um nível de acesso

@nivel_acesso_router.put("/nivel_acesso/{nivel_id}")
def atualizar_nivel(
    nivel_id: int,
    nivel: NivelAcesso,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return atualizar_nivel_acesso(
            db,
            nivel_id,
            nivel
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


# Deleta um nível de acesso

@nivel_acesso_router.delete("/nivel_acesso/{nivel_id}")
def deletar_nivel(
    nivel_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        deletar_nivel_acesso(
            db,
            nivel_id
        )

        return {
            "mensagem": "Nível de acesso deletado com sucesso."
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