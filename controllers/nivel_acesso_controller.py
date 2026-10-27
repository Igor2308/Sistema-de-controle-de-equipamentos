from sqlmodel import Session, select

from entidades.models import NivelAcesso

from sqlalchemy.exc import OperationalError, IntegrityError


# Cadastra um novo nível de acesso no banco de dados

def cadastrar_nivel_acesso(nivel_data: NivelAcesso, db: Session):

    try:

        # Cria um objeto do tipo NivelAcesso
        nivel = NivelAcesso(**nivel_data.model_dump())

        db.add(nivel)
        db.commit()
        db.refresh(nivel)

        return nivel

    except OperationalError as e:

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e

    except IntegrityError as e:

        db.rollback()

        raise ValueError(
            "Verifique os dados informados"
        ) from e


# Busca todos os níveis de acesso cadastrados

def buscar_niveis_acesso(db: Session):

    try:

        # Cria uma consulta para buscar todos os níveis
        statement = select(NivelAcesso)

        niveis = db.exec(statement).all()

        return niveis

    except OperationalError as e:

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e


# Busca um nível de acesso pelo ID

def buscar_nivel_acesso(db: Session, nivel_id: int):

    try:

        # Busca o nível pelo ID
        nivel = db.get(NivelAcesso, nivel_id)

        # Verifica se o nível existe
        if not nivel:

            raise KeyError(
                f"Nível de acesso de ID {nivel_id} não encontrado."
            )

        return nivel

    except OperationalError as e:

        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e


# Atualiza um nível de acesso existente

def atualizar_nivel_acesso(
    db: Session,
    nivel_id: int,
    dados_atualizados: NivelAcesso
):

    try:

        # Busca o nível pelo ID
        nivel = db.get(NivelAcesso, nivel_id)

        # Verifica se o nível existe
        if not nivel:

            raise KeyError(
                f"Nível de acesso de ID {nivel_id} não encontrado."
            )

        nivel_data = dados_atualizados.model_dump(exclude_unset=True)

        # Atualiza os campos recebidos
        for key, value in nivel_data.items():

            # Não altera a chave primária
            if key != "id_acesso":
                setattr(nivel, key, value)

        db.add(nivel)
        db.commit()
        db.refresh(nivel)

        return nivel

    except IntegrityError as e:

        db.rollback()

        raise ValueError(
            "Erro de integridade. Verifique os dados informados."
        ) from e

    except OperationalError as e:

        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e


# Deleta um nível de acesso pelo ID

def deletar_nivel_acesso(db: Session, nivel_id: int):

    try:

        # Busca o nível pelo ID
        nivel = db.get(NivelAcesso, nivel_id)

        # Verifica se o nível existe
        if not nivel:

            raise KeyError(
                f"Nível de acesso de ID {nivel_id} não encontrado."
            )

        # Tenta excluir o nível
        db.delete(nivel)
        db.commit()

    except IntegrityError as e:

        # Impede a exclusão caso existam usuários vinculados
        db.rollback()

        raise ValueError(
            "Não é possível excluir este nível de acesso, "
            "pois existem usuários vinculados a ele."
        ) from e

    except OperationalError as e:

        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e