from core.security import cria_hash_senha
from sqlmodel import Session, select

from entidades.models import Usuario, NivelAcesso

from entidades.schemas import UsuarioCriar, UsuarioAtualizar

from sqlalchemy.exc import OperationalError, IntegrityError


# Confere se e-mail ou CPF já pertencem a outro usuário
def _verificar_duplicidade(
    db: Session,
    email: str | None = None,
    cpf: str | None = None,
    ignorar_id: int | None = None
):
    if email:
        statement = select(Usuario).where(Usuario.email == email)
        existente = db.exec(statement).first()

        if existente and existente.id_usuario != ignorar_id:
            raise ValueError(
                "Já existe um usuário cadastrado com este e-mail."
            )

    if cpf:
        statement = select(Usuario).where(Usuario.cpf == cpf)
        existente = db.exec(statement).first()

        if existente and existente.id_usuario != ignorar_id:
            raise ValueError(
                "Já existe um usuário cadastrado com este CPF."
            )


# Cadastra um novo usuário no banco de dados
def cadastrar_usuario(
    usuario_data: UsuarioCriar,
    db: Session
):
    try:
        # Verifica se o nível de acesso informado existe
        nivel = db.get(
            NivelAcesso,
            usuario_data.nivel_acesso
        )

        if not nivel:
            raise KeyError(
                f"Nível de acesso de ID "
                f"{usuario_data.nivel_acesso} não encontrado."
            )

        # E-mail e CPF não podem repetir
        _verificar_duplicidade(
            db,
            email=usuario_data.email,
            cpf=usuario_data.cpf
        )

        # Cria um objeto do tipo Usuario
        dados_usuario = usuario_data.model_dump()

        dados_usuario["senha"] = cria_hash_senha(
            dados_usuario["senha"]
        )

        usuario = Usuario(**dados_usuario)

        db.add(usuario)
        db.commit()
        db.refresh(usuario)

        return usuario

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Verifique os dados informados. "
            "E-mail ou CPF podem já estar cadastrados."
        ) from e


# Busca todos os usuários cadastrados
def buscar_usuarios(db: Session):
    try:
        statement = select(Usuario)
        usuarios = db.exec(statement).all()

        return usuarios

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Busca um usuário pelo ID
def buscar_usuario(
    db: Session,
    usuario_id: int
):
    try:
        usuario = db.get(
            Usuario,
            usuario_id
        )

        if not usuario:
            raise KeyError(
                f"Usuário de ID {usuario_id} não encontrado."
            )

        return usuario

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Atualiza um usuário existente
def atualizar_usuario(
    db: Session,
    usuario_id: int,
    dados_atualizados: UsuarioAtualizar
):
    try:
        # Busca o usuário pelo ID
        usuario = db.get(
            Usuario,
            usuario_id
        )

        if not usuario:
            raise KeyError(
                f"Usuário de ID {usuario_id} não encontrado."
            )

        # CPF e senha nunca são alterados pela API
        # (se necessário, a alteração é feita direto no banco)
        usuario_data = dados_atualizados.model_dump(
            exclude_unset=True,
            exclude={"id_usuario", "cpf", "senha"}
        )

        # Se o nível de acesso foi alterado,
        # verifica se o novo nível existe
        if "nivel_acesso" in usuario_data:
            nivel = db.get(
                NivelAcesso,
                usuario_data["nivel_acesso"]
            )

            if not nivel:
                raise KeyError(
                    f"Nível de acesso de ID "
                    f"{usuario_data['nivel_acesso']} não encontrado."
                )

        # O novo e-mail não pode pertencer a outro usuário
        if "email" in usuario_data:
            _verificar_duplicidade(
                db,
                email=usuario_data["email"],
                ignorar_id=usuario_id
            )

        # Atualiza os campos recebidos
        for key, value in usuario_data.items():
            setattr(usuario, key, value)

        db.add(usuario)
        db.commit()
        db.refresh(usuario)

        return usuario

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Erro de integridade. Verifique os dados informados."
        ) from e

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e


# Deleta um usuário pelo ID
def deletar_usuario(
    db: Session,
    usuario_id: int
):
    try:
        usuario = db.get(
            Usuario,
            usuario_id
        )

        if not usuario:
            raise KeyError(
                f"Usuário de ID {usuario_id} não encontrado."
            )

        db.delete(usuario)
        db.commit()

    except IntegrityError as e:
        db.rollback()

        raise ValueError(
            "Não é possível excluir este usuário, "
            "pois existem registros vinculados a ele."
        ) from e

    except OperationalError as e:
        db.rollback()

        raise RuntimeError(
            "Falha na conexão com o banco de dados."
        ) from e
