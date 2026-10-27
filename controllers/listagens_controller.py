"""Listagens paginadas, ordenáveis e já "enriquecidas" com os nomes.

Todo o trabalho pesado (filtro, ordem, contagem, junção de tabelas) é feito
no banco de dados: o navegador recebe apenas a página que vai exibir.
"""
from datetime import datetime, date, time
from math import ceil

from sqlalchemy import case, exists, func, or_
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from entidades.models import Emprestimo, Equipamento, Solicitacao, Usuario
from entidades.schemas import UsuarioResposta


def _ordem(consulta, mapa, ordenar, direcao, padrao, desempate):
    """Aplica a ordenação pedida (somente colunas permitidas)."""
    chave = ordenar or padrao

    if chave not in mapa:
        raise ValueError("Ordenação inválida.")

    descendente = (direcao or "desc") == "desc"
    coluna = mapa[chave]

    return consulta.order_by(
        coluna.desc() if descendente else coluna.asc(),
        desempate.desc() if descendente else desempate.asc()
    )


def _pagina(db, contagem, consulta, pagina, por_pagina):
    total = db.exec(contagem).one()
    total_paginas = max(1, ceil(total / por_pagina))

    # Página além do fim volta para a última existente
    pagina = min(max(1, pagina), total_paginas)

    linhas = db.exec(
        consulta.offset((pagina - 1) * por_pagina).limit(por_pagina)
    ).all()

    return total, pagina, total_paginas, linhas


def _resposta(itens, total, pagina, por_pagina, total_paginas):
    return {
        "itens": itens,
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": total_paginas
    }


