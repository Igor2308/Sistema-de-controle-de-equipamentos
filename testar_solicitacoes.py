import requests
from datetime import date, datetime, timedelta


# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL_BASE = "http://127.0.0.1:8000"

SENHA_TESTE = "Teste123!"

USUARIOS = {
    "comum": {
        "email": "comum.teste@exemplo.com",
        "senha": SENHA_TESTE
    },
    "gestor": {
        "email": "gestor.teste@exemplo.com",
        "senha": SENHA_TESTE
    },
    "admin": {
        "email": "admin.teste@exemplo.com",
        "senha": SENHA_TESTE
    }
}

total_testes = 0
testes_aprovados = 0
testes_falharam = 0


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def registrar_resultado(descricao, esperado, resposta):
    global total_testes, testes_aprovados, testes_falharam

    total_testes += 1

    passou = resposta.status_code == esperado

    if passou:
        testes_aprovados += 1
        resultado = "PASSOU"
    else:
        testes_falharam += 1
        resultado = "FALHOU"

    print(f"\n[{resultado}] {descricao}")
    print(f"Esperado: HTTP {esperado}")
    print(f"Recebido: HTTP {resposta.status_code}")

    if not passou:
        print("Resposta da API:")
        print(resposta.text[:1000])

    return passou


def fazer_login(usuario):
    resposta = requests.post(
        f"{URL_BASE}/auth/login",
        json={
            "email": USUARIOS[usuario]["email"],
            "senha": USUARIOS[usuario]["senha"]
        },
        timeout=10
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha no login de {usuario}: "
            f"HTTP {resposta.status_code} - {resposta.text}"
        )

    token = resposta.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def obter_meu_usuario(headers):
    resposta = requests.get(
        f"{URL_BASE}/auth/me",
        headers=headers,
        timeout=10
    )

    resposta.raise_for_status()
    return resposta.json()


def obter_equipamentos(headers):
    resposta = requests.get(
        f"{URL_BASE}/equipamentos",
        headers=headers,
        timeout=10
    )

    resposta.raise_for_status()

    equipamentos = resposta.json()

    if not equipamentos:
        raise RuntimeError(
            "Não existem equipamentos cadastrados. "
            "Cadastre um equipamento antes de executar os testes."
        )

    return equipamentos


def resolver_referencia(schema, componentes):
    while "$ref" in schema:
        nome = schema["$ref"].split("/")[-1]
        schema = componentes[nome]

    return schema


def gerar_valor(campo, propriedade, equipamento_id, usuario_id):
    nome = campo.lower()
    tipo = propriedade.get("type")
    formato = propriedade.get("format")

    if nome in ("id_solicitante", "usuario_id"):
        return usuario_id

    if nome in ("id_equipamento", "equipamento_id"):
        return equipamento_id

    if nome in ("id_solicitacao", "solicitacao_id"):
        return None

    if "situacao" in nome or nome == "status":
        opcoes = propriedade.get("enum", [])

        if "pendente" in opcoes:
            return "pendente"

        if opcoes:
            return opcoes[0]

        return "pendente"

    if "data" in nome or formato in ("date", "date-time"):
        if formato == "date":
            return date.today().isoformat()

        if formato == "date-time":
            return datetime.now().isoformat(timespec="seconds")

        if "devolucao" in nome or "prevista" in nome:
            return (date.today() + timedelta(days=7)).isoformat()

        return date.today().isoformat()

    if tipo == "string":
        opcoes = propriedade.get("enum", [])

        if opcoes:
            return opcoes[0]

        if "motivo" in nome or "descricao" in nome:
            return "Solicitação de teste automatizado"

        if "hora" in nome:
            return "10:00:00"

        return "Teste automatizado"

    if tipo == "integer":
        if nome.startswith("id_") or nome.endswith("_id"):
            return equipamento_id

        return 1

    if tipo == "number":
        return 1.0

    if tipo == "boolean":
        return False

    if tipo == "array":
        return []

    if tipo == "object":
        return {}

    return None


def montar_payload_solicitacao(
    equipamento_id,
    usuario_id
):
    resposta = requests.get(
        f"{URL_BASE}/openapi.json",
        timeout=10
    )
    resposta.raise_for_status()

    documentacao = resposta.json()
    componentes = documentacao["components"]["schemas"]

    rota = documentacao["paths"]["/solicitacoes"]["post"]
    schema = rota["requestBody"]["content"]["application/json"]["schema"]

    schema = resolver_referencia(schema, componentes)

    propriedades = schema.get("properties", {})
    campos_obrigatorios = schema.get("required", [])

    payload = {}

    for campo in campos_obrigatorios:
        propriedade = resolver_referencia(
            propriedades[campo],
            componentes
        )

        valor = gerar_valor(
            campo,
            propriedade,
            equipamento_id,
            usuario_id
        )

        if valor is None:
            raise RuntimeError(
                f"Não foi possível gerar um valor para o campo "
                f"obrigatório '{campo}'. Confira o modelo Solicitacao."
            )

        payload[campo] = valor

    # Acrescenta campos conhecidos que sejam aceitos pela API.
    for campo in propriedades:
        if campo in payload:
            continue

        if campo == "id_solicitante":
            payload[campo] = usuario_id

        elif campo == "id_equipamento":
            payload[campo] = equipamento_id

        elif campo == "situacao":
            payload[campo] = "pendente"

    return payload


# ============================================================
# TESTES
# ============================================================

