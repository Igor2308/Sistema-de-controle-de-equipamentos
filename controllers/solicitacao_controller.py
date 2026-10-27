
from datetime import datetime

from sqlmodel import Session, select

from entidades.models import (
    Solicitacao,
    Usuario,
    Equipamento,
    Emprestimo
)
from entidades.schemas import SolicitacaoCriar, SolicitacaoAtualizar

from sqlalchemy.exc import OperationalError, IntegrityError


# Cadastra uma nova solicitação no banco de dados
def cadastrar_solicitacao(
    solicitacao_data: SolicitacaoCriar,
    db: Session
):
    try:
        # Verifica se o equipamento existe
        equipamento = db.get(
            Equipamento,
            solicitacao_data.id_equipamento
        )

        if not equipamento:
            raise KeyError(
                f"Equipamento de ID "
                f"{solicitacao_data.id_equipamento} não encontrado."
            )

        # Verifica se o usuário solicitante existe
        usuario = db.get(
            Usuario,
            solicitacao_data.id_solicitante
        )

        if not usuario:
            raise KeyError(
                f"Usuário de ID "
                f"{solicitacao_data.id_solicitante} não encontrado."
            )

        # Só equipamentos disponíveis podem ser solicitados
        if equipamento.status_equipamento != "disponivel":
            raise ValueError(
                "Este equipamento não está disponível para solicitação."
            )

        # A devolução não pode ser antes da retirada
        if (
            solicitacao_data.data_prevista_devolucao
            < solicitacao_data.data_retirada_solicitada
        ):
            raise ValueError(
                "A devolução prevista não pode ser anterior à retirada."
            )

        # Cria a solicitação (as datas já chegam como datetime)
        solicitacao = Solicitacao(
            **solicitacao_data.model_dump(exclude={"situacao"})
        )

        # Solicitações novas sempre começam pendentes
        solicitacao.situacao = "pendente"

        # Registra data e hora exatas em que a solicitação foi feita
        solicitacao.data_solicitacao = datetime.now().replace(microsecond=0)

        db.add(solicitacao)
        db.commit()
        db.refresh(solicitacao)

        return solicitacao

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Verifique os dados informados."
        ) from e


# Busca todas as solicitações cadastradas
def buscar_solicitacoes(db: Session):
    try:
        statement = select(Solicitacao)

        solicitacoes = db.exec(statement).all()

        return solicitacoes

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Busca uma solicitação pelo ID
def buscar_solicitacao(
    db: Session,
    solicitacao_id: int
):
    try:
        solicitacao = db.get(
            Solicitacao,
            solicitacao_id
        )

        if not solicitacao:
            raise KeyError(
                f"Solicitação de ID "
                f"{solicitacao_id} não encontrada."
            )

        return solicitacao

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Atualiza uma solicitação existente
def atualizar_solicitacao(
    db: Session,
    solicitacao_id: int,
    dados_atualizados: SolicitacaoAtualizar
):
    try:
        # Busca a solicitação pelo ID
        solicitacao = db.get(
            Solicitacao,
            solicitacao_id
        )

        if not solicitacao:
            raise KeyError(
                f"Solicitação de ID "
                f"{solicitacao_id} não encontrada."
            )

        solicitacao_data = dados_atualizados.model_dump(
            exclude_unset=True
        )

        # Impede a troca do equipamento da solicitação
        if (
            "id_equipamento" in solicitacao_data
            and solicitacao_data["id_equipamento"]
            != solicitacao.id_equipamento
        ):
            raise ValueError(
                "Não é permitido alterar o equipamento "
                "de uma solicitação existente."
            )

        # Impede a troca do solicitante
        if (
            "id_solicitante" in solicitacao_data
            and solicitacao_data["id_solicitante"]
            != solicitacao.id_solicitante
        ):
            raise ValueError(
                "Não é permitido alterar o solicitante "
                "de uma solicitação existente."
            )

        # Verifica se o equipamento existe
        if "id_equipamento" in solicitacao_data:
            equipamento = db.get(
                Equipamento,
                solicitacao_data["id_equipamento"]
            )

            if not equipamento:
                raise KeyError(
                    f"Equipamento de ID "
                    f"{solicitacao_data['id_equipamento']} "
                    f"não encontrado."
                )

        # Verifica se o solicitante existe
        if "id_solicitante" in solicitacao_data:
            usuario = db.get(
                Usuario,
                solicitacao_data["id_solicitante"]
            )

            if not usuario:
                raise KeyError(
                    f"Usuário de ID "
                    f"{solicitacao_data['id_solicitante']} "
                    f"não encontrado."
                )

        # Verifica o autorizador, caso tenha sido informado
        if "id_usuario_autorizador" in solicitacao_data:
            autorizador_id = solicitacao_data[
                "id_usuario_autorizador"
            ]

            if autorizador_id is not None:
                autorizador = db.get(
                    Usuario,
                    autorizador_id
                )

                if not autorizador:
                    raise KeyError(
                        f"Usuário autorizador de ID "
                        f"{autorizador_id} não encontrado."
                    )

        # Uma solicitação já respondida não pode mudar de situação
        nova_situacao = solicitacao_data.get("situacao")

        if (
            nova_situacao is not None
            and solicitacao.situacao in ("aprovado", "recusado")
            and nova_situacao != solicitacao.situacao
        ):
            raise ValueError(
                "Esta solicitação já foi respondida e "
                "não pode mudar de situação."
            )

        # Aprovar uma solicitação pendente já gera o empréstimo
        gerar_emprestimo = (
            nova_situacao == "aprovado"
            and solicitacao.situacao != "aprovado"
        )

        equipamento_emprestimo = None

        if gerar_emprestimo:
            equipamento_emprestimo = db.get(
                Equipamento,
                solicitacao.id_equipamento
            )

            if not equipamento_emprestimo:
                raise KeyError(
                    f"Equipamento de ID "
                    f"{solicitacao.id_equipamento} não encontrado."
                )

            if equipamento_emprestimo.status_equipamento != "disponivel":
                raise ValueError(
                    "Não é possível aprovar: o equipamento "
                    "não está mais disponível."
                )

        # Atualiza os campos recebidos
        for key, value in solicitacao_data.items():
            if key != "id_solicitacao":
                setattr(solicitacao, key, value)

        db.add(solicitacao)

        if gerar_emprestimo:
            # Mesma transação: ou aprova e empresta, ou não faz nada
            db.flush()

            emprestimo = Emprestimo(
                id_usuario=solicitacao.id_solicitante,
                id_solicitacao=solicitacao.id_solicitacao,
                id_equipamento=solicitacao.id_equipamento,
                data_prevista_devolucao=solicitacao.data_prevista_devolucao
            )
            db.add(emprestimo)

            equipamento_emprestimo.status_equipamento = "emprestado"
            db.add(equipamento_emprestimo)

        db.commit()
        db.refresh(solicitacao)

        return solicitacao

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Erro de integridade. "
            "Verifique os dados informados."
        ) from e

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Deleta uma solicitação pelo ID
def deletar_solicitacao(
    db: Session,
    solicitacao_id: int
):
    try:
        solicitacao = db.get(
            Solicitacao,
            solicitacao_id
        )

        if not solicitacao:
            raise KeyError(
                f"Solicitação de ID "
                f"{solicitacao_id} não encontrada."
            )

        db.delete(solicitacao)
        db.commit()

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Não é possível excluir esta solicitação, "
            "pois existem empréstimos vinculados a ela."
        ) from e

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e
