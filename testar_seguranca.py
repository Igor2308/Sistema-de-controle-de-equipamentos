
import requests
from datetime import datetime, timedelta


# Configurações da API
BASE_URL = "http://127.0.0.1:8000"
SENHA = "Teste123!"

EMAIL_COMUM = "comum.teste@exemplo.com"
EMAIL_GESTOR = "gestor.teste@exemplo.com"
EMAIL_ADMIN = "admin.teste@exemplo.com"

total_testes = 0
total_aprovados = 0
total_falhas = 0


def registrar_teste(descricao, condicao, resposta=None):
    global total_testes, total_aprovados, total_falhas

    total_testes += 1

    if condicao:
        total_aprovados += 1
        print(f"[PASSOU] {descricao}")
    else:
        total_falhas += 1
        print(f"[FALHOU] {descricao}")

        if resposta is not None:
            print(f"         Status: {resposta.status_code}")
            print(f"         Resposta: {resposta.text[:500]}")


def fazer_login(email):
    resposta = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": email,
            "senha": SENHA
        },
        timeout=10
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha no login de {email}: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()["access_token"]


def obter_usuario(token):
    resposta = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha ao consultar usuário: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()


def obter_equipamentos(token):
    resposta = requests.get(
        f"{BASE_URL}/equipamentos",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha ao consultar equipamentos: "
            f"{resposta.status_code} - {resposta.text}"
        )

    dados = resposta.json()

    # Aceita tanto uma lista direta quanto uma lista dentro de um objeto
    if isinstance(dados, list):
        return dados

    if isinstance(dados, dict):
        for chave in ("equipamentos", "items", "data"):
            if isinstance(dados.get(chave), list):
                return dados[chave]

    raise RuntimeError(
        "Não foi possível identificar a lista de equipamentos retornada."
    )


def payload_solicitacao(solicitacao):
    # Monta somente os campos da solicitação usados pela API
    campos = [
        "id_equipamento",
        "id_solicitante",
        "id_usuario_autorizador",
        "data_retirada_solicitada",
        "data_prevista_devolucao",
        "data_autorizacao",
        "situacao",
        "observacoes_solicitante",
        "observacoes_autorizador"
    ]

    return {
        campo: solicitacao[campo]
        for campo in campos
        if campo in solicitacao
    }


