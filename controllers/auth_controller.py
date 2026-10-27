
# Importações básicas para consultar o banco de dados
from sqlmodel import Session, select

# Importa os modelos existentes no nosso projeto
from entidades.models import Usuario, NivelAcesso

# Importa as funções de segurança para senha e token JWT
from core.security import verifica_senha, criar_token


# ====== Realiza o login do usuário ======
def fazer_login(db: Session, username: str, password: str):
    # Busca o usuário pelo e-mail informado no login
    usuario = db.exec(
        select(Usuario).where(Usuario.email == username)
    ).first()

    # Verifica se o usuário existe e se a senha está correta
    if usuario is None or not verifica_senha(password, usuario.senha):
        raise ValueError("Credenciais inválidas.")

    # Verifica se o usuário está ativo antes de permitir o login
    if usuario.status_usuario != "ativo":
        raise ValueError("Usuário inativo.")

    # Busca o nível de acesso associado ao usuário
    nivel = db.get(NivelAcesso, usuario.nivel_acesso)

    # Impede o login caso o nível de acesso não exista
    if nivel is None:
        raise ValueError("Nível de acesso não encontrado.")

    # Converte o nível cadastrado no banco em um papel para o token
    roles = [nivel.nome]

    # Cria o token JWT usando o ID do usuário e seu papel
    token = criar_token(
        str(usuario.id_usuario),
        roles=roles
    )

    # Retorna o token para o cliente utilizar nas próximas requisições
    return {
        "access_token": token,
        "token_type": "bearer"
    }
