/* ===== Funções compartilhadas pelas telas (sessão, API, utilitários) ===== */
(function () {
  const CHAVE_TOKEN = "token_acesso";
  const BASE_TELAS = "/frontend/telas/";

  // Nomes dos perfis exatamente como o backend devolve em /auth/me
  const TELA_POR_PERFIL = {
    "Usuário comum": "dashboard_usuario.html",
    "Gestor": "dashboard_gestor.html",
    "Administrador": "dashboard_administrador.html"
  };

  // ---------- Sessão (token JWT guardado só nesta aba) ----------
  const Sessao = {
    token() {
      try { return sessionStorage.getItem(CHAVE_TOKEN); } catch (e) { return null; }
    },
    salvar(token) { sessionStorage.setItem(CHAVE_TOKEN, token); },
    limpar() { try { sessionStorage.removeItem(CHAVE_TOKEN); } catch (e) { /* ignora */ } }
  };

  function irParaLogin(motivo) {
    Sessao.limpar();
    location.replace(BASE_TELAS + "login.html" + (motivo ? "?motivo=" + motivo : ""));
  }

  function irParaTelaDoPerfil(perfis) {
    const tela = TELA_POR_PERFIL[(perfis || [])[0]];
    if (tela) location.replace(BASE_TELAS + tela);
    else irParaLogin("perfil");
  }

  // ---------- Chamadas à API ----------
  function extrairErro(dados, status) {
    if (dados && typeof dados === "object" && dados.detail !== undefined) {
      if (typeof dados.detail === "string") return dados.detail;
      if (Array.isArray(dados.detail)) {
        return dados.detail.map(function (d) {
          const campo = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
          return (campo ? campo + ": " : "") + d.msg;
        }).join("; ");
      }
    }
    return "Erro inesperado (código " + status + ").";
  }

  async function api(caminho, opcoes) {
    const o = opcoes || {};
    const cabecalhos = { "Content-Type": "application/json" };

    if (!o.semAuth) {
      const token = Sessao.token();
      if (!token) { irParaLogin("sessao"); throw new Error("Sessão ausente."); }
      cabecalhos.Authorization = "Bearer " + token;
    }

    let resposta;
    try {
      resposta = await fetch(caminho, {
        method: o.metodo || "GET",
        headers: cabecalhos,
        body: o.corpo !== undefined ? JSON.stringify(o.corpo) : undefined
      });
    } catch (e) {
      throw new Error("Não foi possível conectar ao servidor.");
    }

    const texto = await resposta.text();
    let dados = null;
    if (texto) { try { dados = JSON.parse(texto); } catch (e) { dados = texto; } }

    if (resposta.status === 401 && !o.semAuth) {
      irParaLogin("expirada");
      throw new Error("Sessão expirada.");
    }
    if (!resposta.ok) throw new Error(extrairErro(dados, resposta.status));
    return dados;
  }

  // Confere sessão e perfil antes de mostrar a página protegida.
  // O backend continua validando cada requisição; isto só evita mostrar a tela errada.
  async function exigirPerfil(perfil) {
    let usuario;
    try {
      usuario = await api("/auth/me");
    } catch (e) {
      // Sem sessão ou token vencido: api() já está redirecionando para o login
      if (!Sessao.token()) return new Promise(function () { /* aguarda o redirecionamento */ });
      // Falha de rede ou do servidor: não mostra a tela sem validar o usuário
      document.body.classList.remove("protegido");
      document.body.innerHTML = '<main class="falha-sessao"><h1>Não foi possível abrir o painel</h1><p></p>' +
        '<a class="botao botao--primario" href="">Tentar novamente</a></main>';
      document.querySelector(".falha-sessao p").textContent = e.message;
      return new Promise(function () { /* interrompe */ });
    }
    const perfis = usuario.roles || [];
    if (perfis.indexOf(perfil) === -1) {
      irParaTelaDoPerfil(perfis);
      return new Promise(function () { /* interrompe: a página será trocada */ });
    }
    document.body.classList.remove("protegido");
    const rotulo = document.getElementById("usuario-nome");
    if (rotulo) rotulo.textContent = usuario.nome;
    saudar(usuario);
    return usuario;
  }

  // "Bom dia, Igor" e a data de hoje no topo de cada painel
  function saudar(usuario) {
    const texto = document.getElementById("saudacao");
    const data = document.getElementById("saudacao-data");
    const agora = new Date();
    const hora = agora.getHours();
    const periodo = hora < 12 ? "Bom dia" : (hora < 18 ? "Boa tarde" : "Boa noite");
    const primeiroNome = String(usuario.nome || "").trim().split(/\s+/)[0];
    if (texto) texto.textContent = periodo + (primeiroNome ? ", " + primeiroNome : "");
    if (data) {
      const t = agora.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
      data.textContent = t.charAt(0).toUpperCase() + t.slice(1);
    }
  }

  async function sair() {
    const token = Sessao.token();
    try {
      await fetch("/auth/logout", { method: "POST", headers: token ? { Authorization: "Bearer " + token } : {} });
    } catch (e) { /* o logout é só do lado do cliente */ }
    irParaLogin();
  }

  // ---------- Navegação entre seções da mesma página (#hash) ----------
  function iniciarNavegacao(padrao) {
    const links = Array.prototype.slice.call(document.querySelectorAll("[data-secao-link]"));
    const secoes = Array.prototype.slice.call(document.querySelectorAll("[data-secao]"));
    function mostrar() {
      let id = location.hash.slice(1);
      if (!secoes.some(function (s) { return s.dataset.secao === id; })) id = padrao;
      secoes.forEach(function (s) { s.hidden = s.dataset.secao !== id; });
      links.forEach(function (l) {
        const ativo = l.dataset.secaoLink === id;
        l.classList.toggle("ativo", ativo);
        if (ativo) l.setAttribute("aria-current", "page"); else l.removeAttribute("aria-current");
      });
      window.scrollTo(0, 0);
    }
    window.addEventListener("hashchange", mostrar);
    mostrar();
  }

  // ---------- Utilitários de texto e datas ----------
  function esc(valor) {
    return String(valor === null || valor === undefined ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function formatarData(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    return isNaN(d) ? "-" : d.toLocaleDateString("pt-BR");
  }

  // Data com hora e minutos: 24/10/2026 14:35
  function formatarDataHora(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    if (isNaN(d)) return "-";
    return d.toLocaleDateString("pt-BR") + " " +
      d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  function dois(n) { return String(n).padStart(2, "0"); }
  function hojeISO() {
    const d = new Date();
    return d.getFullYear() + "-" + dois(d.getMonth() + 1) + "-" + dois(d.getDate());
  }
  // Campo <input type="date"> (AAAA-MM-DD) -> datetime aceito pelo backend
  function dataParaApi(valor) { return valor + "T00:00:00"; }

  function numero(id, tamanho) { return "#" + String(id).padStart(tamanho || 3, "0"); }

  function badge(texto, cor) { return '<span class="badge badge--' + cor + '">' + esc(texto) + "</span>"; }

  const STATUS_EQUIPAMENTO = {
    disponivel: ["Disponível", "verde"], emprestado: ["Emprestado", "amarelo"],
    manutencao: ["Manutenção", "amarelo"], inativo: ["Inativo", "vermelho"]
  };
  function badgeEquipamento(status) {
    const s = STATUS_EQUIPAMENTO[status] || [status || "-", "cinza"];
    return badge(s[0], s[1]);
  }

  const SITUACAO_SOLICITACAO = { pendente: ["Pendente", "amarelo"], aprovado: ["Aprovado", "verde"], recusado: ["Recusado", "vermelho"] };
  function situacaoSolicitacao(s) { return s.situacao || "pendente"; }
  function badgeSolicitacao(s) {
    const x = SITUACAO_SOLICITACAO[situacaoSolicitacao(s)];
    return badge(x[0], x[1]);
  }

  // Status do empréstimo é calculado a partir das datas
  function statusEmprestimo(e) {
    if (e.status) return e.status;               // o servidor já calcula quando a lista vem paginada
    if (e.data_devolucao) return "devolvido";
    const inicioHoje = new Date(); inicioHoje.setHours(0, 0, 0, 0);
    return new Date(e.data_prevista_devolucao) < inicioHoje ? "atrasado" : "ativo";
  }
  const ROTULO_EMPRESTIMO = { ativo: ["Ativo", "verde"], atrasado: ["Atrasado", "vermelho"], devolvido: ["Devolvido", "cinza"] };
  function badgeEmprestimo(e) {
    const x = ROTULO_EMPRESTIMO[statusEmprestimo(e)];
    return badge(x[0], x[1]);
  }

  // ---------- Componentes de interface ----------
  function aviso(texto, tipo) {
    let area = document.getElementById("toasts");
    if (!area) {
      area = document.createElement("div");
      area.id = "toasts";
      area.setAttribute("aria-live", "polite");
      document.body.appendChild(area);
    }
    const el = document.createElement("div");
    el.className = "toast toast--" + (tipo === "erro" ? "erro" : "ok");
    el.textContent = texto;
    area.appendChild(el);
    setTimeout(function () { el.remove(); }, tipo === "erro" ? 7000 : 4000);
  }

  // Preenche <tbody> com estado de carregamento, erro, vazio ou as linhas
  function estadoTabela(tbody, colunas, tipo, texto) {
    tbody.innerHTML = '<tr><td class="estado-tabela estado-tabela--' + tipo +
      '" colspan="' + colunas + '">' + esc(texto) + "</td></tr>";
  }
  function preencherTabela(tbody, colunas, linhasHtml, textoVazio) {
    if (!linhasHtml.length) estadoTabela(tbody, colunas, "vazio", textoVazio);
    else tbody.innerHTML = linhasHtml.join("");
  }

  function abrirJanela(dialog) { if (!dialog.open) dialog.showModal(); }
  function fecharJanela(dialog) { if (dialog.open) dialog.close(); }

  // Pergunta de confirmação em janela própria; devolve Promise<boolean>
  function confirmar(titulo, texto) {
    return new Promise(function (resolver) {
      const d = document.createElement("dialog");
      d.className = "modal";
      d.innerHTML = '<div class="modal__corpo"><h2>' + esc(titulo) + "</h2><p>" + esc(texto) + "</p>" +
        '<div class="modal__rodape"><button type="button" class="botao" data-r="nao">Cancelar</button>' +
        '<button type="button" class="botao botao--primario" data-r="sim">Confirmar</button></div></div>';
      document.body.appendChild(d);
      d.addEventListener("click", function (ev) {
        const r = ev.target.getAttribute && ev.target.getAttribute("data-r");
        if (r) d.close(r);
      });
      d.addEventListener("close", function () {
        const sim = d.returnValue === "sim";
        d.remove();
        resolver(sim);
      });
      d.showModal();
    });
  }

  // Liga o botão "Sair" e os botões que fecham janelas (data-fechar)
  function ligarComuns() {
    const btn = document.getElementById("btn-sair");
    if (btn) btn.addEventListener("click", sair);
    document.addEventListener("click", function (ev) {
      const alvo = ev.target.closest && ev.target.closest("[data-fechar]");
      if (alvo) { const d = alvo.closest("dialog"); if (d) d.close(); }
    });
  }

  // ---------- Validações (as mesmas regras do backend) ----------
  const REGEX_EMAIL = /^[A-Za-z0-9](?:[A-Za-z0-9._%+\-]*[A-Za-z0-9])?@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;

  // Devolve "" quando está tudo certo, ou a mensagem para mostrar ao usuário
  function erroEmail(valor) {
    const v = String(valor || "").trim();
    if (!v) return "Informe o e-mail.";
    if (v.length > 150) return "O e-mail pode ter no máximo 150 caracteres.";
    if (v.indexOf("..") !== -1 || !REGEX_EMAIL.test(v)) return "Informe um e-mail válido, por exemplo: nome@empresa.com.";
    return "";
  }

  function erroCpf(valor) {
    const d = String(valor || "").replace(/\D/g, "");
    if (!d) return "Informe o CPF.";
    if (d.length !== 11) return "O CPF deve ter 11 números.";
    let ok = d !== new Array(12).join(d[0]);
    for (let t = 9; ok && t <= 10; t++) {
      let soma = 0;
      for (let i = 0; i < t; i++) soma += parseInt(d[i], 10) * (t + 1 - i);
      if (((soma * 10) % 11) % 10 !== parseInt(d[t], 10)) ok = false;
    }
    return ok ? "" : "CPF inválido. Confira os números digitados.";
  }

  // Máscara 000.000.000-00 enquanto o usuário digita
  function mascaraCpf(input) {
    input.addEventListener("input", function () {
      const n = input.value.replace(/\D/g, "").slice(0, 11);
      let t = n;
      if (n.length > 9) t = n.slice(0, 3) + "." + n.slice(3, 6) + "." + n.slice(6, 9) + "-" + n.slice(9);
      else if (n.length > 6) t = n.slice(0, 3) + "." + n.slice(3, 6) + "." + n.slice(6);
      else if (n.length > 3) t = n.slice(0, 3) + "." + n.slice(3);
      input.value = t;
    });
  }

  // Mensagem logo abaixo de um campo. tipo: "erro" | "ok" | "info"; texto vazio remove a mensagem
  function mensagemCampo(input, texto, tipo) {
    const campo = input.closest(".campo");
    if (!campo) return;
    let el = campo.querySelector(".campo__msg");
    if (!texto) {
      if (el) el.remove();
      input.removeAttribute("aria-invalid");
      input.removeAttribute("aria-describedby");
      return;
    }
    if (!el) {
      el = document.createElement("span");
      el.id = input.id + "-msg";
      campo.appendChild(el);
    }
    const t = tipo || "erro";
    el.className = "campo__msg campo__msg--" + t;
    el.setAttribute("role", t === "erro" ? "alert" : "status");
    el.textContent = texto;
    if (t === "erro") input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
    input.setAttribute("aria-describedby", el.id);
  }

  // Valida um campo e mostra o erro embaixo dele; devolve true se estiver válido
  function validarCampo(input, funcaoErro) {
    const erro = funcaoErro(input.value);
    mensagemCampo(input, erro, "erro");
    return !erro;
  }

  function atrasar(funcao, ms) {
    let timer = null;
    return function () {
      const args = arguments, self = this;
      clearTimeout(timer);
      timer = setTimeout(function () { funcao.apply(self, args); }, ms);
    };
  }

  // ---------- Empréstimo atrasado: destaque em vermelho ----------
  function classeAtraso(e) { return statusEmprestimo(e) === "atrasado" ? ' class="linha--atraso"' : ""; }
  function dataPrevistaHtml(e) {
    const t = formatarData(e.data_prevista_devolucao);
    return statusEmprestimo(e) === "atrasado" ? '<span class="texto-atraso">' + t + "</span>" : t;
  }

  // ---------- Ordenação por clique no cabeçalho ----------
  // Cabeçalhos com data-ordenar="campo" viram botões. estado = { campo, direcao } é atualizado
  // e aoMudar() é chamado para a lista ser buscada de novo (a ordem vale para todas as páginas).
  function ordenacao(thead, estado, aoMudar) {
    thead.querySelectorAll("th[data-ordenar]").forEach(function (th) {
      if (th.querySelector("button")) return;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "ordenar";
      b.innerHTML = "<span>" + th.innerHTML + '</span><span class="ordenar__seta" aria-hidden="true"></span>';
      b.title = "Clique para ordenar";
      th.innerHTML = "";
      th.appendChild(b);
    });

    function marcar() {
      thead.querySelectorAll("th[data-ordenar]").forEach(function (th) {
        const ativo = th.dataset.ordenar === estado.campo;
        th.setAttribute("aria-sort", ativo ? (estado.direcao === "asc" ? "ascending" : "descending") : "none");
        th.querySelector(".ordenar__seta").textContent = ativo ? (estado.direcao === "asc" ? "↑" : "↓") : "↕";
      });
    }

    thead.addEventListener("click", function (ev) {
      const th = ev.target.closest("th[data-ordenar]");
      if (!th) return;
      const campo = th.dataset.ordenar;
      if (estado.campo === campo) {
        estado.direcao = estado.direcao === "asc" ? "desc" : "asc";
      } else {
        estado.campo = campo;
        estado.direcao = th.dataset.direcaoInicial || "asc";
      }
      marcar();
      aoMudar();
    });
    marcar();
  }

  // ---------- Paginação ----------
  // info = { pagina, total_paginas, total, por_pagina }; aoMudar(numeroDaPagina) busca só aquela página
  function paginacao(el, info, aoMudar) {
    const total = info.total || 0;
    if (!total) { el.innerHTML = ""; el.onclick = null; return; }

    const p = info.pagina, ultima = info.total_paginas;
    const de = (p - 1) * info.por_pagina + 1;
    const ate = Math.min(p * info.por_pagina, total);
    const fmt = function (n) { return n.toLocaleString("pt-BR"); };

    const numeros = [];
    for (let i = 1; i <= ultima; i++) {
      if (i === 1 || i === ultima || Math.abs(i - p) <= 1) numeros.push(i);
    }

    let botoes = "";
    if (ultima > 1) {
      botoes += '<button type="button" class="botao botao--pequeno" data-pagina="' + (p - 1) + '"' + (p === 1 ? " disabled" : "") + ">Anterior</button>";
      let anterior = 0;
      numeros.forEach(function (n) {
        if (n - anterior > 1) botoes += '<span class="paginacao__reticencias" aria-hidden="true">…</span>';
        botoes += '<button type="button" class="botao botao--pequeno' + (n === p ? " botao--primario" : "") + '" data-pagina="' + n + '"' +
          (n === p ? ' aria-current="page"' : "") + ' aria-label="Página ' + n + '">' + n + "</button>";
        anterior = n;
      });
      botoes += '<button type="button" class="botao botao--pequeno" data-pagina="' + (p + 1) + '"' + (p === ultima ? " disabled" : "") + ">Próxima</button>";
    }

    el.innerHTML = '<span class="paginacao__texto">Mostrando ' + fmt(de) + "–" + fmt(ate) + " de " + fmt(total) +
      '</span><div class="paginacao__botoes">' + botoes + "</div>";
    el.onclick = function (ev) {
      const b = ev.target.closest("button[data-pagina]");
      if (!b || b.disabled) return;
      aoMudar(parseInt(b.dataset.pagina, 10));
    };
  }

  window.App = {
    erroEmail: erroEmail, erroCpf: erroCpf, mascaraCpf: mascaraCpf, mensagemCampo: mensagemCampo,
    validarCampo: validarCampo, atrasar: atrasar, paginacao: paginacao,
    ordenacao: ordenacao, classeAtraso: classeAtraso, dataPrevistaHtml: dataPrevistaHtml,
    Sessao: Sessao, api: api, exigirPerfil: exigirPerfil, sair: sair, irParaLogin: irParaLogin,
    irParaTelaDoPerfil: irParaTelaDoPerfil, iniciarNavegacao: iniciarNavegacao, esc: esc,
    formatarData: formatarData, formatarDataHora: formatarDataHora, hojeISO: hojeISO, dataParaApi: dataParaApi, numero: numero,
    badge: badge, badgeEquipamento: badgeEquipamento, badgeSolicitacao: badgeSolicitacao,
    situacaoSolicitacao: situacaoSolicitacao, statusEmprestimo: statusEmprestimo, badgeEmprestimo: badgeEmprestimo,
    aviso: aviso, estadoTabela: estadoTabela, preencherTabela: preencherTabela,
    abrirJanela: abrirJanela, fecharJanela: fecharJanela, confirmar: confirmar, ligarComuns: ligarComuns
  };
})();
