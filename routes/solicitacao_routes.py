
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import datetime

from db.db import get_db
from entidades.models import UsuarioAutenticado
from entidades.schemas import SolicitacaoCriar, SolicitacaoAtualizar
from dependencies.auth import get_current_user, require_roles

from controllers.solicitacao_controller import (
    cadastrar_solicitacao,
    buscar_solicitacoes,
    buscar_solicitacao,
    atualizar_solicitacao,
    deletar_solicitacao
)


solicitacao_router = APIRouter()


# Cadastra uma nova solicitação
@solicitacao_router.post("/solicitacoes")
def cadastro_solicitacao(
    solicitacao: SolicitacaoCriar,
    db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(
        require_roles("Usuário comum")
    )
):
    # Vincula a solicitação ao usuário autenticado
    solicitacao.id_solicitante = usuario.id_usuario

    try:
        return cadastrar_solicitacao(solicitacao, db)

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


# Busca solicitações do usuário autenticado
# O Gestor pode consultar todas para realizar as aprovações
@solicitacao_router.get("/solicitacoes")
def buscar_solicitacoes_route(
    db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(get_current_user)
):
    try:
        solicitacoes = buscar_solicitacoes(db)

        if "Gestor" in usuario.roles:
            return solicitacoes

        return [
            solicitacao
            for solicitacao in solicitacoes
            if solicitacao.id_solicitante == usuario.id_usuario
        ]

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


# Busca uma solicitação pelo ID
@solicitacao_router.get("/solicitacoes/{solicitacao_id}")
def buscar_solicitacao_route(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(get_current_user)
):
    try:
        solicitacao = buscar_solicitacao(
            db,
            solicitacao_id
        )

        # Só o Gestor pode consultar solicitações de outros usuários
        if (
            "Gestor" not in usuario.roles
            and solicitacao.id_solicitante != usuario.id_usuario
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Você não tem permissão para "
                    "consultar esta solicitação."
                )
            )

        return solicitacao

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


# Atualiza uma solicitação
@solicitacao_router.put("/solicitacoes/{solicitacao_id}")
def atualizar_solicitacao_route(
    solicitacao_id: int,
    solicitacao: SolicitacaoAtualizar,
    db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(
        require_roles("Gestor")
    )
):
    # Registra automaticamente o Gestor responsável
    # pela aprovação ou recusa da solicitação
    if solicitacao.situacao in ("aprovado", "recusado"):
        solicitacao.id_usuario_autorizador = usuario.id_usuario
        solicitacao.data_autorizacao = datetime.now()

    try:
        return atualizar_solicitacao(
            db,
            solicitacao_id,
            solicitacao
        )

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


# Exclui uma solicitação
@solicitacao_router.delete("/solicitacoes/{solicitacao_id}")
def deletar_solicitacao_route(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioAutenticado = Depends(
        require_roles("Gestor")
    )
):
    try:
        deletar_solicitacao(
            db,
            solicitacao_id
        )

        return {
            "mensagem": "Solicitação deletada com sucesso."
        }

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        ) from e

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e
