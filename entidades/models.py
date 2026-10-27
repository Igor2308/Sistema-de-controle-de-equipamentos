from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, text, String
from sqlmodel import SQLModel, Field
from pydantic import BaseModel, field_validator

from core.validacoes import validar_email_login


class NivelAcesso(SQLModel, table=True):

    __tablename__ = "nivel_acesso"
    id_acesso: int | None = Field(default=None, primary_key=True)
    nome: str = Field(sa_column=Column(String(50), nullable=False))


class CategoriaEquipamento(SQLModel, table=True):

    __tablename__ = "categoria_equipamento"

    id_categoria: int | None = Field(default=None, primary_key=True)

    nome: str = Field(max_length=50, nullable=False, unique=True)


class Usuario(SQLModel, table=True):

    __tablename__ = "usuarios"

    id_usuario: int | None = Field(default=None, primary_key=True)

    nome: str = Field(max_length=100, nullable=False)

    email: str = Field(max_length=150, nullable=False, unique=True)

    cpf: str = Field(max_length=20, nullable=False, unique=True)

    senha: str = Field(max_length=255, nullable=False)

    nivel_acesso: int = Field(foreign_key="nivel_acesso.id_acesso", nullable=False)

    status_usuario: str = Field(
        default="ativo",
        sa_column=Column(
            Enum("ativo", "inativo"),
            nullable=False
        )
         )

    data_criacao: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=True,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )


class Equipamento(SQLModel, table=True):

    __tablename__ = "equipamentos"

    id_equipamento: int | None = Field(default=None, primary_key=True)

    nome: str = Field(max_length=100, nullable=False)

    modelo: str | None = Field(default=None, max_length=100)

    descricao: str | None = Field(default=None, max_length=100)

    numero_patrimonio: str = Field(max_length=100, nullable=False, unique=True)

    id_categoria: int = Field(
        foreign_key="categoria_equipamento.id_categoria",
        nullable=False
    )

    status_equipamento: str = Field(
        default="disponivel",
        sa_column=Column(
            Enum(
                "disponivel",
                "emprestado",
                "manutencao",
                "inativo"
            ),
            nullable=False
        )
    )


class Solicitacao(SQLModel, table=True):

    __tablename__ = "solicitacoes"

    id_solicitacao: int | None = Field(default=None, primary_key=True)

    id_equipamento: int = Field(
        foreign_key="equipamentos.id_equipamento",
        nullable=False
    )

    id_solicitante: int = Field(
        foreign_key="usuarios.id_usuario",
        nullable=False
    )

    id_usuario_autorizador: int | None = Field(
        default=None,
        foreign_key="usuarios.id_usuario"
    )

    # Quando a solicitação foi feita (data e hora)
    data_solicitacao: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=True,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )

    # DateTime puro do SQLAlchemy = DATETIME do MySQL, sem fuso horário
    data_retirada_solicitada: datetime = Field(
        sa_column=Column(DateTime, nullable=False)
    )

    data_prevista_devolucao: datetime = Field(
        sa_column=Column(DateTime, nullable=False)
    )

    data_autorizacao: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )

    situacao: str | None = Field(
        default=None,
        sa_column=Column(
            Enum(
                "pendente",
                "aprovado",
                "recusado"
            )
        )
    )

    observacoes_solicitante: str | None = Field(
        default=None,
        max_length=200
    )

    observacoes_autorizador: str | None = Field(
        default=None,
        max_length=200
    )


class Emprestimo(SQLModel, table=True):

    __tablename__ = "emprestimos"

    id_emprestimo: int | None = Field(default=None, primary_key=True)

    id_usuario: int = Field(
        foreign_key="usuarios.id_usuario",
        nullable=False
    )

    id_solicitacao: int = Field(
        foreign_key="solicitacoes.id_solicitacao",
        nullable=False
    )

    id_equipamento: int = Field(
        foreign_key="equipamentos.id_equipamento",
        nullable=False
    )

    data_prevista_devolucao: datetime = Field(
        sa_column=Column(DateTime, nullable=False)
    )

    data_devolucao: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )

    observacoes: str | None = Field(
        default=None,
        max_length=150
    )

# Parte de autenticação
class UsuarioLogin(BaseModel):
    email: str
    senha: str

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return validar_email_login(v)

    @field_validator("senha")
    @classmethod
    def _senha(cls, v):
        if not v:
            raise ValueError("Informe a senha.")
        return v


class UsuarioAutenticado(BaseModel):
    id_usuario: int
    nome: str
    email: str
    roles: list[str]