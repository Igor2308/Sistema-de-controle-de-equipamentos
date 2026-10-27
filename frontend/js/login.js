/* Tela de login e criação de conta */
(function () {
  const A = window.App;

  const painelEntrar = document.getElementById("painel-entrar");
  const painelCriar = document.getElementById("painel-criar");
  const formLogin = document.getElementById("form-login");
  const formCriar = document.getElementById("form-criar");
  const msgLogin = document.getElementById("msg-login");
  const msgCriar = document.getElementById("msg-criar");
  const msgSucesso = document.getElementById("msg-sucesso");
  const avisoMotivo = document.getElementById("aviso-motivo");

  const MOTIVOS = {
    sessao: "Entre para continuar.",
    expirada: "Sua sessão expirou. Entre novamente.",
    perfil: "Seu perfil de acesso não tem uma tela disponível."
  };

  function mostrarErro(el, texto) { el.textContent = texto; el.hidden = false; }
  function limparErro(el) { el.hidden = true; el.textContent = ""; }

  function alternar(criar) {
    painelEntrar.hidden = criar;
    painelCriar.hidden = !criar;
    limparErro(msgLogin); limparErro(msgCriar);
    document.querySelectorAll(".campo__msg").forEach(function (m) { m.remove(); });
    document.querySelectorAll("[aria-invalid]").forEach(function (c) { c.removeAttribute("aria-invalid"); });
    (criar ? document.getElementById("criar-nome") : document.getElementById("login-email")).focus();
  }
  document.getElementById("ir-criar").addEventListener("click", function () { alternar(true); });
  document.getElementById("ir-entrar").addEventListener("click", function () { alternar(false); });

  // Máscara 000.000.000-00
  A.mascaraCpf(document.getElementById("criar-cpf"));

  // ---------- Validações campo a campo ----------
  const campoLoginEmail = document.getElementById("login-email");
  const campoLoginSenha = document.getElementById("login-senha");
  const campoNome = document.getElementById("criar-nome");
  const campoEmail = document.getElementById("criar-email");
  const campoCpf = document.getElementById("criar-cpf");
  const campoSenha = document.getElementById("criar-senha");
  const campoSenha2 = document.getElementById("criar-senha2");

  // No login a checagem é só de formato (contas antigas continuam entrando)
  function erroEmailLogin(v) {
    v = String(v || "").trim();
    if (!v) return "Informe o e-mail.";
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? "" : "Informe um e-mail válido, por exemplo: nome@empresa.com.";
  }
  function erroSenhaLogin(v) { return v ? "" : "Informe a senha."; }
  function erroNome(v) {
    v = String(v || "").trim();
    if (!v) return "Informe o nome completo.";
    return v.length < 3 ? "O nome deve ter pelo menos 3 caracteres." : "";
  }
  function erroSenhaNova(v) { return !v ? "Crie uma senha." : (v.length < 8 ? "A senha deve ter pelo menos 8 caracteres." : ""); }
  function erroSenha2(v) {
    if (!v) return "Repita a senha para confirmar.";
    return v !== campoSenha.value ? "As senhas não conferem." : "";
  }

  // Valida ao sair do campo e refaz a checagem enquanto digita (só se já houver erro)
  function vigiar(campo, funcaoErro) {
    campo.addEventListener("blur", function () { A.validarCampo(campo, funcaoErro); });
    campo.addEventListener("input", function () {
      if (campo.getAttribute("aria-invalid") === "true") A.validarCampo(campo, funcaoErro);
    });
  }
  vigiar(campoLoginEmail, erroEmailLogin);
  vigiar(campoLoginSenha, erroSenhaLogin);
  vigiar(campoNome, erroNome);
  vigiar(campoEmail, A.erroEmail);
  vigiar(campoCpf, A.erroCpf);
  vigiar(campoSenha, erroSenhaNova);
  vigiar(campoSenha2, erroSenha2);

  // Se já existe sessão válida, vai direto para o painel do perfil
  async function aproveitarSessao() {
    if (!A.Sessao.token()) return;
    try {
      const usuario = await A.api("/auth/me");
      A.irParaTelaDoPerfil(usuario.roles);
    } catch (e) { /* token inválido: api() já limpou a sessão */ }
  }

  formLogin.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    limparErro(msgLogin);
    const email = campoLoginEmail.value.trim();
    const senha = campoLoginSenha.value;
    const okEmail = A.validarCampo(campoLoginEmail, erroEmailLogin);
    const okSenha = A.validarCampo(campoLoginSenha, erroSenhaLogin);
    if (!okEmail || !okSenha) { (okEmail ? campoLoginSenha : campoLoginEmail).focus(); return; }

    const botao = document.getElementById("btn-entrar");
    botao.disabled = true; botao.textContent = "Entrando...";
    try {
      const resp = await A.api("/auth/login", { metodo: "POST", corpo: { email: email, senha: senha }, semAuth: true });
      A.Sessao.salvar(resp.access_token);
      const usuario = await A.api("/auth/me");
      document.getElementById("login-senha").value = "";
      A.irParaTelaDoPerfil(usuario.roles);
    } catch (e) {
      mostrarErro(msgLogin, e.message);
      botao.disabled = false; botao.textContent = "Entrar";
    }
  });

  formCriar.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    limparErro(msgCriar);
    const nome = campoNome.value.trim();
    const email = campoEmail.value.trim();
    const cpf = campoCpf.value.trim();
    const senha = campoSenha.value;

    // Valida todos os campos de uma vez e leva o foco ao primeiro com problema
    const verificacoes = [
      [campoNome, erroNome], [campoEmail, A.erroEmail], [campoCpf, A.erroCpf],
      [campoSenha, erroSenhaNova], [campoSenha2, erroSenha2]
    ].map(function (v) { return [v[0], A.validarCampo(v[0], v[1])]; });
    const primeiro = verificacoes.filter(function (v) { return !v[1]; })[0];
    if (primeiro) { primeiro[0].focus(); return; }

    const botao = document.getElementById("btn-criar");
    botao.disabled = true; botao.textContent = "Criando...";
    try {
      // O backend sempre cria a conta como usuário comum
      await A.api("/usuarios", {
        metodo: "POST", semAuth: true,
        corpo: { nome: nome, email: email, cpf: cpf, senha: senha, nivel_acesso: 1 }
      });
      formCriar.reset();
      alternar(false);
      msgSucesso.textContent = "Conta criada. Entre com seu e-mail e senha.";
      msgSucesso.hidden = false;
      document.getElementById("login-email").value = email;
    } catch (e) {
      mostrarErro(msgCriar, e.message);
    } finally {
      botao.disabled = false; botao.textContent = "Criar conta";
    }
  });

  const motivo = new URLSearchParams(location.search).get("motivo");
  if (motivo && MOTIVOS[motivo]) { avisoMotivo.textContent = MOTIVOS[motivo]; avisoMotivo.hidden = false; }
  aproveitarSessao();
})();
