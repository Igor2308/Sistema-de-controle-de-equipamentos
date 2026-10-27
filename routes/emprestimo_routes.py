
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from db.db import get_db
from entidades.schemas import EmprestimoCriar, EmprestimoAtualizar
from dependencies.auth import require_roles

from controllers.emprestimo_controller import (
    cadastrar_emprestimo,
    buscar_emprestimos,
    buscar_emprestimo,
    atualizar_emprestimo,
    deletar_emprestimo
)


emprestimo_router = APIRouter()


# Cadastra um empréstimo
@emprestimo_router.post("/emprestimos")
def cadastro_emprestimo(
    emprestimo: EmprestimoCriar,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor"))
):
    try:
        return cadastrar_emprestimo(emprestimo, db)

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


# Lista empréstimos
@emprestimo_router.get("/emprestimos")
def buscar_emprestimos_route(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor"))
):
    try:
        return buscar_emprestimos(db)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


# Lista somente os empréstimos do usuário comum autenticado
# Precisa vir antes de /emprestimos/{emprestimo_id}
@emprestimo_router.get("/emprestimos/meus")
def buscar_meus_emprestimos(
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Usuário comum"))
):
    try:
        return [
            emprestimo
            for emprestimo in buscar_emprestimos(db)
            if emprestimo.id_usuario == usuario.id_usuario
        ]

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e


# Busca um empréstimo pelo ID
@emprestimo_router.get("/emprestimos/{emprestimo_id}")
def buscar_emprestimo_route(
    emprestimo_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor"))
):
    try:
        return buscar_emprestimo(db, emprestimo_id)

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


# Atualiza um empréstimo, incluindo o registro da devolução
@emprestimo_router.put("/emprestimos/{emprestimo_id}")
def atualizar_emprestimo_route(
    emprestimo_id: int,
    emprestimo: EmprestimoAtualizar,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor"))
):
    try:
        return atualizar_emprestimo(
            db,
            emprestimo_id,
            emprestimo
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


# Exclui um empréstimo
@emprestimo_router.delete("/emprestimos/{emprestimo_id}")
def deletar_emprestimo_route(
    emprestimo_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(require_roles("Gestor"))
):
    try:
        deletar_emprestimo(db, emprestimo_id)

        return {
            "mensagem": "Empréstimo deletado com sucesso."
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
