/* Painel do gestor: analisa solicitações e controla empréstimos e devoluções.
   As listas são paginadas e ordenadas no servidor: o navegador só recebe a página que exibe. */
(function () {
  const A = window.App;
  const esc = A.esc;

  const POR_PAGINA = 25;

  let solicItens = [];            // página atual de Solicitações
  let emprItens = [];             // página atual de Empréstimos
  let filtroSituacao = "";
  let filtroEmprestimo = "todos";
  const estSolic = { campo: "id", direcao: "desc" };
  const estEmpr = { campo: "id", direcao: "desc" };
  let paginaSolic = 1;
  let paginaEmpr = 1;
  let reqSolic = 0;               // descarta respostas antigas se o usuário clicar rápido
  let reqEmpr = 0;
  let solicitacaoAberta = null;
  let emprestimoAberto = null;
  let ultimoAviso = 0;

  const tbRecentes = document.getElementById("tb-recentes");
  const tbAtivos = document.getElementById("tb-ativos");
  const tbSolic = document.getElementById("tb-solicitacoes");
  const tbEmpr = document.getElementById("tb-emprestimos");
  const pagSolic = document.getElementById("pag-solic");
  const pagEmpr = document.getElementById("pag-empr");
  const dlgSolic = document.getElementById("dlg-solicitacao");
  const dlgEmpr = document.getElementById("dlg-emprestimo");

  function consulta(pagina, porPagina, extra, estado) {
    const q = new URLSearchParams({ pagina: pagina, por_pagina: porPagina });
    Object.keys(extra || {}).forEach(function (k) { if (extra[k]) q.set(k, extra[k]); });
    if (estado) { q.set("ordenar", estado.campo); q.set("direcao", estado.direcao); }
    return q.toString();
  }

  // Mostra no máximo um aviso de erro por vez, mesmo que várias listas falhem juntas
  function falha(e) {
    if (Date.now() - ultimoAviso > 2000) { A.aviso(e.message, "erro"); ultimoAviso = Date.now(); }
  }

  // ---------- Dashboard ----------
  async function carregarIndicadores() {
    try {
      const r = await Promise.all([A.api("/equipamentos/resumo"), A.api("/solicitacoes/resumo")]);
      document.getElementById("ind-total").textContent = r[0].total;
      document.getElementById("ind-disponiveis").textContent = r[0].disponivel;
      document.getElementById("ind-emprestados").textContent = r[0].emprestado;
      document.getElementById("ind-manutencao").textContent = r[0].manutencao;
      document.getElementById("ind-pendentes").textContent = r[1].pendente;
    } catch (e) { falha(e); }
  }

  async function carregarListasDoDashboard() {
    A.estadoTabela(tbRecentes, 3, "carregando", "Carregando...");
    A.estadoTabela(tbAtivos, 3, "carregando", "Carregando...");
    try {
      const r = await A.api("/solicitacoes/paginado?" + consulta(1, 5, {}, { campo: "id", direcao: "desc" }));
      A.preencherTabela(tbRecentes, 3, r.itens.map(function (s) {
        return "<tr><td>" + A.numero(s.id_solicitacao) + "</td><td>" + esc(s.solicitante_nome) + "</td><td>" + A.badgeSolicitacao(s) + "</td></tr>";
      }), "Nenhuma solicitação registrada.");
    } catch (e) { A.estadoTabela(tbRecentes, 3, "erro", e.message); falha(e); }

    try {
      // Os mais urgentes primeiro: menor data de devolução; atrasados aparecem em vermelho
      const r = await A.api("/emprestimos/paginado?" + consulta(1, 5, { status: "abertos" }, { campo: "prevista", direcao: "asc" }));
      A.preencherTabela(tbAtivos, 3, r.itens.map(function (e) {
        return "<tr" + A.classeAtraso(e) + "><td>" + esc(e.usuario_nome) + "</td><td>" + esc(e.equipamento_nome) + "</td><td>" +
          A.dataPrevistaHtml(e) + "</td></tr>";
      }), "Nenhum empréstimo ativo.");
    } catch (e) { A.estadoTabela(tbAtivos, 3, "erro", e.message); falha(e); }
  }

  // ---------- Solicitações ----------
  async function carregarSolicitacoes(pagina) {
    const minha = ++reqSolic;
    A.estadoTabela(tbSolic, 8, "carregando", "Carregando solicitações...");
    try {
      const r = await A.api("/solicitacoes/paginado?" + consulta(pagina, POR_PAGINA, { situacao: filtroSituacao }, estSolic));
      if (minha !== reqSolic) return;
      paginaSolic = r.pagina;
      solicItens = r.itens;
      A.preencherTabela(tbSolic, 8, solicItens.map(function (s) {
        let acoes = '<button type="button" class="botao botao--pequeno" data-solic="' + s.id_solicitacao + '">' +
          (s.situacao === "pendente" ? "Analisar" : "Ver") + "</button>";
        if (s.situacao === "aprovado" && !s.tem_emprestimo) {
          acoes += ' <button type="button" class="botao botao--primario botao--pequeno" data-registrar="' + s.id_solicitacao + '">Registrar empréstimo</button>';
        }
        return "<tr><td>" + A.numero(s.id_solicitacao) + "</td><td>" + esc(s.solicitante_nome) + "</td><td>" +
          esc(s.equipamento_nome) + "</td><td>" + A.formatarDataHora(s.data_solicitacao) + "</td><td>" +
          A.formatarData(s.data_retirada_solicitada) + "</td><td>" + A.badgeSolicitacao(s) + "</td><td>" +
          esc(s.autorizador_nome || "-") + '</td><td class="acoes">' + acoes + "</td></tr>";
      }), filtroSituacao ? "Nenhuma solicitação com essa situação." : "Nenhuma solicitação registrada.");
      A.paginacao(pagSolic, r, function (p) { carregarSolicitacoes(p); window.scrollTo(0, 0); });
    } catch (e) {
      if (minha !== reqSolic) return;
      A.estadoTabela(tbSolic, 8, "erro", e.message);
      pagSolic.innerHTML = "";
      falha(e);
    }
  }

  function linha(rotulo, html, largo) {
    return '<div class="' + (largo ? "largo" : "") + '"><dt>' + esc(rotulo) + "</dt><dd>" + html + "</dd></div>";
  }

  function abrirSolicitacao(id) {
    const s = solicItens.find(function (x) { return x.id_solicitacao === id; });
    if (!s) return;
    solicitacaoAberta = s;
    const pendente = s.situacao === "pendente";

    document.getElementById("dlg-solic-titulo").textContent = "Detalhes da solicitação " + A.numero(s.id_solicitacao);
    document.getElementById("solic-detalhes").innerHTML = [
      linha("Solicitante", esc(s.solicitante_nome)),
      linha("Equipamento", esc(s.equipamento_nome)),
      linha("Número de patrimônio", esc(s.equipamento_patrimonio)),
      linha("Situação", A.badgeSolicitacao(s)),
      linha("Solicitada em", A.formatarDataHora(s.data_solicitacao)),
      linha("Retirada solicitada para", A.formatarData(s.data_retirada_solicitada)),
      linha("Devolução prevista", A.formatarData(s.data_prevista_devolucao)),
      linha("Observações do solicitante", esc(s.observacoes_solicitante || "-"), true)
    ].concat(pendente ? [] : [
      linha("Respondida por", esc(s.autorizador_nome || "-")),
      linha("Respondida em", A.formatarDataHora(s.data_autorizacao)),
      linha("Observação do responsável", esc(s.observacoes_autorizador || "-"), true)
    ]).join("");

    document.getElementById("bloco-analise").hidden = !pendente;
    document.getElementById("btn-aprovar").hidden = !pendente;
    document.getElementById("btn-recusar").hidden = !pendente;
    document.getElementById("analise-obs").value = "";
    document.getElementById("msg-analise").hidden = true;
    A.abrirJanela(dlgSolic);
  }

  async function responder(situacao) {
    const msg = document.getElementById("msg-analise");
    const obs = document.getElementById("analise-obs").value.trim();
    msg.hidden = true;
    if (situacao === "recusado" && !obs) {
      msg.textContent = "Explique o motivo da recusa."; msg.hidden = false; return;
    }
    const botoes = [document.getElementById("btn-aprovar"), document.getElementById("btn-recusar")];
    botoes.forEach(function (b) { b.disabled = true; });
    try {
      // Só a decisão é enviada; o backend define autorizador e data
      // e, ao aprovar, já registra o empréstimo e marca o equipamento como emprestado
      await A.api("/solicitacoes/" + solicitacaoAberta.id_solicitacao, {
        metodo: "PUT",
        corpo: { situacao: situacao, observacoes_autorizador: obs || null }
      });
      A.fecharJanela(dlgSolic);
      A.aviso(situacao === "aprovado" ? "Solicitação aprovada e empréstimo registrado." : "Solicitação recusada.");
      recarregarTudo();
    } catch (e) {
      msg.textContent = e.message; msg.hidden = false;
    } finally {
      botoes.forEach(function (b) { b.disabled = false; });
    }
  }

  // Para solicitações antigas aprovadas que ficaram sem empréstimo
  async function registrarEmprestimo(id) {
    const s = solicItens.find(function (x) { return x.id_solicitacao === id; });
    if (!s) return;
    const ok = await A.confirmar("Registrar empréstimo",
      "Entregar " + s.equipamento_nome + " para " + s.solicitante_nome + "? O equipamento ficará como emprestado.");
    if (!ok) return;
    try {
      await A.api("/emprestimos", {
        metodo: "POST",
        corpo: {
          id_usuario: s.id_solicitante,
          id_solicitacao: s.id_solicitacao,
          id_equipamento: s.id_equipamento,
          data_prevista_devolucao: s.data_prevista_devolucao
        }
      });
      A.aviso("Empréstimo registrado.");
      recarregarTudo();
      location.hash = "#emprestimos";
    } catch (e) {
      A.aviso(e.message, "erro");
    }
  }

  // ---------- Empréstimos ----------
  async function carregarEmprestimos(pagina) {
    const minha = ++reqEmpr;
    A.estadoTabela(tbEmpr, 9, "carregando", "Carregando empréstimos...");
    try {
      const r = await A.api("/emprestimos/paginado?" + consulta(pagina, POR_PAGINA,
        { status: filtroEmprestimo === "todos" ? "" : filtroEmprestimo }, estEmpr));
      if (minha !== reqEmpr) return;
      paginaEmpr = r.pagina;
      emprItens = r.itens;
      A.preencherTabela(tbEmpr, 9, emprItens.map(function (e) {
        const devolver = !e.data_devolucao
          ? ' <button type="button" class="botao botao--primario botao--pequeno" data-empr="' + e.id_emprestimo + '">Devolver</button>' : "";
        return "<tr" + A.classeAtraso(e) + "><td>" + A.numero(e.id_emprestimo) + "</td><td>" + esc(e.usuario_nome) + "</td><td>" +
          esc(e.equipamento_nome) + "</td><td>" + esc(e.equipamento_patrimonio) + "</td><td>" +
          A.formatarData(e.data_retirada) + "</td><td>" + A.dataPrevistaHtml(e) + "</td><td>" + A.formatarData(e.data_devolucao) + "</td><td>" +
          A.badgeEmprestimo(e) + '</td><td class="acoes"><button type="button" class="botao botao--pequeno" data-empr="' +
          e.id_emprestimo + '">Ver</button>' + devolver + "</td></tr>";
      }), filtroEmprestimo === "todos" ? "Nenhum empréstimo registrado." : "Nenhum empréstimo nesta categoria.");
      A.paginacao(pagEmpr, r, function (p) { carregarEmprestimos(p); window.scrollTo(0, 0); });
    } catch (e) {
      if (minha !== reqEmpr) return;
      A.estadoTabela(tbEmpr, 9, "erro", e.message);
      pagEmpr.innerHTML = "";
      falha(e);
    }
  }

  function abrirEmprestimo(id) {
    const e = emprItens.find(function (x) { return x.id_emprestimo === id; });
    if (!e) return;
    emprestimoAberto = e;
    const aberto = !e.data_devolucao;

    document.getElementById("dlg-empr-titulo").textContent = "Empréstimo " + A.numero(e.id_emprestimo);
    document.getElementById("empr-detalhes").innerHTML = [
      linha("Usuário", esc(e.usuario_nome)),
      linha("Equipamento", esc(e.equipamento_nome)),
      linha("Patrimônio", esc(e.equipamento_patrimonio)),
      linha("Retirada", A.formatarData(e.data_retirada)),
      linha("Devolução prevista", A.dataPrevistaHtml(e)),
      linha("Devolvido em", A.formatarData(e.data_devolucao)),
      linha("Status", A.badgeEmprestimo(e)),
      linha("Observações", esc(e.observacoes || "-"), true)
    ].join("");

    document.getElementById("bloco-devolucao").hidden = !aberto;
    document.getElementById("btn-devolver").hidden = !aberto;

    // A data de devolução fica entre a retirada e hoje; o calendário não deixa escolher fora disso
    const campoData = document.getElementById("devolucao-data");
    const retiradaISO = e.data_retirada ? String(e.data_retirada).slice(0, 10) : "";
    campoData.min = retiradaISO;
    campoData.max = A.hojeISO();
    campoData.value = retiradaISO && retiradaISO > A.hojeISO() ? retiradaISO : A.hojeISO();
    document.getElementById("devolucao-data-ajuda").textContent = retiradaISO
      ? "Escolha uma data entre a retirada (" + A.formatarData(e.data_retirada) + ") e hoje."
      : "A data não pode ser futura.";
    document.getElementById("devolucao-obs").value = "";
    document.getElementById("msg-devolucao").hidden = true;
    A.abrirJanela(dlgEmpr);
  }

  document.getElementById("form-devolucao").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const msg = document.getElementById("msg-devolucao");
    const data = document.getElementById("devolucao-data").value;
    const obs = document.getElementById("devolucao-obs").value.trim();
    msg.hidden = true;
    if (!data) { msg.textContent = "Informe a data de devolução."; msg.hidden = false; return; }
    const campoData = document.getElementById("devolucao-data");
    if (campoData.min && data < campoData.min) {
      msg.textContent = "A devolução não pode ser anterior à retirada (" + A.formatarData(campoData.min + "T00:00:00") + ")."; msg.hidden = false; return;
    }
    if (campoData.max && data > campoData.max) {
      msg.textContent = "A data de devolução não pode ser uma data futura."; msg.hidden = false; return;
    }

    const botao = document.getElementById("btn-devolver");
    botao.disabled = true;
    try {
      await A.api("/emprestimos/" + emprestimoAberto.id_emprestimo, {
        metodo: "PUT",
        corpo: {
          data_devolucao: A.dataParaApi(data),
          observacoes: obs || emprestimoAberto.observacoes
        }
      });
      A.fecharJanela(dlgEmpr);
      A.aviso("Devolução registrada.");
      recarregarTudo();
    } catch (e) {
      msg.textContent = e.message; msg.hidden = false;
    } finally {
      botao.disabled = false;
    }
  });

  // ---------- Carga ----------
  // Recarrega indicadores, listas do dashboard e as duas listas, mantendo a página atual de cada uma
  function recarregarTudo() {
    carregarIndicadores();
    carregarListasDoDashboard();
    carregarSolicitacoes(paginaSolic);
    carregarEmprestimos(paginaEmpr);
  }

  // ---------- Eventos ----------
  A.ordenacao(document.getElementById("th-solicitacoes"), estSolic, function () { carregarSolicitacoes(1); });
  A.ordenacao(document.getElementById("th-emprestimos"), estEmpr, function () { carregarEmprestimos(1); });

  document.getElementById("filtro-situacao").addEventListener("change", function (ev) {
    filtroSituacao = ev.target.value;
    carregarSolicitacoes(1);
  });
  document.getElementById("filtros-emprestimo").addEventListener("click", function (ev) {
    const chip = ev.target.closest(".chip");
    if (!chip) return;
    filtroEmprestimo = chip.dataset.filtro;
    document.querySelectorAll("#filtros-emprestimo .chip").forEach(function (c) {
      c.setAttribute("aria-pressed", c === chip ? "true" : "false");
    });
    carregarEmprestimos(1);
  });
  document.getElementById("btn-aprovar").addEventListener("click", function () { responder("aprovado"); });
  document.getElementById("btn-recusar").addEventListener("click", function () { responder("recusado"); });
  document.addEventListener("click", function (ev) {
    const t = ev.target.closest("button");
    if (!t) return;
    if (t.dataset.solic) abrirSolicitacao(parseInt(t.dataset.solic, 10));
    if (t.dataset.registrar) registrarEmprestimo(parseInt(t.dataset.registrar, 10));
    if (t.dataset.empr) abrirEmprestimo(parseInt(t.dataset.empr, 10));
  });

  // ---------- Início ----------
  A.ligarComuns();
  A.exigirPerfil("Gestor").then(function () {
    A.iniciarNavegacao("dashboard");
    carregarIndicadores();
    carregarListasDoDashboard();
    carregarSolicitacoes(1);
    carregarEmprestimos(1);
  });
})();
