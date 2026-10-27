
import requests
from datetime import datetime, timedelta

URL = "http://127.0.0.1:8000"
SENHA = "Teste123!"

USUARIOS = {
    "comum": "comum.teste@exemplo.com",
    "gestor": "gestor.teste@exemplo.com",
    "admin": "admin.teste@exemplo.com",
}

total = 0
falhas = 0


def testar(nome, resposta, esperado):
    global total, falhas
    total += 1

    passou = resposta.status_code == esperado

    print(f"\n[{'PASSOU' if passou else 'FALHOU'}] {nome}")
    print(f"Esperado: {esperado} | Recebido: {resposta.status_code}")

    if not passou:
        falhas += 1
        print(resposta.text[:1000])

    return passou


def testar_condicao(nome, condicao, detalhe=""):
    global total, falhas
    total += 1

    print(f"\n[{'PASSOU' if condicao else 'FALHOU'}] {nome}")

    if not condicao:
        falhas += 1
        print(detalhe or "A condição não foi atendida.")

    return condicao


def login(perfil):
    resposta = requests.post(
        f"{URL}/auth/login",
        json={
            "email": USUARIOS[perfil],
            "senha": SENHA,
        },
        timeout=10,
    )
    resposta.raise_for_status()

    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def executar():
    print("=" * 60)
    print("TESTES AUTOMATIZADOS: EMPRÉSTIMOS")
    print("=" * 60)

    comum = login("comum")
    gestor = login("gestor")
    admin = login("admin")

    print("\n1. Procurando equipamento disponível...")

    resposta = requests.get(
        f"{URL}/equipamentos",
        headers=comum,
        timeout=10,
    )
    resposta.raise_for_status()

    equipamentos = resposta.json()
    disponiveis = [
        e for e in equipamentos
        if e.get("status_equipamento") == "disponivel"
    ]

    if not disponiveis:
        raise RuntimeError(
            "Não há equipamentos disponíveis. "
            "Cadastre ou libere um equipamento antes do teste."
        )

    equipamento = disponiveis[0]
    equipamento_id = equipamento["id_equipamento"]

    resposta = requests.get(
        f"{URL}/auth/me",
        headers=comum,
        timeout=10,
    )
    resposta.raise_for_status()
    id_comum = resposta.json()["id_usuario"]

    resposta = requests.get(
        f"{URL}/auth/me",
        headers=gestor,
        timeout=10,
    )
    resposta.raise_for_status()
    id_gestor = resposta.json()["id_usuario"]

    agora = datetime.now().replace(microsecond=0)
    retirada = agora.isoformat()
    devolucao_prevista = (agora + timedelta(days=7)).isoformat()

    print(f"Equipamento escolhido: {equipamento_id}")

    print("\n2. Criando uma solicitação de teste...")

    payload_solicitacao = {
        "id_equipamento": equipamento_id,
        "id_solicitante": id_comum,
        "data_retirada_solicitada": retirada,
        "data_prevista_devolucao": devolucao_prevista,
        "situacao": "pendente",
        "observacoes_solicitante": "Teste automatizado de empréstimo",
    }

    resposta = requests.post(
        f"{URL}/solicitacoes",
        headers=comum,
        json=payload_solicitacao,
        timeout=10,
    )

    if not testar("Usuário comum cria solicitação", resposta, 200):
        raise RuntimeError("Não foi possível criar a solicitação de teste.")

    solicitacao = resposta.json()
    solicitacao_id = solicitacao["id_solicitacao"]

    print(f"Solicitação criada: {solicitacao_id}")

    print("\n3. Verificando bloqueios de acesso...")

    resposta = requests.get(
        f"{URL}/emprestimos",
        headers=comum,
        timeout=10,
    )
    testar("Usuário comum não lista empréstimos", resposta, 403)

    resposta = requests.get(
        f"{URL}/emprestimos",
        headers=admin,
        timeout=10,
    )
    testar("Administrador não lista empréstimos", resposta, 403)

    resposta = requests.put(
        f"{URL}/solicitacoes/{solicitacao_id}",
        headers=comum,
        json=payload_solicitacao,
        timeout=10,
    )
    testar("Usuário comum não aprova solicitação", resposta, 403)

    print("\n4. Aprovando a solicitação como Gestor...")

    payload_aprovacao = {
        **payload_solicitacao,
        "id_usuario_autorizador": id_gestor,
        "data_autorizacao": agora.isoformat(),
        "situacao": "aprovado",
        "observacoes_autorizador": "Aprovado no teste automatizado",
    }

    resposta = requests.put(
        f"{URL}/solicitacoes/{solicitacao_id}",
        headers=gestor,
        json=payload_aprovacao,
        timeout=10,
    )

    if not testar("Gestor aprova solicitação", resposta, 200):
        raise RuntimeError("A aprovação falhou. Confira o erro acima.")

    print("\n5. Criando o empréstimo como Gestor...")

    payload_emprestimo = {
        "id_usuario": id_comum,
        "id_solicitacao": solicitacao_id,
        "id_equipamento": equipamento_id,
        "data_prevista_devolucao": devolucao_prevista,
        "data_devolucao": None,
        "observacoes": "Empréstimo de teste automatizado",
    }

    resposta = requests.post(
        f"{URL}/emprestimos",
        headers=gestor,
        json=payload_emprestimo,
        timeout=10,
    )

    if not testar("Gestor registra empréstimo aprovado", resposta, 200):
        raise RuntimeError("O empréstimo falhou. Confira o erro acima.")

    emprestimo_id = resposta.json()["id_emprestimo"]
    print(f"Empréstimo criado: {emprestimo_id}")

    print("\n6. Verificando o empréstimo e o equipamento...")

    resposta = requests.get(
        f"{URL}/emprestimos",
        headers=gestor,
        timeout=10,
    )

    if testar("Gestor lista empréstimos", resposta, 200):
        ids = [e["id_emprestimo"] for e in resposta.json()]
        testar_condicao(
            "Empréstimo criado aparece na listagem",
            emprestimo_id in ids,
        )

    resposta = requests.get(
        f"{URL}/equipamentos/{equipamento_id}",
        headers=comum,
        timeout=10,
    )

    if testar("Usuário consulta equipamento", resposta, 200):
        testar_condicao(
            "Equipamento fica emprestado após o cadastro",
            resposta.json()["status_equipamento"] == "emprestado",
        )

    print("\n7. Testando bloqueios de atualização...")

    payload_devolucao = {
        **payload_emprestimo,
        "data_devolucao": agora.isoformat(),
    }

    resposta = requests.put(
        f"{URL}/emprestimos/{emprestimo_id}",
        headers=comum,
        json=payload_devolucao,
        timeout=10,
    )
    testar("Usuário comum não registra devolução", resposta, 403)

    resposta = requests.put(
        f"{URL}/emprestimos/{emprestimo_id}",
        headers=admin,
        json=payload_devolucao,
        timeout=10,
    )
    testar("Administrador não registra devolução", resposta, 403)

    print("\n8. Registrando devolução como Gestor...")

    resposta = requests.put(
        f"{URL}/emprestimos/{emprestimo_id}",
        headers=gestor,
        json=payload_devolucao,
        timeout=10,
    )

    if not testar("Gestor registra devolução", resposta, 200):
        raise RuntimeError("A devolução falhou. Confira o erro acima.")

    testar_condicao(
        "Devolução ficou registrada",
        resposta.json().get("data_devolucao") is not None,
    )

    resposta = requests.get(
        f"{URL}/equipamentos/{equipamento_id}",
        headers=comum,
        timeout=10,
    )

    if testar("Usuário consulta equipamento após devolução", resposta, 200):
        testar_condicao(
            "Equipamento volta a ficar disponível",
            resposta.json()["status_equipamento"] == "disponivel",
        )

    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Total: {total}")
    print(f"Passaram: {total - falhas}")
    print(f"Falharam: {falhas}")


if __name__ == "__main__":
    try:
        executar()
    except requests.RequestException as erro:
        print("\nERRO DE COMUNICAÇÃO COM A API:")
        print(erro)
    except Exception as erro:
        print(f"\nTESTE INTERROMPIDO: {type(erro).__name__}: {erro}")
