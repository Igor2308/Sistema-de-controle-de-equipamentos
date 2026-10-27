from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, field_validator

from core.validacoes import (
    validar_email,
    validar_cpf,
    validar_texto,
)

# Schema utilizado para devolver um usuário pela API
# A senha não faz parte deste schema
class UsuarioResposta(BaseModel):

    id_usuario: int
    nome: str
    email: str
    cpf: str
    nivel_acesso: int
    status_usuario: str
    data_criacao: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Schemas de ENTRADA
# Os modelos "table=True" do SQLModel não validam nem convertem tipos,
# então uma data enviada como texto chegava ao MySQL ainda como str
# ("'str' object has no attribute 'utcoffset'").
# Estes schemas usam o Pydantic puro, que converte o texto em datetime.
# ============================================================

def _datetime_ingenuo(valor):
    """Converte para datetime sem fuso (o banco usa DATETIME simples)."""
    if isinstance(valor, datetime) and valor.tzinfo is not None:
        return valor.astimezone(timezone.utc).replace(tzinfo=None)
    return valor


class _EntradaComDatas(BaseModel):
    @field_validator(
        "data_retirada_solicitada",
        "data_prevista_devolucao",
        "data_autorizacao",
        "data_devolucao",
        check_fields=False,
        mode="after",
    )
    @classmethod
    def _sem_fuso(cls, valor):
        return _datetime_ingenuo(valor)


# ----- Solicitações -----
class SolicitacaoCriar(_EntradaComDatas):
    id_equipamento: int
    id_solicitante: int | None = None  # a rota usa o usuário do token
    data_retirada_solicitada: datetime
    data_prevista_devolucao: datetime
    observacoes_solicitante: str | None = None
    situacao: str | None = None  # ignorado: toda solicitação nasce pendente


class SolicitacaoAtualizar(_EntradaComDatas):
    id_equipamento: int | None = None
    id_solicitante: int | None = None
    id_usuario_autorizador: int | None = None
    data_retirada_solicitada: datetime | None = None
    data_prevista_devolucao: datetime | None = None
    data_autorizacao: datetime | None = None
    situacao: str | None = None
    observacoes_solicitante: str | None = None
    observacoes_autorizador: str | None = None


# ----- Empréstimos -----
class EmprestimoCriar(_EntradaComDatas):
    id_usuario: int
    id_solicitacao: int
    id_equipamento: int
    data_prevista_devolucao: datetime
    data_devolucao: datetime | None = None
    observacoes: str | None = None


class EmprestimoAtualizar(_EntradaComDatas):
    id_usuario: int | None = None
    id_solicitacao: int | None = None
    id_equipamento: int | None = None
    data_prevista_devolucao: datetime | None = None
    data_devolucao: datetime | None = None
    observacoes: str | None = None


# ----- Usuários -----
class UsuarioCriar(BaseModel):
    nome: str
    email: str
    cpf: str
    senha: str
    nivel_acesso: int = 1

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return validar_texto(v, "o nome completo", minimo=3, maximo=100)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return validar_email(v)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v):
        return validar_cpf(v)

    @field_validator("senha")
    @classmethod
    def _senha(cls, v):
        if len(v or "") < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres.")
        if len(v) > 128:
            raise ValueError("A senha pode ter no máximo 128 caracteres.")
        return v


class UsuarioAtualizar(BaseModel):
    """CPF e senha NÃO fazem parte deste schema de propósito:
    pela API eles não podem ser alterados (somente direto no banco).
    Se vierem no corpo da requisição, são simplesmente ignorados."""
    nome: str | None = None
    email: str | None = None
    nivel_acesso: int | None = None
    status_usuario: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return validar_texto(v, "o nome completo", minimo=3, maximo=100)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return validar_email(v)

    @field_validator("status_usuario")
    @classmethod
    def _status(cls, v):
        if v not in ("ativo", "inativo"):
            raise ValueError("O status do usuário deve ser ativo ou inativo.")
        return v


# ----- Equipamentos -----
STATUS_EQUIPAMENTO = ("disponivel", "emprestado", "manutencao", "inativo")


def _status_equipamento(v):
    if v not in STATUS_EQUIPAMENTO:
        raise ValueError("Status de equipamento inválido.")
    return v


class EquipamentoCriar(BaseModel):
    nome: str
    modelo: str
    numero_patrimonio: str
    id_categoria: int
    descricao: str | None = None
    status_equipamento: str = "disponivel"

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return validar_texto(v, "o nome do equipamento", minimo=2, maximo=100)

    @field_validator("modelo")
    @classmethod
    def _modelo(cls, v):
        return validar_texto(v, "o modelo", minimo=1, maximo=100)

    @field_validator("numero_patrimonio")
    @classmethod
    def _patrimonio(cls, v):
        return validar_texto(
            v, "o número de patrimônio", minimo=1, maximo=100
        )

    @field_validator("descricao")
    @classmethod
    def _descricao(cls, v):
        return validar_texto(
            v, "a descrição", maximo=100, obrigatorio=False
        )

    @field_validator("status_equipamento")
    @classmethod
    def _status(cls, v):
        return _status_equipamento(v)


class EquipamentoAtualizar(BaseModel):
    nome: str | None = None
    modelo: str | None = None
    numero_patrimonio: str | None = None
    id_categoria: int | None = None
    descricao: str | None = None
    status_equipamento: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return validar_texto(v, "o nome do equipamento", minimo=2, maximo=100)

    @field_validator("modelo")
    @classmethod
    def _modelo(cls, v):
        return validar_texto(v, "o modelo", minimo=1, maximo=100)

    @field_validator("numero_patrimonio")
    @classmethod
    def _patrimonio(cls, v):
        return validar_texto(
            v, "o número de patrimônio", minimo=1, maximo=100
        )

    @field_validator("descricao")
    @classmethod
    def _descricao(cls, v):
        return validar_texto(
            v, "a descrição", maximo=100, obrigatorio=False
        )

    @field_validator("status_equipamento")
    @classmethod
    def _status(cls, v):
        return _status_equipamento(v)


# ----- Categorias -----
class CategoriaCriar(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return validar_texto(
            v, "o nome da categoria", minimo=2, maximo=50
        )
