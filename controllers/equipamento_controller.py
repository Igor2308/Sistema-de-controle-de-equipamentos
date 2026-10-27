
from math import ceil

from sqlmodel import Session, select, col
from sqlalchemy import func, or_

from entidades.models import (
    Equipamento,
    CategoriaEquipamento,
    Emprestimo
)
from entidades.schemas import (
    EquipamentoCriar,
    EquipamentoAtualizar,
    STATUS_EQUIPAMENTO
)

from sqlalchemy.exc import OperationalError, IntegrityError


# Verifica se já existe equipamento com o número de patrimônio informado
def patrimonio_existe(
    db: Session,
    numero: str,
    ignorar_id: int | None = None
) -> bool:
    try:
        statement = select(Equipamento.id_equipamento).where(
            Equipamento.numero_patrimonio == numero.strip()
        )

        if ignorar_id is not None:
            statement = statement.where(
                Equipamento.id_equipamento != ignorar_id
            )

        return db.exec(statement).first() is not None

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Lista equipamentos de forma paginada (a consulta já filtra no banco)
def buscar_equipamentos_paginado(
    db: Session,
    pagina: int = 1,
    por_pagina: int = 25,
    status: str | None = None,
    busca: str | None = None,
    ordenar: str | None = None,
    direcao: str | None = None
):
    try:
        if status and status not in STATUS_EQUIPAMENTO:
            raise ValueError("Status de equipamento inválido.")

        filtros = []

        if status:
            filtros.append(col(Equipamento.status_equipamento) == status)

        termo = (busca or "").strip()

        if termo:
            # Escapa curingas para a busca ser literal
            seguro = (
                termo.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            padrao = f"%{seguro}%"

            filtros.append(
                or_(
                    col(Equipamento.nome).like(padrao),
                    col(Equipamento.modelo).like(padrao),
                    col(Equipamento.numero_patrimonio).like(padrao)
                )
            )

        mapa = {
            "id": col(Equipamento.id_equipamento),
            "nome": col(Equipamento.nome),
            "modelo": col(Equipamento.modelo),
            "patrimonio": col(Equipamento.numero_patrimonio),
            "categoria": col(CategoriaEquipamento.nome),
            "status": col(Equipamento.status_equipamento),
        }
        chave = ordenar or "id"

        if chave not in mapa:
            raise ValueError("Ordenação inválida.")

        descendente = (direcao or "desc") == "desc"
        coluna = mapa[chave]
        id_equip = col(Equipamento.id_equipamento)

        total = db.exec(
            select(func.count()).select_from(Equipamento).where(*filtros)
        ).one()

        total_paginas = max(1, ceil(total / por_pagina))

        # Página além do fim volta para a última existente
        pagina = min(max(1, pagina), total_paginas)

        consulta = select(Equipamento).where(*filtros)

        if chave == "categoria":
            consulta = consulta.join(
                CategoriaEquipamento,
                col(CategoriaEquipamento.id_categoria)
                == col(Equipamento.id_categoria)
            )

        itens = db.exec(
            consulta
            .order_by(
                coluna.desc() if descendente else coluna.asc(),
                id_equip.desc() if descendente else id_equip.asc()
            )
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        ).all()

        return {
            "itens": itens,
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": total_paginas
        }

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Conta os equipamentos por status sem carregar a lista inteira
def resumo_equipamentos(db: Session):
    try:
        linhas = db.exec(
            select(
                col(Equipamento.status_equipamento),
                func.count()
            ).group_by(col(Equipamento.status_equipamento))
        ).all()

        resumo = {status: 0 for status in STATUS_EQUIPAMENTO}

        for status, quantidade in linhas:
            resumo[status] = quantidade

        resumo["total"] = sum(resumo.values())

        return resumo

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Cadastra um novo equipamento no banco de dados
def cadastrar_equipamento(
    equipamento_data: EquipamentoCriar,
    db: Session
):
    try:
        # Verifica se a categoria informada existe
        categoria = db.get(
            CategoriaEquipamento,
            equipamento_data.id_categoria
        )

        if not categoria:
            raise KeyError(
                f"Categoria de equipamento de ID "
                f"{equipamento_data.id_categoria} não encontrada."
            )

        # O número de patrimônio não pode repetir
        if patrimonio_existe(db, equipamento_data.numero_patrimonio):
            raise ValueError(
                "Já existe um equipamento cadastrado com "
                "este número de patrimônio."
            )

        # Cria um objeto do tipo Equipamento
        equipamento = Equipamento(
            **equipamento_data.model_dump()
        )

        db.add(equipamento)
        db.commit()
        db.refresh(equipamento)

        return equipamento

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Verifique os dados informados. "
            "O número de patrimônio pode já estar cadastrado."
        ) from e


