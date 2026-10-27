/* Painel do usuário comum: equipamentos, solicitações e empréstimos próprios.
   As listas são paginadas e ordenadas no servidor: o navegador só recebe a página que exibe. */
(function () {
  const A = window.App;
  const esc = A.esc;

  const POR_PAGINA = 25;

  let usuario = null;
  let equipItens = [];            // página atual de equipamentos disponíveis
  let solicItens = [];            // página atual das minhas solicitações
  let emprItens = [];             // página atual dos meus empréstimos
  let termoEquip = "";
  const estEquip = { campo: "nome", direcao: "asc" };
  const estSolic = { campo: "id", direcao: "desc" };
  const estEmpr = { campo: "id", direcao: "desc" };
  let paginaEquip = 1, paginaSolic = 1, paginaEmpr = 1;
  let reqEquip = 0, reqSolic = 0, reqEmpr = 0;
  let ultimoAviso = 0;

  const tbEquip = document.getElementById("tb-equipamentos");
  const tbSolic = document.getElementById("tb-solicitacoes");
  const tbEmpr = document.getElementById("tb-emprestimos");
  const pagEquip = document.getElementById("pag-equip");
  const pagSolic = document.getElementById("pag-solic");
  const pagEmpr = document.getElementById("pag-empr");
  const dlgNova = document.getElementById("dlg-nova");
  const dlgDet = document.getElementById("dlg-detalhes");

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
  async function carregarDashboard() {
    const lista = document.getElementById("lista-atividades");
    try {
      const r = await Promise.all([
        A.api("/solicitacoes/resumo"),
        A.api("/emprestimos/resumo"),
        A.api("/solicitacoes/paginado?" + consulta(1, 4, {}, { campo: "id", direcao: "desc" })),
        A.api("/emprestimos/paginado?" + consulta(1, 3, { status: "abertos" }, { campo: "prevista", direcao: "asc" }))
      ]);
      document.getElementById("ind-pendentes").textContent = r[0].pendente;
      document.getElementById("ind-ativos").textContent = r[1].abertos;

      const itens = [];
      r[2].itens.forEach(function (s) {
        itens.push("<li><span>" + esc(s.equipamento_nome) + " | Retirada: " +
          A.formatarData(s.data_retirada_solicitada) + "</span>" + A.badgeSolicitacao(s) + "</li>");
      });
      r[3].itens.forEach(function (e) {
        itens.push('<li class="' + (A.statusEmprestimo(e) === "atrasado" ? "atrasado" : "") + '"><span>' + esc(e.equipamento_nome) + " | Devolução: " +
          A.dataPrevistaHtml(e) + "</span>" + A.badgeEmprestimo(e) + "</li>");
      });
      lista.innerHTML = itens.length ? itens.join("")
        : '<li class="vazio">Você ainda não tem atividades. Solicite um equipamento para começar.</li>';
    } catch (e) { falha(e); }
  }

  // ---------- Equipamentos disponíveis ----------
  async function carregarEquipamentos(pagina) {
    const minha = ++reqEquip;
    A.estadoTabela(tbEquip, 4, "carregando", "Carregando equipamentos...");
    try {
      const r = await A.api("/equipamentos/disponiveis?" + consulta(pagina, POR_PAGINA, { busca: termoEquip }, estEquip));
      if (minha !== reqEquip) return;
      paginaEquip = r.pagina;
      equipItens = r.itens;
      A.preencherTabela(tbEquip, 4, equipItens.map(function (e) {
        return "<tr><td>" + esc(e.nome) + "</td><td>" + esc(e.modelo || "-") + "</td><td>" +
          A.badgeEquipamento(e.status_equipamento) + '</td><td class="acoes">' +
          '<button type="button" class="botao botao--primario botao--pequeno" data-solicitar="' + e.id_equipamento + '">Solicitar</button></td></tr>';
      }), termoEquip ? "Nenhum equipamento disponível encontrado para essa pesquisa." : "Nenhum equipamento disponível no momento.");
      A.paginacao(pagEquip, r, function (p) { carregarEquipamentos(p); window.scrollTo(0, 0); });
    } catch (e) {
      if (minha !== reqEquip) return;
      A.estadoTabela(tbEquip, 4, "erro", e.message);
      pagEquip.innerHTML = "";
      falha(e);
    }
  }

  // ---------- Minhas solicitações ----------
  async function carregarSolicitacoes(pagina) {
    const minha = ++reqSolic;
    A.estadoTabela(tbSolic, 5, "carregando", "Carregando solicitações...");
    try {
      const r = await A.api("/solicitacoes/paginado?" + consulta(pagina, POR_PAGINA, {}, estSolic));
      if (minha !== reqSolic) return;
      paginaSolic = r.pagina;
      solicItens = r.itens;
      A.preencherTabela(tbSolic, 5, solicItens.map(function (s) {
        return "<tr><td>" + A.numero(s.id_solicitacao) + "</td><td>" + esc(s.equipamento_nome) + "</td><td>" +
          A.formatarData(s.data_retirada_solicitada) + "</td><td>" + A.badgeSolicitacao(s) + '</td><td class="acoes">' +
          '<button type="button" class="botao botao--pequeno" data-ver-solic="' + s.id_solicitacao + '">Ver</button></td></tr>';
      }), "Você ainda não fez nenhuma solicitação.");
      A.paginacao(pagSolic, r, function (p) { carregarSolicitacoes(p); window.scrollTo(0, 0); });
    } catch (e) {
      if (minha !== reqSolic) return;
      A.estadoTabela(tbSolic, 5, "erro", e.message);
      pagSolic.innerHTML = "";
      falha(e);
    }
  }

  // ---------- Meus empréstimos ----------
  async function carregarEmprestimos(pagina) {
    const minha = ++reqEmpr;
    A.estadoTabela(tbEmpr, 6, "carregando", "Carregando empréstimos...");
    try {
      const r = await A.api("/emprestimos/paginado?" + consulta(pagina, POR_PAGINA, {}, estEmpr));
      if (minha !== reqEmpr) return;
      paginaEmpr = r.pagina;
      emprItens = r.itens;
      A.preencherTabela(tbEmpr, 6, emprItens.map(function (e) {
        return "<tr" + A.classeAtraso(e) + "><td>" + A.numero(e.id_emprestimo) + "</td><td>" + esc(e.equipamento_nome) + "</td><td>" +
          esc(e.equipamento_patrimonio) + "</td><td>" + A.dataPrevistaHtml(e) + "</td><td>" +
          A.badgeEmprestimo(e) + '</td><td class="acoes">' +
          '<button type="button" class="botao botao--pequeno" data-ver-empr="' + e.id_emprestimo + '">Ver</button></td></tr>';
      }), "Você não tem empréstimos registrados.");
      A.paginacao(pagEmpr, r, function (p) { carregarEmprestimos(p); window.scrollTo(0, 0); });
    } catch (e) {
      if (minha !== reqEmpr) return;
      A.estadoTabela(tbEmpr, 6, "erro", e.message);
      pagEmpr.innerHTML = "";
      falha(e);
    }
  }

  // ---------- Detalhes ----------
  function linha(rotulo, valorHtml, largo) {
    return '<div class="' + (largo ? "largo" : "") + '"><dt>' + esc(rotulo) + "</dt><dd>" + valorHtml + "</dd></div>";
  }
  function abrirDetalhes(titulo, linhas) {
    document.getElementById("dlg-detalhes-titulo").textContent = titulo;
    document.getElementById("detalhes-lista").innerHTML = linhas.join("");
    A.abrirJanela(dlgDet);
  }

  function verSolicitacao(id) {
    const s = solicItens.find(function (x) { return x.id_solicitacao === id; });
    if (!s) return;
    const l = [
      linha("Equipamento", esc(s.equipamento_nome)),
      linha("Patrimônio", esc(s.equipamento_patrimonio)),
      linha("Solicitada em", A.formatarDataHora(s.data_solicitacao)),
      linha("Retirada solicitada para", A.formatarData(s.data_retirada_solicitada)),
      linha("Devolução prevista", A.formatarData(s.data_prevista_devolucao)),
      linha("Situação", A.badgeSolicitacao(s)),
      linha("Respondida em", A.formatarDataHora(s.data_autorizacao)),
      linha("Suas observações", esc(s.observacoes_solicitante || "-"), true)
    ];
    if (s.observacoes_autorizador) l.push(linha("Resposta do responsável", esc(s.observacoes_autorizador), true));
    abrirDetalhes("Solicitação " + A.numero(s.id_solicitacao), l);
  }

  function verEmprestimo(id) {
    const e = emprItens.find(function (x) { return x.id_emprestimo === id; });
    if (!e) return;
    abrirDetalhes("Empréstimo " + A.numero(e.id_emprestimo), [
      linha("Equipamento", esc(e.equipamento_nome)),
      linha("Patrimônio", esc(e.equipamento_patrimonio)),
      linha("Retirada", A.formatarData(e.data_retirada)),
      linha("Devolução prevista", A.dataPrevistaHtml(e)),
      linha("Devolvido em", A.formatarData(e.data_devolucao)),
      linha("Status", A.badgeEmprestimo(e)),
      linha("Observações", esc(e.observacoes || "-"), true)
    ]);
  }

  // ---------- Nova solicitação ----------
  // O equipamento é escolhido na lista (botão "Solicitar"): o pedido já abre com ele preenchido
  function abrirNova(idEquipamento) {
    const e = equipItens.find(function (x) { return x.id_equipamento === idEquipamento; });
    if (!e) return;
    document.getElementById("form-nova").reset();
    document.getElementById("nova-equipamento").value = String(e.id_equipamento);
    document.getElementById("nova-equipamento-nome").value = e.nome + (e.modelo ? " - " + e.modelo : "");
    const hoje = A.hojeISO();
    document.getElementById("nova-retirada").min = hoje;
    document.getElementById("nova-devolucao").min = hoje;
    document.getElementById("msg-nova").hidden = true;
    A.abrirJanela(dlgNova);
  }

  document.getElementById("form-nova").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const msg = document.getElementById("msg-nova");
    const idEquip = parseInt(document.getElementById("nova-equipamento").value, 10);
    const retirada = document.getElementById("nova-retirada").value;
    const devolucao = document.getElementById("nova-devolucao").value;
    const obs = document.getElementById("nova-obs").value.trim();

    function erro(t) { msg.textContent = t; msg.hidden = false; }
    msg.hidden = true;
    if (!idEquip) return erro("Escolha o equipamento na lista e clique em Solicitar.");
    if (!retirada || !devolucao) return erro("Informe as datas de retirada e devolução.");
    if (retirada < A.hojeISO()) return erro("A data de retirada não pode ser anterior a hoje.");
    if (devolucao < retirada) return erro("A devolução deve ser no mesmo dia da retirada ou depois dele.");

    const botao = document.getElementById("btn-enviar-nova");
    botao.disabled = true; botao.textContent = "Enviando...";
    try {
      await A.api("/solicitacoes", {
        metodo: "POST",
        corpo: {
          id_equipamento: idEquip,
          id_solicitante: usuario.id_usuario,
          data_retirada_solicitada: A.dataParaApi(retirada),
          data_prevista_devolucao: A.dataParaApi(devolucao),
          observacoes_solicitante: obs || null,
          situacao: "pendente"
        }
      });
      A.fecharJanela(dlgNova);
      A.aviso("Solicitação enviada para aprovação.");
      location.hash = "#solicitacoes";
      carregarDashboard();
      carregarSolicitacoes(1);
    } catch (e) {
      erro(e.message);
    } finally {
      botao.disabled = false; botao.textContent = "Enviar solicitação";
    }
  });

  // ---------- Eventos ----------
  A.ordenacao(document.getElementById("th-equipamentos"), estEquip, function () { carregarEquipamentos(1); });
  A.ordenacao(document.getElementById("th-solicitacoes"), estSolic, function () { carregarSolicitacoes(1); });
  A.ordenacao(document.getElementById("th-emprestimos"), estEmpr, function () { carregarEmprestimos(1); });

  // Pesquisa feita no servidor, depois que a pessoa para de digitar
  document.getElementById("busca-equip").addEventListener("input", A.atrasar(function () {
    const termo = document.getElementById("busca-equip").value.trim();
    if (termo === termoEquip) return;
    termoEquip = termo;
    carregarEquipamentos(1);
  }, 400));

  // "+ Nova solicitação" leva à lista, onde a pessoa escolhe o equipamento
  document.getElementById("btn-nova").addEventListener("click", function () {
    location.hash = "#equipamentos";
    A.aviso("Escolha o equipamento na lista e clique em Solicitar.");
  });
  document.addEventListener("click", function (ev) {
    const t = ev.target.closest("button");
    if (!t) return;
    if (t.dataset.solicitar) abrirNova(parseInt(t.dataset.solicitar, 10));
    if (t.dataset.verSolic) verSolicitacao(parseInt(t.dataset.verSolic, 10));
    if (t.dataset.verEmpr) verEmprestimo(parseInt(t.dataset.verEmpr, 10));
  });

  // ---------- Início ----------
  A.ligarComuns();
  A.exigirPerfil("Usuário comum").then(function (u) {
    usuario = u;
    A.iniciarNavegacao("dashboard");
    carregarDashboard();
    carregarEquipamentos(1);
    carregarSolicitacoes(1);
    carregarEmprestimos(1);
  });
})();
