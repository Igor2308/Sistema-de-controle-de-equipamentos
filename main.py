from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes.nivel_acesso_routes import nivel_acesso_router
from routes.categoria_equipamento_routes import categoria_equipamento_router
from routes.listagens_routes import listagens_router
from routes.usuario_routes import usuario_router
from routes.equipamento_routes import equipamento_router
from routes.solicitacao_routes import solicitacao_router
from routes.emprestimo_routes import emprestimo_router
from routes.auth_routes import auth_routes

app = FastAPI()


# Faz o navegador conferir com o servidor a cada abertura de tela.
# Sem isso ele pode reaproveitar um .js/.css antigo e a tela fica branca.
@app.middleware("http")
async def sem_cache_no_frontend(request: Request, call_next):
    resposta = await call_next(request)

    if request.url.path.startswith("/frontend"):
        resposta.headers["Cache-Control"] = "no-cache"

    return resposta


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


# ====== Front-end ======
# As páginas ficam em /frontend e não colidem com os endpoints da API
PASTA_FRONTEND = Path(__file__).resolve().parent / "frontend"

app.mount(
    "/frontend",
    StaticFiles(directory=PASTA_FRONTEND, html=True),
    name="frontend"
)


# Abrir http://127.0.0.1:8000/ leva direto para o login
@app.get("/", include_in_schema=False)
def pagina_inicial():
    return RedirectResponse(url="/frontend/telas/login.html")
