from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from db.db import get_db
from entidades.schemas import EquipamentoCriar, EquipamentoAtualizar
from dependencies.auth import require_roles

from controllers.equipamento_controller import (
    cadastrar_equipamento,
    buscar_equipamentos,
    buscar_equipamentos_paginado,
    resumo_equipamentos,
    patrimonio_existe,
    buscar_equipamento,
    atualizar_equipamento,
    deletar_equipamento
)

equipamento_router = APIRouter()


# Cadastra um novo equipamento
@equipamento_router.post("/equipamentos")
def cadastro_equipamento(
    equipamento: EquipamentoCriar,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return cadastrar_equipamento(
            equipamento,
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


# Busca todos os equipamentos
@equipamento_router.get("/equipamentos")
def buscar_equipamentos_route(
    db: Session = Depends(get_db),
    usuario=Depends(
        require_roles("Usuário comum", "Gestor", "Administrador")
    )
):
    try:
        return buscar_equipamentos(db)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Lista equipamentos paginada: o front pede uma página por vez
# (precisa vir antes de /equipamentos/{equipamento_id})
@equipamento_router.get("/equipamentos/paginado")
def buscar_equipamentos_paginado_route(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    status_equipamento: str | None = Query(None, alias="status"),
    busca: str | None = Query(None, max_length=100),
    ordenar: str | None = Query(None, max_length=20),
    direcao: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return buscar_equipamentos_paginado(
            db,
            pagina=pagina,
            por_pagina=por_pagina,
            status=status_equipamento,
            busca=busca,
            ordenar=ordenar,
            direcao=direcao
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


# Totais por status para os indicadores do painel
@equipamento_router.get("/equipamentos/resumo")
def resumo_equipamentos_route(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador", "Gestor"))
):
    try:
        return resumo_equipamentos(db)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Confere na hora se um número de patrimônio já está em uso
@equipamento_router.get("/equipamentos/patrimonio/existe")
def patrimonio_existe_route(
    numero: str = Query(..., min_length=1, max_length=100),
    ignorar_id: int | None = Query(None),
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return {"existe": patrimonio_existe(db, numero, ignorar_id)}

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Busca um equipamento pelo ID
@equipamento_router.get("/equipamentos/{equipamento_id}")
def buscar_equipamento_route(
    equipamento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(
        require_roles("Usuário comum", "Gestor", "Administrador")
    )
):
    try:
        return buscar_equipamento(
            db,
            equipamento_id
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


# Atualiza um equipamento
@equipamento_router.put("/equipamentos/{equipamento_id}")
def atualizar_equipamento_route(
    equipamento_id: int,
    equipamento: EquipamentoAtualizar,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        return atualizar_equipamento(
            db,
            equipamento_id,
            equipamento
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


# Deleta um equipamento
@equipamento_router.delete("/equipamentos/{equipamento_id}")
def deletar_equipamento_route(
    equipamento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    try:
        deletar_equipamento(
            db,
            equipamento_id
        )

        return {
            "mensagem": "Equipamento deletado com sucesso."
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