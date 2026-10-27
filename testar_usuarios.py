
import time
import requests


BASE_URL = "http://127.0.0.1:8000"

SENHA_PADRAO = "Teste123!"

EMAIL_ADMIN = "admin.teste@exemplo.com"
EMAIL_COMUM = "comum.teste@exemplo.com"

resultados = []


def gerar_cpf_valido(semente):
    """Gera um CPF com dígitos verificadores corretos (o sistema valida o CPF)."""
    base = [int(c) for c in str(10**8 + int(semente) % (9 * 10**8))[:9]]

    if len(set(base)) == 1:
        base[-1] = (base[-1] + 1) % 10

    for tamanho in (9, 10):
        soma = sum(base[i] * (tamanho + 1 - i) for i in range(tamanho))
        base.append((soma * 10) % 11 % 10)

    return "".join(str(d) for d in base)



def verificar(nome, condicao, detalhe=""):
    status = "PASSOU" if condicao else "FALHOU"
    resultados.append(condicao)

    print(f"[{status}] {nome}")

    if not condicao and detalhe:
        print(f"         Detalhe: {detalhe}")


def fazer_login(email, senha):
    return requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": email,
            "senha": senha
        },
        timeout=10
    )


def executar_testes():
    print("\n===== TESTES DE USUÁRIOS E SEGURANÇA =====\n")

    # 1. Login administrativo
    resposta_admin = fazer_login(
        EMAIL_ADMIN,
        SENHA_PADRAO
    )

    verificar(
        "Login de administrador",
        resposta_admin.status_code == 200,
        resposta_admin.text
    )

    if resposta_admin.status_code != 200:
        print("\nNão foi possível continuar sem o administrador.")
        return

    token_admin = resposta_admin.json()["access_token"]

    headers_admin = {
        "Authorization": f"Bearer {token_admin}"
    }

    # 2. Login de usuário comum
    resposta_comum = fazer_login(
        EMAIL_COMUM,
        SENHA_PADRAO
    )

    verificar(
        "Login de usuário comum",
        resposta_comum.status_code == 200,
        resposta_comum.text
    )

    token_comum = None

    if resposta_comum.status_code == 200:
        token_comum = resposta_comum.json()["access_token"]

    # 3. Criar um usuário de teste único
    identificador = str(time.time_ns())

    email_teste = f"teste.{identificador}@exemplo.com"
    cpf_teste = gerar_cpf_valido(int(identificador[-10:]))

    senha_teste = "SenhaTeste123!"

    usuario_teste = {
        "nome": "Usuario Teste Automatizado",
        "email": email_teste,
        "cpf": cpf_teste,
        "senha": senha_teste,
        "nivel_acesso": 3,
        "status_usuario": "ativo"
    }

    resposta_cadastro = requests.post(
        f"{BASE_URL}/usuarios",
        json=usuario_teste,
        timeout=10
    )

    verificar(
        "Cadastro público de usuário",
        resposta_cadastro.status_code == 201,
        resposta_cadastro.text
    )

    if resposta_cadastro.status_code != 201:
        print("\nNão foi possível continuar sem criar o usuário de teste.")
        return

    usuario_criado = resposta_cadastro.json()
    id_teste = usuario_criado["id_usuario"]

    verificar(
        "Resposta não expõe a senha",
        "senha" not in usuario_criado,
        str(usuario_criado)
    )

    verificar(
        "Cadastro público não concede privilégio administrativo",
        usuario_criado["nivel_acesso"] == 1,
        str(usuario_criado.get("nivel_acesso"))
    )

    # 4. Verificar que a senha cadastrada permite login
    resposta_login_teste = fazer_login(
        email_teste,
        senha_teste
    )

    verificar(
        "Login funciona com a senha cadastrada",
        resposta_login_teste.status_code == 200,
        resposta_login_teste.text
    )

    # 5. Senha incorreta
    resposta_senha_errada = fazer_login(
        email_teste,
        "SenhaIncorreta123!"
    )

    verificar(
        "Senha incorreta retorna 401",
        resposta_senha_errada.status_code == 401,
        resposta_senha_errada.text
    )

    # 6. Acesso à lista sem token
    resposta_sem_token = requests.get(
        f"{BASE_URL}/usuarios",
        timeout=10
    )

    verificar(
        "Lista de usuários bloqueada sem token",
        resposta_sem_token.status_code in (401, 403),
        resposta_sem_token.text
    )

    # 7. Acesso com token inválido
    resposta_token_invalido = requests.get(
        f"{BASE_URL}/usuarios",
        headers={
            "Authorization": "Bearer token-invalido"
        },
        timeout=10
    )

    verificar(
        "Token inválido é rejeitado",
        resposta_token_invalido.status_code == 401,
        resposta_token_invalido.text
    )

    # 8. Usuário comum não pode listar usuários
    if token_comum:
        resposta_permissao = requests.get(
            f"{BASE_URL}/usuarios",
            headers={
                "Authorization": f"Bearer {token_comum}"
            },
            timeout=10
        )

        verificar(
            "Usuário comum recebe 403 ao listar usuários",
            resposta_permissao.status_code == 403,
            resposta_permissao.text
        )
    else:
        verificar(
            "Usuário comum recebe 403 ao listar usuários",
            False,
            "Não foi possível autenticar o usuário comum."
        )

    # 9. Administrador pode listar usuários
    resposta_lista_admin = requests.get(
        f"{BASE_URL}/usuarios",
        headers=headers_admin,
        timeout=10
    )

    verificar(
        "Administrador pode listar usuários",
        resposta_lista_admin.status_code == 200,
        resposta_lista_admin.text
    )

    # 10. Buscar ID inexistente
    resposta_inexistente = requests.get(
        f"{BASE_URL}/usuarios/999999999",
        headers=headers_admin,
        timeout=10
    )

    verificar(
        "Usuário inexistente retorna 404",
        resposta_inexistente.status_code == 404,
        resposta_inexistente.text
    )

    # 11. E-mail duplicado
    cadastro_email_duplicado = {
        **usuario_teste,
        "cpf": gerar_cpf_valido(int(identificador[-10:]) + 1)
    }

    resposta_email_duplicado = requests.post(
        f"{BASE_URL}/usuarios",
        json=cadastro_email_duplicado,
        timeout=10
    )

    verificar(
        "E-mail duplicado retorna 400",
        resposta_email_duplicado.status_code == 400,
        resposta_email_duplicado.text
    )

    # 12. CPF duplicado
    cadastro_cpf_duplicado = {
        **usuario_teste,
        "email": f"outro.{identificador}@exemplo.com"
    }

    resposta_cpf_duplicado = requests.post(
        f"{BASE_URL}/usuarios",
        json=cadastro_cpf_duplicado,
        timeout=10
    )

    verificar(
        "CPF duplicado retorna 400",
        resposta_cpf_duplicado.status_code == 400,
        resposta_cpf_duplicado.text
    )

    # 13. Atualizar senha do usuário de teste
    senha_nova = "SenhaAtualizada456!"

    dados_atualizados = {
        **usuario_teste,
        "senha": senha_nova,
        "nivel_acesso": 1
    }

    resposta_atualizacao = requests.put(
        f"{BASE_URL}/usuarios/{id_teste}",
        headers=headers_admin,
        json=dados_atualizados,
        timeout=10
    )

    verificar(
        "Administrador atualiza usuário",
        resposta_atualizacao.status_code == 200,
        resposta_atualizacao.text
    )

    if resposta_atualizacao.status_code == 200:
        login_senha_nova = fazer_login(
            email_teste,
            senha_nova
        )

        verificar(
            "Senha atualizada permite login",
            login_senha_nova.status_code == 200,
            login_senha_nova.text
        )

        login_senha_antiga = fazer_login(
            email_teste,
            senha_teste
        )

        verificar(
            "Senha antiga deixa de funcionar",
            login_senha_antiga.status_code == 401,
            login_senha_antiga.text
        )

    # 14. Excluir somente o usuário criado pelo teste
    resposta_exclusao = requests.delete(
        f"{BASE_URL}/usuarios/{id_teste}",
        headers=headers_admin,
        timeout=10
    )

    verificar(
        "Administrador exclui usuário de teste",
        resposta_exclusao.status_code == 200,
        resposta_exclusao.text
    )

    # 15. Confirmar que o usuário foi excluído
    resposta_pos_exclusao = requests.get(
        f"{BASE_URL}/usuarios/{id_teste}",
        headers=headers_admin,
        timeout=10
    )

    verificar(
        "Usuário excluído retorna 404",
        resposta_pos_exclusao.status_code == 404,
        resposta_pos_exclusao.text
    )

    total = len(resultados)
    aprovados = sum(resultados)
    falharam = total - aprovados

    print("\n===== RESUMO =====")
    print(f"Total: {total}")
    print(f"Passaram: {aprovados}")
    print(f"Falharam: {falharam}")

    if falharam:
        print("\nExistem cenários que precisam ser investigados.")
    else:
        print("\nTodos os cenários executados passaram!")


if __name__ == "__main__":
    executar_testes()
