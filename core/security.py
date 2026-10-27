from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from config.Config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
#====== Criptografa senha ==========
def cria_hash_senha(senha:str):
    return pwd_context.hash(senha)

#===== Verifica senha se é correta =========
def verifica_senha(senha:str, senha_hash:str):
    return pwd_context.verify(senha,senha_hash)

#===== Criando token de acesso
def criar_token(info:str, roles:list[str]|str):
    vence_em = datetime.now(timezone.utc)+timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    print(f"Vencimento em:{vence_em}")
    payload={
        "sub":info,
        "roles":roles,
        "exp":vence_em,
        "iss":settings.JWT_ISSUER
    }
    return jwt.encode(payload,settings.JWT_SECRET_KEY,settings.JWT_ALGORITHM)
#====== Decodificando token
# Lança jwt.InvalidTokenError (se inválido)por qualquer motivo
def decodificar_token(token: str):
    
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
    )
   ###Colocar verificações caso necessárias
    return payload