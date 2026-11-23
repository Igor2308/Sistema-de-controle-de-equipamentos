const botao = document.getElementById("buscar_usuarios");

const tabela = document.getElementById("lista_usuarios");

botao.addEventListener("click", () => {

    fetch("http://127.0.0.1:8000/usuarios")

        .then(function(response) {

            if (!response.ok) {
                throw new Error("Erro ao buscar usuários");
            }

            return response.json();

        })

        .then(function(usuarios) {

            tabela.innerHTML = "";

            usuarios.forEach(function(usuario) {

                const linha = document.createElement("tr");

                function adicionarCelula(valor) {
                    const coluna = document.createElement("td");
                    coluna.textContent = valor ?? "";
                    linha.appendChild(coluna);
                }

                adicionarCelula(usuario.id_usuario);
                adicionarCelula(usuario.nome);
                adicionarCelula(usuario.email);
                adicionarCelula(usuario.cpf);
                adicionarCelula(usuario.nivel_acesso);
                adicionarCelula(usuario.status_usuario);
                adicionarCelula(usuario.data_criacao);

                tabela.appendChild(linha);

            });

        })

        .catch(function(erro) {

            console.log("Erro:", erro);

        });

});

.then(function(lista) {
    lista.forEach(function(usuario) {
        const linha = document.createElement("tr");

        function adicionarColuna(teste) {
            const coluna = document.createElement("td");
            coluna.textContent = teste ?? ""; 
            linha.appendChild(coluna);
        }

        adicionarColuna(usuario.nome);

        tabela.appendChild(linha);
    });


/*
O forEach() pega um usuário.
createElement("tr") cria uma linha nova.
adicionarColuna(usuario.nome) cria uma célula com o nome.
adicionarColuna(usuario.email) cria outra célula com o e-mail.
adicionarColuna(usuario.cpf) cria outra célula com o CPF.
tabela.appendChild(linha) coloca a linha completa dentro da tabela.
*/