def _padrao_busca(termo: str) -> str:
    seguro = (
        termo.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{seguro}%"


def _inicio_de_hoje() -> datetime:
    return datetime.combine(date.today(), time.min)


def _tratar_banco(funcao):
    """Converte falha de conexão em mensagem amigável."""
    def interno(*args, **kwargs):
        db = args[0]
        try:
            return funcao(*args, **kwargs)
        except OperationalError as e:
            db.rollback()
            raise RuntimeError(
                "Falha na conexão com o banco de dados."
            ) from e
    return interno


# ============================================================
# USUÁRIOS
# ============================================================
@_tratar_banco
def usuarios_paginado(
    db: Session,
    pagina: int,
    por_pagina: int,
    busca: str | None,
    ordenar: str | None,
    direcao: str | None
):
    filtros = []
    termo = (busca or "").strip()

    if termo:
        padrao = _padrao_busca(termo)
        filtros.append(
            or_(
                col(Usuario.nome).like(padrao),
                col(Usuario.email).like(padrao),
                col(Usuario.cpf).like(padrao)
            )
        )

    mapa = {
        "id": col(Usuario.id_usuario),
        "nome": col(Usuario.nome),
        "cpf": col(Usuario.cpf),
        "nivel": col(Usuario.nivel_acesso),
        "status": col(Usuario.status_usuario),
        "criacao": col(Usuario.data_criacao),
    }

    consulta = _ordem(
        select(Usuario).where(*filtros),
        mapa, ordenar, direcao, "id", col(Usuario.id_usuario)
    )
    contagem = select(func.count()).select_from(Usuario).where(*filtros)

    total, pagina, total_paginas, linhas = _pagina(
        db, contagem, consulta, pagina, por_pagina
    )

    itens = [UsuarioResposta.model_validate(u) for u in linhas]

    return _resposta(itens, total, pagina, por_pagina, total_paginas)


@_tratar_banco
def usuarios_resumo(db: Session):
    ativos = db.exec(
        select(func.count()).select_from(Usuario).where(
            col(Usuario.status_usuario) == "ativo"
        )
    ).one()

    por_nivel = db.exec(
        select(col(Usuario.nivel_acesso), func.count())
        .group_by(col(Usuario.nivel_acesso))
    ).all()

    return {
        "ativos": ativos,
        "por_nivel": {nivel: qtd for nivel, qtd in por_nivel}
    }


# ============================================================
# SOLICITAÇÕES
# ============================================================
def _filtro_situacao(situacao: str | None):
    if not situacao:
        return []

    if situacao not in ("pendente", "aprovado", "recusado"):
        raise ValueError("Situação inválida.")

    if situacao == "pendente":
        # situacao vazia no banco também conta como pendente
        return [
            or_(
                col(Solicitacao.situacao) == "pendente",
                col(Solicitacao.situacao).is_(None)
            )
        ]

    return [col(Solicitacao.situacao) == situacao]


@_tratar_banco
def solicitacoes_paginado(
    db: Session,
    pagina: int,
    por_pagina: int,
    situacao: str | None,
    ordenar: str | None,
    direcao: str | None,
    id_solicitante: int | None = None
):
    """id_solicitante preenchido = o usuário só enxerga as próprias."""
    filtros = _filtro_situacao(situacao)

    if id_solicitante is not None:
        filtros.append(col(Solicitacao.id_solicitante) == id_solicitante)

    Solicitante = aliased(Usuario)
    Autorizador = aliased(Usuario)

    tem_emprestimo = exists().where(
        Emprestimo.id_solicitacao == Solicitacao.id_solicitacao
    ).correlate(Solicitacao)

    mapa = {
        "id": col(Solicitacao.id_solicitacao),
        "solicitante": Solicitante.nome,
        "equipamento": Equipamento.nome,
        "solicitada": col(Solicitacao.data_solicitacao),
        "retirada": col(Solicitacao.data_retirada_solicitada),
        "situacao": col(Solicitacao.situacao),
        "autorizador": Autorizador.nome,
    }

    consulta = _ordem(
        select(
            Solicitacao,
            Solicitante.nome,
            Equipamento.nome,
            Equipamento.numero_patrimonio,
            Autorizador.nome,
            tem_emprestimo.label("tem_emprestimo")
        )
        .join(
            Solicitante,
            Solicitante.id_usuario == Solicitacao.id_solicitante
        )
        .join(
            Equipamento,
            col(Equipamento.id_equipamento) == Solicitacao.id_equipamento
        )
        .outerjoin(
            Autorizador,
            Autorizador.id_usuario == Solicitacao.id_usuario_autorizador
        )
        .where(*filtros),
        mapa, ordenar, direcao, "id", col(Solicitacao.id_solicitacao)
    )
    contagem = select(func.count()).select_from(Solicitacao).where(*filtros)

    total, pagina, total_paginas, linhas = _pagina(
        db, contagem, consulta, pagina, por_pagina
    )

    itens = []

    for s, nome_solicitante, nome_equip, patrimonio, nome_autorizador, tem in linhas:
        item = s.model_dump()
        item["situacao"] = s.situacao or "pendente"
        item["solicitante_nome"] = nome_solicitante
        item["equipamento_nome"] = nome_equip
        item["equipamento_patrimonio"] = patrimonio
        item["autorizador_nome"] = nome_autorizador
        item["tem_emprestimo"] = bool(tem)
        itens.append(item)

    return _resposta(itens, total, pagina, por_pagina, total_paginas)


@_tratar_banco
def solicitacoes_resumo(db: Session, id_solicitante: int | None = None):
    filtros = []

    if id_solicitante is not None:
        filtros.append(col(Solicitacao.id_solicitante) == id_solicitante)

    linhas = db.exec(
        select(col(Solicitacao.situacao), func.count())
        .where(*filtros)
        .group_by(col(Solicitacao.situacao))
    ).all()

    resumo = {"pendente": 0, "aprovado": 0, "recusado": 0}

    for situacao, qtd in linhas:
        resumo[situacao or "pendente"] += qtd

    resumo["total"] = sum(resumo.values())

    return resumo


# ============================================================
# EMPRÉSTIMOS
# ============================================================
def _status_emprestimo(devolucao, prevista) -> str:
    if devolucao is not None:
        return "devolvido"

    return "atrasado" if prevista < _inicio_de_hoje() else "ativo"


def _filtro_status_emprestimo(status: str | None):
    if not status or status == "todos":
        return []

    hoje = _inicio_de_hoje()
    aberto = col(Emprestimo.data_devolucao).is_(None)

    filtros = {
        "ativo": [aberto, col(Emprestimo.data_prevista_devolucao) >= hoje],
        "atrasado": [aberto, col(Emprestimo.data_prevista_devolucao) < hoje],
        "devolvido": [col(Emprestimo.data_devolucao).is_not(None)],
        "abertos": [aberto],
    }

    if status not in filtros:
        raise ValueError("Status de empréstimo inválido.")

    return filtros[status]


@_tratar_banco
def emprestimos_paginado(
    db: Session,
    pagina: int,
    por_pagina: int,
    status: str | None,
    ordenar: str | None,
    direcao: str | None,
    id_usuario: int | None = None
):
    """id_usuario preenchido = o usuário só enxerga os próprios."""
    filtros = _filtro_status_emprestimo(status)

    if id_usuario is not None:
        filtros.append(col(Emprestimo.id_usuario) == id_usuario)

    hoje = _inicio_de_hoje()

    ordem_status = case(
        (col(Emprestimo.data_devolucao).is_not(None), 2),
        (col(Emprestimo.data_prevista_devolucao) < hoje, 1),
        else_=0
    )

    mapa = {
        "id": col(Emprestimo.id_emprestimo),
        "usuario": Usuario.nome,
        "equipamento": Equipamento.nome,
        "patrimonio": Equipamento.numero_patrimonio,
        "retirada": col(Solicitacao.data_retirada_solicitada),
        "prevista": col(Emprestimo.data_prevista_devolucao),
        "devolvido": col(Emprestimo.data_devolucao),
        "status": ordem_status,
    }

    consulta = _ordem(
        select(
            Emprestimo,
            Usuario.nome,
            Equipamento.nome,
            Equipamento.numero_patrimonio,
            Solicitacao.data_retirada_solicitada
        )
        .join(Usuario, col(Usuario.id_usuario) == Emprestimo.id_usuario)
        .join(
            Equipamento,
            col(Equipamento.id_equipamento) == Emprestimo.id_equipamento
        )
        .join(
            Solicitacao,
            col(Solicitacao.id_solicitacao) == Emprestimo.id_solicitacao
        )
        .where(*filtros),
        mapa, ordenar, direcao, "id", col(Emprestimo.id_emprestimo)
    )
    contagem = select(func.count()).select_from(Emprestimo).where(*filtros)

    total, pagina, total_paginas, linhas = _pagina(
        db, contagem, consulta, pagina, por_pagina
    )

    itens = []

    for e, nome_usuario, nome_equip, patrimonio, retirada in linhas:
        item = e.model_dump()
        item["usuario_nome"] = nome_usuario
        item["equipamento_nome"] = nome_equip
        item["equipamento_patrimonio"] = patrimonio
        item["data_retirada"] = retirada
        item["status"] = _status_emprestimo(
            e.data_devolucao, e.data_prevista_devolucao
        )
        itens.append(item)

    return _resposta(itens, total, pagina, por_pagina, total_paginas)


@_tratar_banco
def emprestimos_resumo(db: Session, id_usuario: int | None = None):
    filtros = []

    if id_usuario is not None:
        filtros.append(col(Emprestimo.id_usuario) == id_usuario)

    hoje = _inicio_de_hoje()

    linhas = db.exec(
        select(
            func.sum(case((col(Emprestimo.data_devolucao).is_not(None), 1), else_=0)),
            func.sum(case(
                (
                    (col(Emprestimo.data_devolucao).is_(None))
                    & (col(Emprestimo.data_prevista_devolucao) < hoje),
                    1
                ),
                else_=0
            )),
            func.count()
        ).select_from(Emprestimo).where(*filtros)
    ).one()

    devolvidos = int(linhas[0] or 0)
    atrasados = int(linhas[1] or 0)
    total = int(linhas[2] or 0)
    abertos = total - devolvidos

    return {
        "ativo": abertos - atrasados,
        "atrasado": atrasados,
        "devolvido": devolvidos,
        "abertos": abertos,
        "total": total
    }
