from fastapi import APIRouter, Depends, HTTPException, status

from sqlmodel import Session

from db.db import get_db
from dependencies.auth import require_roles

from entidades.models import CategoriaEquipamento
from entidades.schemas import CategoriaCriar

from controllers.categoria_equipamento_controller import (
    cadastrar_categoria_equipamento,
    buscar_categorias_equipamento,
    buscar_categoria_equipamento,
    atualizar_categoria_equipamento,
    deletar_categoria_equipamento
)

categoria_equipamento_router = APIRouter()


# Cadastra uma nova categoria de equipamento

@categoria_equipamento_router.post("/categoria_equipamentos")
def cadastro_categoria_equipamento(
    categoria: CategoriaCriar,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return cadastrar_categoria_equipamento(
            categoria,
            db
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


# Busca todas as categorias de equipamento

@categoria_equipamento_router.get("/categoria_equipamentos")
def buscar_categorias(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Usuário comum", "Gestor", "Administrador"))
):
    try:
        return buscar_categorias_equipamento(db)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Busca uma categoria de equipamento pelo ID

@categoria_equipamento_router.get("/categoria_equipamentos/{categoria_id}")
def buscar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Usuário comum", "Gestor", "Administrador"))
):
    try:
        return buscar_categoria_equipamento(
            db,
            categoria_id
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


# Atualiza uma categoria de equipamento

@categoria_equipamento_router.put("/categoria_equipamentos/{categoria_id}")
def atualizar_categoria(
    categoria_id: int,
    categoria: CategoriaEquipamento,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return atualizar_categoria_equipamento(
            db,
            categoria_id,
            categoria
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


# Deleta uma categoria de equipamento

@categoria_equipamento_router.delete("/categoria_equipamentos/{categoria_id}")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        deletar_categoria_equipamento(
            db,
            categoria_id
        )

        return {
            "mensagem": "Categoria de equipamento deletada com sucesso."
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