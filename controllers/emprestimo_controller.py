
from datetime import datetime

from sqlmodel import Session, select

from entidades.models import (
    Emprestimo,
    Usuario,
    Solicitacao,
    Equipamento
)

from entidades.schemas import EmprestimoCriar, EmprestimoAtualizar

from sqlalchemy.exc import OperationalError, IntegrityError


# Confere a coerência das datas do empréstimo (somente o dia é comparado)
def _validar_datas(
    solicitacao: Solicitacao,
    data_prevista: datetime | None = None,
    data_devolucao: datetime | None = None
):
    retirada = solicitacao.data_retirada_solicitada.date()
    hoje = datetime.now().date()

    if data_prevista is not None and data_prevista.date() < retirada:
        raise ValueError(
            "A devolução prevista não pode ser anterior à retirada "
            f"({retirada.strftime('%d/%m/%Y')})."
        )

    if data_devolucao is not None:
        if data_devolucao.date() < retirada:
            raise ValueError(
                "A data de devolução não pode ser anterior à data de "
                f"retirada ({retirada.strftime('%d/%m/%Y')})."
            )

        if data_devolucao.date() > hoje:
            raise ValueError(
                "A data de devolução não pode ser uma data futura."
            )


# Cadastra um novo empréstimo
def cadastrar_emprestimo(
    emprestimo_data: EmprestimoCriar,
    db: Session
):
    try:
        # Verifica se o usuário existe
        usuario = db.get(
            Usuario,
            emprestimo_data.id_usuario
        )

        if not usuario:
            raise KeyError(
                f"Usuário de ID "
                f"{emprestimo_data.id_usuario} não encontrado."
            )

        # Verifica se a solicitação existe
        solicitacao = db.get(
            Solicitacao,
            emprestimo_data.id_solicitacao
        )

        if not solicitacao:
            raise KeyError(
                f"Solicitação de ID "
                f"{emprestimo_data.id_solicitacao} não encontrada."
            )

        # Exige que a solicitação esteja aprovada
        if solicitacao.situacao != "aprovado":
            raise ValueError(
                "Não é possível criar o empréstimo, "
                "pois a solicitação não está aprovada."
            )

        # Confere se o usuário corresponde ao solicitante
        if solicitacao.id_solicitante != emprestimo_data.id_usuario:
            raise ValueError(
                "O usuário informado no empréstimo "
                "não corresponde ao solicitante da solicitação."
            )

        # Verifica se o equipamento existe
        equipamento = db.get(
            Equipamento,
            emprestimo_data.id_equipamento
        )

        if not equipamento:
            raise KeyError(
                f"Equipamento de ID "
                f"{emprestimo_data.id_equipamento} não encontrado."
            )

        # Verifica se o equipamento está disponível
        if equipamento.status_equipamento != "disponivel":
            raise ValueError(
                "Não é possível realizar o empréstimo, "
                "pois o equipamento não está disponível."
            )

        # Confere se o equipamento corresponde à solicitação
        if solicitacao.id_equipamento != emprestimo_data.id_equipamento:
            raise ValueError(
                "O equipamento informado no empréstimo "
                "não corresponde ao equipamento da solicitação."
            )

        # As datas precisam fazer sentido em relação à retirada
        _validar_datas(
            solicitacao,
            emprestimo_data.data_prevista_devolucao,
            emprestimo_data.data_devolucao
        )

        # Cria o empréstimo
        emprestimo = Emprestimo(
            **emprestimo_data.model_dump()
        )

        db.add(emprestimo)

        # Atualiza o status do equipamento
        equipamento.status_equipamento = "emprestado"
        db.add(equipamento)

        db.commit()
        db.refresh(emprestimo)

        return emprestimo

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


