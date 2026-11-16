import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.Config import settings

from routes.nivel_acesso_routes import nivel_acesso_router
from routes.categoria_equipamento_routes import categoria_equipamento_router
from routes.listagens_routes import listagens_router
from routes.usuario_routes import usuario_router
from routes.equipamento_routes import equipamento_router
from routes.solicitacao_routes import solicitacao_router
from routes.emprestimo_routes import emprestimo_router
from routes.auth_routes import auth_routes

app = FastAPI(title="Controle de Equipamentos de TI - API")


# ====== CORS ======
# O front-end roda em outro endereço (ex.: Live Server na porta 5500) e o FastAPI (porta 8000)
# cuida somente dos dados. O navegador só deixa a página chamar a API se ela estiver nesta lista.
ORIGENS_PERMITIDAS = [
    origem.strip() for origem in settings.CORS_ORIGENS.split(",") if origem.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,   # o login usa token no cabeçalho, não cookies
)


# ====== Mensagens de erro em português ======
ROTULOS_CAMPOS = {
    "nome": "Nome",
    "email": "E-mail",
    "senha": "Senha",
    "cpf": "CPF",
    "modelo": "Modelo",
    "descricao": "Descrição",
    "numero_patrimonio": "Número de patrimônio",
    "id_categoria": "Categoria",
    "id_equipamento": "Equipamento",
    "id_solicitante": "Solicitante",
    "id_usuario": "Usuário",
    "id_solicitacao": "Solicitação",
    "nivel_acesso": "Nível de acesso",
    "status_usuario": "Status do usuário",
    "status_equipamento": "Status do equipamento",
    "situacao": "Situação",
    "data_retirada_solicitada": "Data de retirada",
    "data_prevista_devolucao": "Data de devolução prevista",
    "data_devolucao": "Data de devolução",
    "observacoes_solicitante": "Observações",
    "observacoes_autorizador": "Observação do responsável",
    "observacoes": "Observações",
    "pagina": "Página",
    "por_pagina": "Itens por página",
    "busca": "Busca",
    "numero": "Número de patrimônio",
}


def _traduzir_erro(erro: dict) -> str:
    tipo = erro.get("type", "")
    local = erro.get("loc", ())
    campo = local[-1] if local and local[-1] != "body" else ""
    rotulo = ROTULOS_CAMPOS.get(str(campo), str(campo)) or "Campo"

    # Mensagens que nós mesmos escrevemos nas validações
    if tipo == "value_error":
        return str(erro.get("msg", "")).removeprefix("Value error, ")

    if tipo == "json_invalid":
        return "Os dados enviados não estão em um formato válido."

    if tipo == "missing":
        return f"Preencha o campo: {rotulo}."

    if tipo in ("int_parsing", "int_type", "int_from_float"):
        return f"{rotulo}: informe um número válido."

    if tipo.startswith("datetime") or tipo.startswith("date"):
        return f"{rotulo}: informe uma data válida."

    if tipo in ("string_type", "string_too_short"):
        return f"{rotulo}: informe um texto válido."

    if tipo == "string_too_long":
        limite = erro.get("ctx", {}).get("max_length", "")
        return f"{rotulo}: use no máximo {limite} caracteres."

    if tipo in ("greater_than_equal", "less_than_equal"):
        return f"{rotulo}: valor fora do limite permitido."

    return f"{rotulo}: valor inválido."


@app.exception_handler(RequestValidationError)
async def erro_de_validacao(request: Request, exc: RequestValidationError):
    mensagens = []

    for erro in exc.errors():
        texto = _traduzir_erro(erro)

        if texto not in mensagens:
            mensagens.append(texto)

    return JSONResponse(
        status_code=422,
        content={"detail": " ".join(mensagens)}
    )


MENSAGENS_HTTP = {
    "Not authenticated": "Você precisa entrar no sistema para continuar.",
    "Not Found": "O endereço solicitado não foi encontrado.",
    "Method Not Allowed": "Operação não permitida para este endereço.",
}


@app.exception_handler(StarletteHTTPException)
async def erro_http(request: Request, exc: StarletteHTTPException):
    detalhe = exc.detail

    if isinstance(detalhe, str):
        detalhe = MENSAGENS_HTTP.get(detalhe, detalhe)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detalhe},
        headers=getattr(exc, "headers", None)
    )


# Inclui as rotas de cada entidade do sistema
# As listagens vêm primeiro: /solicitacoes/paginado não pode cair em /solicitacoes/{id}
app.include_router(listagens_router)
app.include_router(nivel_acesso_router)
app.include_router(categoria_equipamento_router)
app.include_router(usuario_router)
app.include_router(equipamento_router)
app.include_router(solicitacao_router)
app.include_router(emprestimo_router)
app.include_router(auth_routes)


# ====== Erro inesperado (500) ======
# Erros 500 passam por fora do CORS; sem isto o navegador mostraria "erro de CORS"
# em vez de uma mensagem. O erro completo continua aparecendo no terminal.
@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception):
    traceback.print_exception(type(exc), exc, exc.__traceback__)

    resposta = JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente."}
    )

    origem = request.headers.get("origin")

    if origem in ORIGENS_PERMITIDAS:
        resposta.headers["Access-Control-Allow-Origin"] = origem
        resposta.headers["Vary"] = "Origin"

    return resposta


# A porta da API entrega somente dados; as páginas ficam no servidor do front-end
@app.get("/", include_in_schema=False)
def raiz():
    return {
        "mensagem": "API do Controle de Equipamentos de TI em execução.",
        "documentacao": "/docs"
    }
