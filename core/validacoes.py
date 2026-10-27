"""Validações compartilhadas pelo sistema (todas as mensagens em português).

Cada função devolve o valor já limpo/padronizado ou levanta ValueError
com uma mensagem que pode ser mostrada diretamente ao usuário.
"""
import re

# Formato: texto@dominio.extensao (sem espaços, sem pontos seguidos)
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._%+\-]*[A-Za-z0-9])?"
    r"@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)*"
    r"\.[A-Za-z]{2,}$"
)


def validar_email(valor: str) -> str:
    """Valida o formato de um e-mail e devolve em minúsculas."""
    email = (valor or "").strip().lower()

    if not email:
        raise ValueError("Informe o e-mail.")

    if len(email) > 150:
        raise ValueError("O e-mail pode ter no máximo 150 caracteres.")

    if ".." in email or not _EMAIL_RE.match(email):
        raise ValueError(
            "Informe um e-mail válido, por exemplo: nome@empresa.com."
        )

    return email


def validar_email_login(valor: str) -> str:
    """Checagem mais branda para o login (não bloqueia contas antigas)."""
    email = (valor or "").strip().lower()

    if not email:
        raise ValueError("Informe o e-mail.")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError(
            "Informe um e-mail válido, por exemplo: nome@empresa.com."
        )

    return email


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def formatar_cpf(digitos: str) -> str:
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def cpf_e_valido(digitos: str) -> bool:
    """Confere tamanho, sequências repetidas e os 2 dígitos verificadores."""
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    for tamanho in (9, 10):
        soma = sum(
            int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho)
        )
        digito = (soma * 10) % 11 % 10

        if digito != int(digitos[tamanho]):
            return False

    return True


def validar_cpf(valor: str) -> str:
    """Valida o CPF e devolve no padrão 000.000.000-00."""
    digitos = somente_digitos(valor)

    if not digitos:
        raise ValueError("Informe o CPF.")

    if len(digitos) != 11:
        raise ValueError("O CPF deve ter 11 números.")

    if not cpf_e_valido(digitos):
        raise ValueError(
            "CPF inválido. Confira os números digitados."
        )

    return formatar_cpf(digitos)


def validar_texto(
    valor,
    rotulo: str,
    minimo: int = 1,
    maximo: int = 100,
    obrigatorio: bool = True,
):
    """Remove espaços das pontas e confere o tamanho do texto."""
    texto = (valor or "").strip() if isinstance(valor, str) or valor is None else str(valor).strip()
    texto = re.sub(r"\s+", " ", texto)

    if not texto:
        if obrigatorio:
            raise ValueError(f"Informe {rotulo}.")
        return None

    if len(texto) < minimo:
        raise ValueError(
            f"{rotulo[0].upper() + rotulo[1:]} deve ter pelo menos "
            f"{minimo} caracteres."
        )

    if len(texto) > maximo:
        raise ValueError(
            f"{rotulo[0].upper() + rotulo[1:]} pode ter no máximo "
            f"{maximo} caracteres."
        )

    return texto