# Busca todos os empréstimos
def buscar_emprestimos(db: Session):
    try:
        statement = select(Emprestimo)
        emprestimos = db.exec(statement).all()

        return emprestimos

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Busca um empréstimo pelo ID
def buscar_emprestimo(
    db: Session,
    emprestimo_id: int
):
    try:
        emprestimo = db.get(
            Emprestimo,
            emprestimo_id
        )

        if not emprestimo:
            raise KeyError(
                f"Empréstimo de ID "
                f"{emprestimo_id} não encontrado."
            )

        return emprestimo

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Atualiza um empréstimo existente
def atualizar_emprestimo(
    db: Session,
    emprestimo_id: int,
    dados_atualizados: EmprestimoAtualizar
):
    try:
        # Busca o empréstimo pelo ID
        emprestimo = db.get(
            Emprestimo,
            emprestimo_id
        )

        if not emprestimo:
            raise KeyError(
                f"Empréstimo de ID "
                f"{emprestimo_id} não encontrado."
            )

        emprestimo_data = dados_atualizados.model_dump(
            exclude_unset=True
        )

        # Impede alterar o identificador do empréstimo
        emprestimo_data.pop("id_emprestimo", None)

        # Calcula os vínculos finais, considerando
        # tanto os dados existentes quanto os recebidos
        usuario_id = emprestimo_data.get(
            "id_usuario",
            emprestimo.id_usuario
        )

        solicitacao_id = emprestimo_data.get(
            "id_solicitacao",
            emprestimo.id_solicitacao
        )

        equipamento_id = emprestimo_data.get(
            "id_equipamento",
            emprestimo.id_equipamento
        )

        # Verifica se o usuário existe
        usuario = db.get(Usuario, usuario_id)

        if not usuario:
            raise KeyError(
                f"Usuário de ID {usuario_id} não encontrado."
            )

        # Verifica se a solicitação existe e está aprovada
        solicitacao = db.get(
            Solicitacao,
            solicitacao_id
        )

        if not solicitacao:
            raise KeyError(
                f"Solicitação de ID "
                f"{solicitacao_id} não encontrada."
            )

        if solicitacao.situacao != "aprovado":
            raise ValueError(
                "A solicitação informada não está aprovada."
            )

        # Confere se o usuário corresponde ao solicitante
        if solicitacao.id_solicitante != usuario_id:
            raise ValueError(
                "O usuário do empréstimo deve ser "
                "o solicitante da solicitação."
            )

        # Verifica se o equipamento existe
        equipamento = db.get(
            Equipamento,
            equipamento_id
        )

        if not equipamento:
            raise KeyError(
                f"Equipamento de ID "
                f"{equipamento_id} não encontrado."
            )

        # Confere se o equipamento corresponde à solicitação
        if solicitacao.id_equipamento != equipamento_id:
            raise ValueError(
                "O equipamento do empréstimo deve corresponder "
                "ao equipamento da solicitação."
            )

        # Identifica se o empréstimo está sendo devolvido
        data_devolucao = emprestimo_data.get(
            "data_devolucao",
            emprestimo.data_devolucao
        )

        # Valida só o que está sendo alterado agora
        # (não bloqueia registros antigos que não mudaram)
        nova_devolucao = emprestimo_data.get("data_devolucao")
        nova_prevista = emprestimo_data.get("data_prevista_devolucao")

        if nova_prevista == emprestimo.data_prevista_devolucao:
            nova_prevista = None

        if nova_devolucao == emprestimo.data_devolucao:
            nova_devolucao = None

        _validar_datas(solicitacao, nova_prevista, nova_devolucao)

        # Não permite usar equipamento indisponível
        # em um empréstimo que ainda está ativo
        if data_devolucao is None:
            if (
                equipamento_id != emprestimo.id_equipamento
                and equipamento.status_equipamento != "disponivel"
            ):
                raise ValueError(
                    "O novo equipamento não está disponível."
                )
        equipamento_anterior_id = emprestimo.id_equipamento

        # Atualiza os campos recebidos
        for key, value in emprestimo_data.items():
            setattr(emprestimo, key, value)

                # Se o equipamento mudou, libera o anterior
        if equipamento_id != equipamento_anterior_id:
            equipamento_anterior = db.get(
                Equipamento,
                equipamento_anterior_id
            )

            if equipamento_anterior:
                equipamento_anterior.status_equipamento = "disponivel"
                db.add(equipamento_anterior)

        # Atualiza o status do equipamento relacionado
        if data_devolucao is not None:
            equipamento.status_equipamento = "disponivel"
            db.add(equipamento)
        else:
            equipamento.status_equipamento = "emprestado"
            db.add(equipamento)

        db.add(emprestimo)
        db.commit()
        db.refresh(emprestimo)

        return emprestimo

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


# Deleta um empréstimo pelo ID
def deletar_emprestimo(
    db: Session,
    emprestimo_id: int
):
    try:
        emprestimo = db.get(
            Emprestimo,
            emprestimo_id
        )

        if not emprestimo:
            raise KeyError(
                f"Empréstimo de ID "
                f"{emprestimo_id} não encontrado."
            )

        # Guarda os dados antes de excluir o registro
        equipamento_id = emprestimo.id_equipamento
        emprestimo_ativo = emprestimo.data_devolucao is None

        db.delete(emprestimo)
        db.flush()

        # Só verifica a disponibilidade se o empréstimo
        # excluído ainda estava ativo
        if emprestimo_ativo:
            equipamento = db.get(
                Equipamento,
                equipamento_id
            )

            if equipamento:
                # Confere se existe outro empréstimo ativo
                statement = select(Emprestimo).where(
                    Emprestimo.id_equipamento == equipamento_id,
                    Emprestimo.data_devolucao.is_(None)
                )

                outros_emprestimos = db.exec(statement).first()

                if not outros_emprestimos:
                    equipamento.status_equipamento = "disponivel"
                    db.add(equipamento)

        db.commit()

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Não é possível excluir este empréstimo, "
            "pois existem registros vinculados a ele."
        ) from e

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e
