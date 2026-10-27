from sqlmodel import Session, select

from entidades.models import CategoriaEquipamento
from entidades.schemas import CategoriaCriar

from sqlalchemy import func
from sqlalchemy.exc import OperationalError, IntegrityError


# Cadastra uma nova categoria de equipamento no banco de dados

def cadastrar_categoria_equipamento(
    categoria_data: CategoriaCriar,
    db: Session
):

    try:

        # Não permite duas categorias com o mesmo nome
        existente = db.exec(
            select(CategoriaEquipamento).where(
                func.lower(CategoriaEquipamento.nome)
                == categoria_data.nome.lower()
            )
        ).first()

        if existente:
            raise ValueError(
                "Já existe uma categoria com este nome."
            )

        # Cria um objeto do tipo CategoriaEquipamento
        categoria = CategoriaEquipamento(**categoria_data.model_dump())

        db.add(categoria)
        db.commit()
        db.refresh(categoria)

        return categoria

    except OperationalError as e:

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e

    except IntegrityError as e:

        # Desfaz a operação caso aconteça um erro
        db.rollback()

        raise ValueError(
            "Verifique os dados informados. "
            "A categoria pode já estar cadastrada."
        ) from e


# Busca todas as categorias de equipamento cadastradas

def buscar_categorias_equipamento(db: Session):

    try:

        # Cria uma consulta para buscar todas as categorias
        statement = select(CategoriaEquipamento)

        categorias = db.exec(statement).all()

        return categorias

    except OperationalError as e:

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e


# Busca uma categoria de equipamento pelo ID

def buscar_categoria_equipamento(
    db: Session,
    categoria_id: int
):

    try:

        # Busca a categoria pelo ID
        categoria = db.get(CategoriaEquipamento, categoria_id)

        # Verifica se a categoria existe
        if not categoria:

            raise KeyError(
                f"Categoria de equipamento de ID {categoria_id} não encontrada."
            )

        return categoria

    except OperationalError as e:

        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e


# Atualiza uma categoria de equipamento existente

def atualizar_categoria_equipamento(
    db: Session,
    categoria_id: int,
    dados_atualizados: CategoriaEquipamento
):

    try:

        # Busca a categoria pelo seu ID
        categoria = db.get(CategoriaEquipamento, categoria_id)

        # Verifica se a categoria existe
        if not categoria:

            raise KeyError(
                f"Categoria de equipamento de ID {categoria_id} não encontrada."
            )

        categoria_data = dados_atualizados.model_dump(
            exclude_unset=True
        )

        # Percorre os dados recebidos e atualiza os campos da categoria
        for key, value in categoria_data.items():

            if key != "id_categoria":
                setattr(categoria, key, value)

        db.add(categoria)
        db.commit()
        db.refresh(categoria)

        return categoria

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


# Deleta uma categoria de equipamento pelo ID

def deletar_categoria_equipamento(
    db: Session,
    categoria_id: int
):

    try:

        # Busca a categoria pelo ID
        categoria = db.get(CategoriaEquipamento, categoria_id)

        # Verifica se a categoria existe
        if not categoria:

            raise KeyError(
                f"Categoria de equipamento de ID {categoria_id} não encontrada."
            )

        # Tenta excluir a categoria
        db.delete(categoria)
        db.commit()

    except IntegrityError as e:

        # Desfaz a operação caso a categoria possua equipamentos vinculados
        db.rollback()

        raise ValueError(
            "Não é possível excluir esta categoria, "
            "pois existem equipamentos vinculados a ela."
        ) from e

    except OperationalError as e:

        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados"
        ) from e