def executar_testes():
    print("=" * 60)
    print("TESTES AUTOMATIZADOS: SOLICITAÇÕES")
    print("=" * 60)

    print("\n1. Realizando login dos três usuários...")

    comum_headers = fazer_login("comum")
    gestor_headers = fazer_login("gestor")
    admin_headers = fazer_login("admin")

    comum = obter_meu_usuario(comum_headers)
    admin = obter_meu_usuario(admin_headers)

    print("Login dos três usuários realizado com sucesso.")

    print("\n2. Procurando equipamentos cadastrados...")

    equipamentos = obter_equipamentos(comum_headers)
    equipamento = equipamentos[0]

    equipamento_id = equipamento.get("id_equipamento")

    if equipamento_id is None:
        raise RuntimeError(
            "Não foi encontrado o campo id_equipamento "
            "no primeiro equipamento retornado pela API."
        )

    print(f"Equipamento escolhido para os testes: ID {equipamento_id}")

    print("\n3. Criando uma solicitação como usuário comum...")

    payload = montar_payload_solicitacao(
        equipamento_id,
        comum["id_usuario"]
    )

    resposta = requests.post(
        f"{URL_BASE}/solicitacoes",
        headers=comum_headers,
        json=payload,
        timeout=10
    )

    if not registrar_resultado(
        "Usuário comum consegue criar uma solicitação",
        200,
        resposta
    ):
        print("\nPayload enviado:")
        print(payload)
        print(
            "\nConfira os campos obrigatórios de Solicitacao "
            "se a API retornar erro 422."
        )
        return

    solicitacao_criada = resposta.json()
    solicitacao_id = solicitacao_criada.get("id_solicitacao")

    if solicitacao_id is None:
        print(
            "\nNão foi possível identificar id_solicitacao "
            "na resposta. Confira o modelo Solicitacao."
        )
        return

    print(f"Solicitação criada com ID {solicitacao_id}.")

    print("\n4. Testando a listagem das solicitações...")

    resposta = requests.get(
        f"{URL_BASE}/solicitacoes",
        headers=comum_headers,
        timeout=10
    )

    if registrar_resultado(
        "Usuário comum consegue listar suas solicitações",
        200,
        resposta
    ):
        lista = resposta.json()

        pertence_ao_usuario = all(
            item.get("id_solicitante") == comum["id_usuario"]
            for item in lista
        )

        registrar_resultado(
            "A listagem do usuário comum não contém solicitações alheias",
            200,
            type(
                "RespostaTeste",
                (),
                {
                    "status_code": (
                        200 if pertence_ao_usuario else 500
                    ),
                    "text": (
                        "Todos os registros pertencem ao usuário."
                        if pertence_ao_usuario
                        else "A listagem contém solicitações de terceiros."
                    )
                }
            )()
        )

    print("\n5. Testando o acesso a uma solicitação de outro usuário...")

    resposta = requests.get(
        f"{URL_BASE}/solicitacoes/{solicitacao_id}",
        headers=admin_headers,
        timeout=10
    )

    registrar_resultado(
        "Administrador não consegue consultar solicitação alheia",
        403,
        resposta
    )

    print("\n6. Verificando se o administrador vê apenas as próprias...")

    resposta = requests.get(
        f"{URL_BASE}/solicitacoes",
        headers=admin_headers,
        timeout=10
    )

    if registrar_resultado(
        "Administrador consegue consultar sua listagem",
        200,
        resposta
    ):
        lista = resposta.json()

        apenas_proprias = all(
            item.get("id_solicitante") == admin["id_usuario"]
            for item in lista
        )

        registrar_resultado(
            "Listagem do administrador não contém solicitações alheias",
            200,
            type(
                "RespostaTeste",
                (),
                {
                    "status_code": 200 if apenas_proprias else 500,
                    "text": (
                        "Nenhuma solicitação alheia encontrada."
                        if apenas_proprias
                        else "Foram encontradas solicitações alheias."
                    )
                }
            )()
        )

    print("\n7. Verificando o acesso do Gestor...")

    resposta = requests.get(
        f"{URL_BASE}/solicitacoes",
        headers=gestor_headers,
        timeout=10
    )

    if registrar_resultado(
        "Gestor consegue consultar todas as solicitações",
        200,
        resposta
    ):
        lista = resposta.json()

        encontrou_solicitacao = any(
            item.get("id_solicitacao") == solicitacao_id
            for item in lista
        )

        registrar_resultado(
            "Gestor consegue visualizar a solicitação criada",
            200,
            type(
                "RespostaTeste",
                (),
                {
                    "status_code": 200 if encontrou_solicitacao else 500,
                    "text": (
                        "Solicitação encontrada."
                        if encontrou_solicitacao
                        else "Solicitação não encontrada na listagem."
                    )
                }
            )()
        )

    print("\n8. Verificando permissões de criação...")

    resposta = requests.post(
        f"{URL_BASE}/solicitacoes",
        headers=gestor_headers,
        json=payload,
        timeout=10
    )

    registrar_resultado(
        "Gestor não pode criar solicitação",
        403,
        resposta
    )

    resposta = requests.post(
        f"{URL_BASE}/solicitacoes",
        headers=admin_headers,
        json=payload,
        timeout=10
    )

    registrar_resultado(
        "Administrador não pode criar solicitação",
        403,
        resposta
    )

    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    print(f"Total executado: {total_testes}")
    print(f"Passaram: {testes_aprovados}")
    print(f"Falharam: {testes_falharam}")

    if testes_falharam == 0:
        print("\nTodos os testes passaram!")
    else:
        print("\nConfira os erros acima antes de continuar.")


if __name__ == "__main__":
    try:
        executar_testes()

    except requests.RequestException as erro:
        print("\nERRO DE CONEXÃO COM A API:")
        print(erro)
        print("Verifique se o servidor FastAPI está rodando.")

    except Exception as erro:
        print("\nERRO DURANTE OS TESTES:")
        print(f"{type(erro).__name__}: {erro}")