def executar_testes():
    print("\n=== TESTES DE SEGURANÇA DA API ===\n")

    # Autenticação dos três perfis
    token_comum = fazer_login(EMAIL_COMUM)
    token_gestor = fazer_login(EMAIL_GESTOR)
    token_admin = fazer_login(EMAIL_ADMIN)

    usuario_comum = obter_usuario(token_comum)
    usuario_admin = obter_usuario(token_admin)

    id_comum = usuario_comum["id_usuario"]
    id_admin = usuario_admin["id_usuario"]

    headers_comum = {
        "Authorization": f"Bearer {token_comum}"
    }
    headers_gestor = {
        "Authorization": f"Bearer {token_gestor}"
    }
    headers_admin = {
        "Authorization": f"Bearer {token_admin}"
    }

    # Busca um equipamento existente para usar como base
    equipamentos = obter_equipamentos(token_admin)

    if not equipamentos:
        raise RuntimeError(
            "Não há equipamentos cadastrados para executar os testes."
        )

    equipamento_base = equipamentos[0]

    # Cria um segundo equipamento para testar a troca indevida
    # O patrimônio recebe um identificador único para evitar duplicidade.
    identificador = datetime.now().strftime("%Y%m%d%H%M%S")

    dados_equipamento = {
        "nome": f"Equipamento de Teste {identificador}",
        "modelo": f"Modelo Teste {identificador}",
        "descricao": "Equipamento criado pelo teste de segurança.",
        "numero_patrimonio": f"TESTE{identificador}",
        "id_categoria": equipamento_base["id_categoria"],
        "status_equipamento": "disponivel"
    }

    resposta_equipamento = requests.post(
        f"{BASE_URL}/equipamentos",
        headers=headers_admin,
        json=dados_equipamento,
        timeout=10
    )

    if resposta_equipamento.status_code not in (200, 201):
        raise RuntimeError(
            "Não foi possível criar o segundo equipamento necessário "
            "para o teste. Confira os campos exigidos pela API.\n"
            f"Status: {resposta_equipamento.status_code}\n"
            f"Resposta: {resposta_equipamento.text}"
        )

    equipamento_novo = resposta_equipamento.json()
    id_equipamento_novo = equipamento_novo["id_equipamento"]

    id_equipamento_original = equipamento_base["id_equipamento"]

    # Cria uma solicitação nova com o usuário comum
    agora = datetime.now()
    retirada = (agora + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    devolucao = (agora + timedelta(days=2)).replace(
        hour=17, minute=0, second=0, microsecond=0
    )

    dados_solicitacao = {
        "id_equipamento": id_equipamento_original,
        "id_solicitante": id_comum,
        "data_retirada_solicitada": retirada.isoformat(),
        "data_prevista_devolucao": devolucao.isoformat(),
        "situacao": "pendente",
        "observacoes_solicitante": "Teste automatizado de segurança."
    }

    resposta_solicitacao = requests.post(
        f"{BASE_URL}/solicitacoes",
        headers=headers_comum,
        json=dados_solicitacao,
        timeout=10
    )

    if resposta_solicitacao.status_code not in (200, 201):
        raise RuntimeError(
            "Não foi possível criar a solicitação de teste.\n"
            f"Status: {resposta_solicitacao.status_code}\n"
            f"Resposta: {resposta_solicitacao.text}"
        )

    solicitacao = resposta_solicitacao.json()
    id_solicitacao = solicitacao["id_solicitacao"]

    # TESTE 1: impedir a troca do solicitante
    dados_alterados = payload_solicitacao(solicitacao)
    dados_alterados["id_solicitante"] = id_admin

    resposta = requests.put(
        f"{BASE_URL}/solicitacoes/{id_solicitacao}",
        headers=headers_gestor,
        json=dados_alterados,
        timeout=10
    )

    registrar_teste(
        "Impedir a troca do solicitante de uma solicitação",
        resposta.status_code == 400,
        resposta
    )

    # TESTE 2: impedir a troca do equipamento da solicitação
    dados_alterados = payload_solicitacao(solicitacao)
    dados_alterados["id_equipamento"] = id_equipamento_novo

    resposta = requests.put(
        f"{BASE_URL}/solicitacoes/{id_solicitacao}",
        headers=headers_gestor,
        json=dados_alterados,
        timeout=10
    )

    registrar_teste(
        "Impedir a troca do equipamento de uma solicitação",
        resposta.status_code == 400,
        resposta
    )

    # Aprova a solicitação original para preparar os testes de empréstimo
    dados_aprovacao = payload_solicitacao(solicitacao)
    dados_aprovacao["situacao"] = "aprovado"

    resposta_aprovacao = requests.put(
        f"{BASE_URL}/solicitacoes/{id_solicitacao}",
        headers=headers_gestor,
        json=dados_aprovacao,
        timeout=10
    )

    if resposta_aprovacao.status_code != 200:
        raise RuntimeError(
            "Não foi possível aprovar a solicitação de teste.\n"
            f"Status: {resposta_aprovacao.status_code}\n"
            f"Resposta: {resposta_aprovacao.text}"
        )

    # Dados-base para tentar criar empréstimos inválidos
    dados_emprestimo = {
        "id_usuario": id_comum,
        "id_solicitacao": id_solicitacao,
        "id_equipamento": id_equipamento_original,
        "data_prevista_devolucao": devolucao.isoformat(),
        "data_devolucao": None,
        "observacoes": "Teste automatizado de segurança."
    }

    # TESTE 3: impedir empréstimo para outro usuário
    emprestimo_usuario_incorreto = dados_emprestimo.copy()
    emprestimo_usuario_incorreto["id_usuario"] = id_admin

    resposta = requests.post(
        f"{BASE_URL}/emprestimos",
        headers=headers_gestor,
        json=emprestimo_usuario_incorreto,
        timeout=10
    )

    registrar_teste(
        "Impedir empréstimo para usuário diferente do solicitante",
        resposta.status_code == 400,
        resposta
    )

    # TESTE 4: impedir empréstimo com outro equipamento
    emprestimo_equipamento_incorreto = dados_emprestimo.copy()
    emprestimo_equipamento_incorreto["id_equipamento"] = (
        id_equipamento_novo
    )

    resposta = requests.post(
        f"{BASE_URL}/emprestimos",
        headers=headers_gestor,
        json=emprestimo_equipamento_incorreto,
        timeout=10
    )

    registrar_teste(
        "Impedir empréstimo com equipamento diferente da solicitação",
        resposta.status_code == 400,
        resposta
    )

    # Resumo final
    print("\n=== RESUMO DOS TESTES DE SEGURANÇA ===")
    print(f"Total de testes: {total_testes}")
    print(f"Aprovados: {total_aprovados}")
    print(f"Falhas: {total_falhas}")

    if total_falhas == 0:
        print("\nSUCESSO: todas as regras de segurança foram validadas!")
    else:
        print("\nATENÇÃO: revise os testes que falharam.")


if __name__ == "__main__":
    try:
        executar_testes()
    except requests.RequestException as erro:
        print("\nERRO DE COMUNICAÇÃO COM A API:")
        print(erro)
        print("Confira se o servidor FastAPI está em execução.")
    except Exception as erro:
        print("\nERRO DURANTE OS TESTES:")
        print(erro)
