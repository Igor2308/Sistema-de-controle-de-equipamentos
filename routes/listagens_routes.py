"""Rotas de listagem: paginadas, ordenáveis e com os nomes já preenchidos.

IMPORTANTE: este router é incluído ANTES dos demais no main.py, porque
caminhos como /solicitacoes/paginado não podem ser confundidos com
/solicitacoes/{solicitacao_id}.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from controllers.equipamento_controller import buscar_equipamentos_paginado
from controllers.listagens_controller import (
    emprestimos_paginado,
    emprestimos_resumo,
    solicitacoes_paginado,
    solicitacoes_resumo,
    usuarios_paginado,
    usuarios_resumo,
)
from db.db import get_db
from dependencies.auth import require_roles

listagens_router = APIRouter()



def _direcao(padrao: str = "desc"):
    # Um Query novo por parâmetro (evita compartilhar o mesmo objeto entre rotas)
    return Query(padrao, pattern="^(asc|desc)$")


def _executar(funcao, *args, **kwargs):
    try:
        return funcao(*args, **kwargs)

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


def _eh_gestor(usuario) -> bool:
    return "Gestor" in usuario.roles


# ----- Usuários (Administrador) -----
@listagens_router.get("/usuarios/paginado")
def usuarios_paginado_route(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    busca: str | None = Query(None, max_length=100),
    ordenar: str | None = Query(None, max_length=20),
    direcao: str = _direcao(),
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    return _executar(
        usuarios_paginado, db, pagina, por_pagina, busca, ordenar, direcao
    )


@listagens_router.get("/usuarios/resumo")
def usuarios_resumo_route(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Administrador"))
):
    return _executar(usuarios_resumo, db)


# ----- Equipamentos disponíveis (Usuário comum) -----
@listagens_router.get("/equipamentos/disponiveis")
def equipamentos_disponiveis_route(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    busca: str | None = Query(None, max_length=100),
    ordenar: str | None = Query("nome", max_length=20),
    direcao: str = _direcao("asc"),
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Usuário comum", "Gestor", "Administrador"))
):
    return _executar(
        buscar_equipamentos_paginado,
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        status="disponivel",
        busca=busca,
        ordenar=ordenar,
        direcao=direcao
    )


# ----- Solicitações (Gestor vê todas; Usuário comum vê as próprias) -----
@listagens_router.get("/solicitacoes/paginado")
def solicitacoes_paginado_route(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    situacao: str | None = Query(None, max_length=20),
    ordenar: str | None = Query(None, max_length=20),
    direcao: str = _direcao(),
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor", "Usuário comum"))
):
    return _executar(
        solicitacoes_paginado,
        db, pagina, por_pagina, situacao, ordenar, direcao,
        None if _eh_gestor(usuario) else usuario.id_usuario
    )


@listagens_router.get("/solicitacoes/resumo")
def solicitacoes_resumo_route(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor", "Usuário comum"))
):
    return _executar(
        solicitacoes_resumo,
        db,
        None if _eh_gestor(usuario) else usuario.id_usuario
    )


# ----- Empréstimos (Gestor vê todos; Usuário comum vê os próprios) -----
@listagens_router.get("/emprestimos/paginado")
def emprestimos_paginado_route(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
    status_emprestimo: str | None = Query(None, alias="status", max_length=20),
    ordenar: str | None = Query(None, max_length=20),
    direcao: str = _direcao(),
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor", "Usuário comum"))
):
    return _executar(
        emprestimos_paginado,
        db, pagina, por_pagina, status_emprestimo, ordenar, direcao,
        None if _eh_gestor(usuario) else usuario.id_usuario
    )


@listagens_router.get("/emprestimos/resumo")
def emprestimos_resumo_route(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor", "Usuário comum"))
):
    return _executar(
        emprestimos_resumo,
        db,
        None if _eh_gestor(usuario) else usuario.id_usuario
    )