# Busca todos os equipamentos cadastrados
def buscar_equipamentos(db: Session):
    try:
        statement = select(Equipamento)
        equipamentos = db.exec(statement).all()

        return equipamentos

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Busca um equipamento pelo ID
def buscar_equipamento(
    db: Session,
    equipamento_id: int
):
    try:
        equipamento = db.get(
            Equipamento,
            equipamento_id
        )

        if not equipamento:
            raise KeyError(
                f"Equipamento de ID "
                f"{equipamento_id} não encontrado."
            )

        return equipamento

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Atualiza um equipamento existente
def atualizar_equipamento(
    db: Session,
    equipamento_id: int,
    dados_atualizados: EquipamentoAtualizar
):
    try:
        # Busca o equipamento pelo ID
        equipamento = db.get(
            Equipamento,
            equipamento_id
        )

        if not equipamento:
            raise KeyError(
                f"Equipamento de ID "
                f"{equipamento_id} não encontrado."
            )

        equipamento_data = dados_atualizados.model_dump(
            exclude_unset=True
        )

        # Impede alterar o identificador do equipamento
        equipamento_data.pop("id_equipamento", None)

        # Se o patrimônio mudou, não pode coincidir com outro equipamento
        if "numero_patrimonio" in equipamento_data and patrimonio_existe(
            db,
            equipamento_data["numero_patrimonio"],
            ignorar_id=equipamento_id
        ):
            raise ValueError(
                "Já existe outro equipamento cadastrado com "
                "este número de patrimônio."
            )

        # Se a categoria foi alterada,
        # verifica se a nova categoria existe
        if "id_categoria" in equipamento_data:
            categoria = db.get(
                CategoriaEquipamento,
                equipamento_data["id_categoria"]
            )

            if not categoria:
                raise KeyError(
                    f"Categoria de equipamento de ID "
                    f"{equipamento_data['id_categoria']} não encontrada."
                )

        # Impede marcar como disponível um equipamento
        # que ainda possui empréstimo ativo
        if (
            equipamento_data.get("status_equipamento")
            == "disponivel"
        ):
            statement = select(Emprestimo).where(
                Emprestimo.id_equipamento == equipamento_id,
                Emprestimo.data_devolucao.is_(None)
            )

            emprestimo_ativo = db.exec(statement).first()

            if emprestimo_ativo:
                raise ValueError(
                    "Não é possível marcar o equipamento como disponível "
                    "enquanto existir um empréstimo ativo."
                )

        # Atualiza os campos recebidos
        for key, value in equipamento_data.items():
            setattr(equipamento, key, value)

        db.add(equipamento)
        db.commit()
        db.refresh(equipamento)

        return equipamento

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


# Deleta um equipamento pelo ID
def deletar_equipamento(
    db: Session,
    equipamento_id: int
):
    try:
        equipamento = db.get(
            Equipamento,
            equipamento_id
        )

        if not equipamento:
            raise KeyError(
                f"Equipamento de ID "
                f"{equipamento_id} não encontrado."
            )

        # Impede excluir equipamento com empréstimo ativo
        statement = select(Emprestimo).where(
            Emprestimo.id_equipamento == equipamento_id,
            Emprestimo.data_devolucao.is_(None)
        )

        emprestimo_ativo = db.exec(statement).first()

        if emprestimo_ativo:
            raise ValueError(
                "Não é possível excluir um equipamento "
                "que possui um empréstimo ativo."
            )

        db.delete(equipamento)
        db.commit()

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Não é possível excluir este equipamento, "
            "pois existem solicitações ou empréstimos vinculados a ele."
        ) from e

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e
