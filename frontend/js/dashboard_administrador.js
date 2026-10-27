/* Painel do administrador: gerencia equipamentos e usuários */
(function () {
  const A = window.App;
  const esc = A.esc;

  const POR_PAGINA_EQUIP = 25;   // tela Equipamentos
  const POR_PAGINA_MANUT = 10;   // janela do dashboard
  const POR_PAGINA_USUARIOS = 25;

  let eu = null;
  let usuariosItens = [];        // somente a página atual da lista de usuários
  let resumoUsuarios = { ativos: 0, por_nivel: {} };
  let resumoEquip = null;
  let niveis = [];
  let categorias = [];
  let equipItens = [];           // somente a página atual da tela Equipamentos
  let filtroEquip = "todos";
  let termoEquip = "";
  let paginaEquip = 1;
  let paginaManut = 1;
  let paginaUsuarios = 1;
  let termoUsuario = "";
  let reqUsuarios = 0;
  const estEquip = { campo: "id", direcao: "desc" };       // mais recentes primeiro
  const estUsuarios = { campo: "id", direcao: "asc" };
  let equipEmEdicao = null;
  let equipDetalhe = null;
  let usuarioEmEdicao = null;
  let reqEquip = 0;              // descarta respostas antigas se o usuário clicar rápido
  let reqManut = 0;

  const tbEquip = document.getElementById("tb-equipamentos");
  const tbUsuarios = document.getElementById("tb-usuarios");
  const tbAtencao = document.getElementById("tb-atencao");
  const tbNiveis = document.getElementById("tb-niveis");
  const pagEquip = document.getElementById("pag-equip");
  const pagUsuarios = document.getElementById("pag-usuarios");
  const pagAtencao = document.getElementById("pag-atencao");
  const dlgEquip = document.getElementById("dlg-equip");
  const dlgUsuario = document.getElementById("dlg-usuario");
  const dlgCategoria = document.getElementById("dlg-categoria");
  const dlgDetalhes = document.getElementById("dlg-detalhes-equip");

  function nomeNivel(id) {
    const n = niveis.find(function (x) { return x.id_acesso === id; });
    return n ? n.nome : "Nível " + id;
  }
  function nomeCategoria(id) {
    const c = categorias.find(function (x) { return x.id_categoria === id; });
    return c ? c.nome : "-";
  }
  function semAcento(t) { return String(t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }
  function linha(rotulo, html, largo) {
    return '<div class="' + (largo ? "largo" : "") + '"><dt>' + esc(rotulo) + "</dt><dd>" + html + "</dd></div>";
  }

  // ---------- Carga de dados ----------
  async function carregar() {
    A.estadoTabela(tbEquip, 7, "carregando", "Carregando equipamentos...");
    A.estadoTabela(tbUsuarios, 7, "carregando", "Carregando usuários...");
    A.estadoTabela(tbAtencao, 3, "carregando", "Carregando...");
    A.estadoTabela(tbNiveis, 2, "carregando", "Carregando...");
    try {
      const r = await Promise.all([
        A.api("/usuarios/resumo"), A.api("/nivel_acesso"), A.api("/categoria_equipamentos"), A.api("/equipamentos/resumo")
      ]);
      resumoUsuarios = r[0]; niveis = r[1]; categorias = r[2]; resumoEquip = r[3];
      desenharIndicadores();
      desenharNiveis();
    } catch (e) {
      [[tbEquip, 7], [tbUsuarios, 7], [tbAtencao, 3], [tbNiveis, 2]].forEach(function (p) { A.estadoTabela(p[0], p[1], "erro", e.message); });
      A.aviso(e.message, "erro");
      return;
    }
    // Só a primeira página de cada lista; as próximas são buscadas quando o usuário clicar
    carregarManutencao(1);
    carregarEquipamentos(1);
    carregarUsuarios(1);
  }

  async function carregarResumo() {
    try { resumoEquip = await A.api("/equipamentos/resumo"); desenharIndicadores(); } catch (e) { /* mantém os valores atuais */ }
  }

  // ---------- Dashboard ----------
  function desenharIndicadores() {
    if (resumoEquip) {
      document.getElementById("ind-total").textContent = resumoEquip.total;
      document.getElementById("ind-disponiveis").textContent = resumoEquip.disponivel;
      document.getElementById("ind-emprestados").textContent = resumoEquip.emprestado;
      document.getElementById("ind-manutencao").textContent = resumoEquip.manutencao;
    }
    document.getElementById("ind-usuarios").textContent = resumoUsuarios.ativos;
  }

  function desenharNiveis() {
    A.preencherTabela(tbNiveis, 2, niveis.map(function (n) {
      const qtd = resumoUsuarios.por_nivel[n.id_acesso] || 0;
      return "<tr><td>" + esc(n.nome) + "</td><td>" + qtd + "</td></tr>";
    }), "Nenhum nível de acesso cadastrado.");
  }

  async function carregarManutencao(pagina) {
    const minha = ++reqManut;
    A.estadoTabela(tbAtencao, 3, "carregando", "Carregando...");
    try {
      const r = await A.api("/equipamentos/paginado?status=manutencao&pagina=" + pagina + "&por_pagina=" + POR_PAGINA_MANUT);
      if (minha !== reqManut) return;
      paginaManut = r.pagina;
      A.preencherTabela(tbAtencao, 3, r.itens.map(function (e) {
        return "<tr><td>" + esc(e.nome) + "</td><td>" + esc(e.numero_patrimonio) + '</td><td class="acoes">' +
          '<button type="button" class="botao botao--pequeno" data-detalhes-equip="' + e.id_equipamento + '">Detalhes</button></td></tr>';
      }), "Nenhum equipamento em manutenção. Tudo certo por aqui.");
      A.paginacao(pagAtencao, r, carregarManutencao);
    } catch (e) {
      if (minha !== reqManut) return;
      A.estadoTabela(tbAtencao, 3, "erro", e.message);
      pagAtencao.innerHTML = "";
    }
  }

  // ---------- Equipamentos (paginação feita no servidor) ----------
  async function carregarEquipamentos(pagina) {
    const minha = ++reqEquip;
    A.estadoTabela(tbEquip, 7, "carregando", "Carregando equipamentos...");
    const q = new URLSearchParams({ pagina: pagina, por_pagina: POR_PAGINA_EQUIP });
    q.set("ordenar", estEquip.campo);
    q.set("direcao", estEquip.direcao);
    if (filtroEquip !== "todos") q.set("status", filtroEquip);
    if (termoEquip) q.set("busca", termoEquip);
    try {
      const r = await A.api("/equipamentos/paginado?" + q.toString());
      if (minha !== reqEquip) return;
      paginaEquip = r.pagina;
      equipItens = r.itens;
      desenharEquipamentos(r.total);
      A.paginacao(pagEquip, r, carregarEquipamentos);
      if (pagina !== r.pagina || pagina > 1) window.scrollTo(0, 0);
    } catch (e) {
      if (minha !== reqEquip) return;
      A.estadoTabela(tbEquip, 7, "erro", e.message);
      pagEquip.innerHTML = "";
      A.aviso(e.message, "erro");
    }
  }

  function desenharEquipamentos(total) {
    const filtrando = filtroEquip !== "todos" || !!termoEquip;
    A.preencherTabela(tbEquip, 7, equipItens.map(function (e) {
      const inativo = e.status_equipamento === "inativo";
      const emprestado = e.status_equipamento === "emprestado";
      const alternar = emprestado ? "" :
        ' <button type="button" class="botao botao--pequeno ' + (inativo ? "" : "botao--perigo") + '" data-alternar-equip="' + e.id_equipamento + '">' +
        (inativo ? "Reativar" : "Inativar") + "</button>";
      return "<tr><td>" + A.numero(e.id_equipamento) + "</td><td>" + esc(e.nome) + "</td><td>" + esc(e.modelo || "-") + "</td><td>" +
        esc(e.numero_patrimonio) + "</td><td>" + esc(nomeCategoria(e.id_categoria)) + "</td><td>" + A.badgeEquipamento(e.status_equipamento) +
        '</td><td class="acoes"><button type="button" class="botao botao--pequeno" data-detalhes-equip="' + e.id_equipamento + '">Detalhes</button> ' +
        '<button type="button" class="botao botao--pequeno" data-editar-equip="' + e.id_equipamento + '">Editar</button>' + alternar + "</td></tr>";
    }), filtrando ? "Nenhum equipamento encontrado com esses filtros." : "Nenhum equipamento cadastrado. Use “Novo equipamento” para começar.");
  }

  // ---------- Detalhes do equipamento ----------
  async function abrirDetalhesEquip(id) {
    // Leva para a tela de Equipamentos e abre os detalhes por cima dela
    if (location.hash !== "#equipamentos") location.hash = "#equipamentos";
    try {
      const e = await A.api("/equipamentos/" + id);
      equipDetalhe = e;
      document.getElementById("dlg-det-titulo").textContent = e.nome;
      document.getElementById("det-equip").innerHTML = [
        linha("Nome", esc(e.nome)),
        linha("Modelo", esc(e.modelo || "-")),
        linha("Número de patrimônio", esc(e.numero_patrimonio)),
        linha("Categoria", esc(nomeCategoria(e.id_categoria))),
        linha("Status", A.badgeEquipamento(e.status_equipamento)),
        linha("Código interno", A.numero(e.id_equipamento)),
        linha("Descrição", esc(e.descricao || "-"), true)
      ].join("");
      A.abrirJanela(dlgDetalhes);
    } catch (err) {
      A.aviso(err.message, "erro");
    }
  }

  document.getElementById("btn-det-editar").addEventListener("click", function () {
    A.fecharJanela(dlgDetalhes);
    if (equipDetalhe) abrirEquip(equipDetalhe);
  });

  // ---------- Cadastro / edição de equipamento (campos liberados em etapas) ----------
  const eqNome = document.getElementById("eq-nome");
  const eqModelo = document.getElementById("eq-modelo");
  const eqPat = document.getElementById("eq-patrimonio");
  const eqCat = document.getElementById("eq-categoria");
  const eqStatus = document.getElementById("eq-status");
  const eqDesc = document.getElementById("eq-descricao");
  const eqGuia = document.getElementById("eq-guia");
  const btnNovaCat = document.getElementById("btn-nova-categoria");
  const btnSalvarEquip = document.getElementById("btn-salvar-equip");

  // Situação da conferência do patrimônio: vazio | verificando | livre | duplicado | erro
  let pat = { valor: "", situacao: "vazio" };
  let patToken = 0;

  function patrimonioDigitado() { return eqPat.value.trim(); }

  function etapas() {
    const edicao = !!equipEmEdicao;
    const nomeOk = eqNome.value.trim().length >= 2;
    const modeloOk = eqModelo.value.trim().length >= 1;
    const patOk = pat.situacao === "livre" && pat.valor === patrimonioDigitado();
    const emprestado = edicao && equipEmEdicao.status_equipamento === "emprestado";
    const liberaResto = edicao || (nomeOk && modeloOk && patOk);

    eqModelo.disabled = !edicao && !nomeOk;
    eqPat.disabled = !edicao && !(nomeOk && modeloOk);
    eqCat.disabled = !liberaResto;
    btnNovaCat.disabled = !liberaResto;
    eqStatus.disabled = !liberaResto || emprestado;
    eqDesc.disabled = !liberaResto;
    btnSalvarEquip.disabled = !(nomeOk && modeloOk && patOk && eqCat.value);

    // Orientação passo a passo (só no cadastro)
    if (!edicao) {
      let texto;
      if (!nomeOk) texto = "Passo 1: informe o nome do equipamento.";
      else if (!modeloOk) texto = "Passo 2: informe o modelo.";
      else if (!patOk) texto = pat.situacao === "duplicado"
        ? "Passo 3: este número de patrimônio já está em uso. Corrija para continuar."
        : "Passo 3: informe o número de patrimônio. Ele não pode existir em outro equipamento.";
      else if (!eqCat.value) texto = "Passo 4: escolha a categoria. Se ela ainda não existir, use “+ Nova categoria”.";
      else texto = "Tudo certo! Revise os dados e clique em “Salvar equipamento”.";
      eqGuia.textContent = texto;
    }
  }

  function montarCategorias(selecionada) {
    eqCat.innerHTML = categorias.length
      ? '<option value="">Selecione a categoria</option>' + categorias.map(function (c) {
          return '<option value="' + c.id_categoria + '">' + esc(c.nome) + "</option>";
        }).join("")
      : '<option value="">Nenhuma categoria cadastrada</option>';
    if (selecionada) eqCat.value = String(selecionada);
  }

  function abrirEquip(equip) {
    equipEmEdicao = equip || null;
    const edicao = !!equip;
    document.getElementById("dlg-equip-titulo").textContent = edicao ? "Editar equipamento" : "Novo equipamento";
    document.getElementById("form-equip").reset();
    document.getElementById("msg-equip").hidden = true;
    document.querySelectorAll("#form-equip .campo__msg").forEach(function (m) { m.remove(); });
    document.querySelectorAll("#form-equip [aria-invalid]").forEach(function (c) { c.removeAttribute("aria-invalid"); });
    patToken++;

    montarCategorias(edicao ? equip.id_categoria : null);

    const opcoes = [["disponivel", "Disponível"], ["manutencao", "Manutenção"], ["inativo", "Inativo"]];
    if (edicao && equip.status_equipamento === "emprestado") opcoes.unshift(["emprestado", "Emprestado"]);
    eqStatus.innerHTML = opcoes.map(function (o) { return '<option value="' + o[0] + '">' + o[1] + "</option>"; }).join("");

    if (edicao) {
      eqNome.value = equip.nome;
      eqModelo.value = equip.modelo || "";
      eqPat.value = equip.numero_patrimonio;
      eqDesc.value = equip.descricao || "";
      eqStatus.value = equip.status_equipamento;
      pat = { valor: equip.numero_patrimonio.trim(), situacao: "livre" };
    } else {
      pat = { valor: "", situacao: "vazio" };
    }
    eqGuia.hidden = edicao;
    document.getElementById("eq-status-ajuda").hidden = !(edicao && equip.status_equipamento === "emprestado");
    etapas();
    A.abrirJanela(dlgEquip);
    (edicao ? eqNome : eqNome).focus();
  }

  eqNome.addEventListener("input", function () {
    A.mensagemCampo(eqNome, "", "erro");
    etapas();
  });
  eqNome.addEventListener("blur", function () {
    const v = eqNome.value.trim();
    if (v && v.length < 2) A.mensagemCampo(eqNome, "O nome deve ter pelo menos 2 caracteres.", "erro");
  });
  eqModelo.addEventListener("input", etapas);
  eqCat.addEventListener("change", etapas);

  // Confere no servidor, assim que o usuário para de digitar, se o patrimônio já existe
  const conferirPatrimonio = A.atrasar(async function () {
    const valor = patrimonioDigitado();
    if (!valor) return;
    const meu = ++patToken;
    let url = "/equipamentos/patrimonio/existe?numero=" + encodeURIComponent(valor);
    if (equipEmEdicao) url += "&ignorar_id=" + equipEmEdicao.id_equipamento;
    try {
      const r = await A.api(url);
      if (meu !== patToken || valor !== patrimonioDigitado()) return;
      if (r.existe) {
        pat = { valor: valor, situacao: "duplicado" };
        A.mensagemCampo(eqPat, "Já existe outro equipamento cadastrado com este número de patrimônio. Informe um número diferente.", "erro");
      } else {
        pat = { valor: valor, situacao: "livre" };
        A.mensagemCampo(eqPat, "Número de patrimônio disponível.", "ok");
      }
    } catch (e) {
      if (meu !== patToken) return;
      pat = { valor: valor, situacao: "erro" };
      A.mensagemCampo(eqPat, "Não foi possível conferir o número agora. Tente novamente.", "erro");
    }
    etapas();
  }, 350);

  eqPat.addEventListener("input", function () {
    patToken++;                                   // ignora conferências que ainda estão em andamento
    const v = patrimonioDigitado();
    if (equipEmEdicao && v === equipEmEdicao.numero_patrimonio.trim()) {
      pat = { valor: v, situacao: "livre" };      // não mudou: continua válido
      A.mensagemCampo(eqPat, "", "erro");
    } else if (!v) {
      pat = { valor: "", situacao: "vazio" };
      A.mensagemCampo(eqPat, "", "erro");
    } else {
      pat = { valor: "", situacao: "verificando" };
      A.mensagemCampo(eqPat, "Conferindo se o número já está em uso...", "info");
      conferirPatrimonio();
    }
    etapas();
  });

  document.getElementById("form-equip").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const msg = document.getElementById("msg-equip");
    function erro(t) { msg.textContent = t; msg.hidden = false; }
    msg.hidden = true;

    const dados = {
      nome: eqNome.value.trim(),
      modelo: eqModelo.value.trim(),
      numero_patrimonio: patrimonioDigitado(),
      id_categoria: parseInt(eqCat.value, 10),
      status_equipamento: eqStatus.value,
      descricao: eqDesc.value.trim() || null
    };
    if (dados.nome.length < 2) return erro("Informe o nome do equipamento.");
    if (!dados.modelo) return erro("Informe o modelo do equipamento.");
    if (!dados.numero_patrimonio) return erro("Informe o número de patrimônio.");
    if (pat.situacao !== "livre") return erro("Aguarde a conferência do número de patrimônio ou corrija o número informado.");
    if (!dados.id_categoria) return erro("Selecione a categoria.");

    btnSalvarEquip.disabled = true;
    const editando = !!equipEmEdicao;
    try {
      if (editando) {
        await A.api("/equipamentos/" + equipEmEdicao.id_equipamento, { metodo: "PUT", corpo: dados });
      } else {
        await A.api("/equipamentos", { metodo: "POST", corpo: dados });
      }
      A.fecharJanela(dlgEquip);
      A.aviso(editando ? "Equipamento atualizado." : "Equipamento cadastrado.");
      carregarResumo();
      carregarManutencao(paginaManut);
      await carregarEquipamentos(editando ? paginaEquip : 1);   // novo equipamento aparece no topo (mais recentes primeiro)
    } catch (e) {
      erro(e.message);
    } finally {
      etapas();
    }
  });

  async function alternarEquip(id) {
    const e = equipItens.find(function (x) { return x.id_equipamento === id; });
    if (!e) return;
    const inativar = e.status_equipamento !== "inativo";
    const ok = await A.confirmar(inativar ? "Inativar equipamento" : "Reativar equipamento",
      inativar ? e.nome + " deixará de ser oferecido para empréstimo." : e.nome + " voltará a ficar disponível.");
    if (!ok) return;
    try {
      await A.api("/equipamentos/" + id, {
        metodo: "PUT", corpo: { status_equipamento: inativar ? "inativo" : "disponivel" }
      });
      A.aviso(inativar ? "Equipamento inativado." : "Equipamento reativado.");
      carregarResumo();
      carregarManutencao(paginaManut);
      await carregarEquipamentos(paginaEquip);
    } catch (err) {
      A.aviso(err.message, "erro");
    }
  }

  // ---------- Nova categoria (sem sair do cadastro de equipamento) ----------
  const catNome = document.getElementById("cat-nome");

  btnNovaCat.addEventListener("click", function () {
    document.getElementById("form-categoria").reset();
    document.getElementById("msg-categoria").hidden = true;
    A.mensagemCampo(catNome, "", "erro");
    A.abrirJanela(dlgCategoria);
    catNome.focus();
  });

  catNome.addEventListener("input", function () { A.mensagemCampo(catNome, "", "erro"); });

  document.getElementById("form-categoria").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const msg = document.getElementById("msg-categoria");
    msg.hidden = true;
    const nome = catNome.value.trim().replace(/\s+/g, " ");

    if (nome.length < 2) { A.mensagemCampo(catNome, "Informe o nome da categoria (mínimo de 2 letras).", "erro"); catNome.focus(); return; }

    // Já existe? Em vez de duplicar, seleciona a que já existe
    const existente = categorias.find(function (c) { return semAcento(c.nome) === semAcento(nome); });
    if (existente) {
      montarCategorias(existente.id_categoria);
      A.fecharJanela(dlgCategoria);
      A.aviso("A categoria “" + existente.nome + "” já existe e foi selecionada.");
      etapas();
      return;
    }

    const botao = document.getElementById("btn-salvar-categoria");
    botao.disabled = true;
    try {
      const criada = await A.api("/categoria_equipamentos", { metodo: "POST", corpo: { nome: nome } });
      categorias.push(criada);
      montarCategorias(criada.id_categoria);
      A.fecharJanela(dlgCategoria);
      A.aviso("Categoria cadastrada.");
      etapas();
    } catch (e) {
      msg.textContent = e.message; msg.hidden = false;
    } finally {
      botao.disabled = false;
    }
  });

  // ---------- Usuários (paginação, busca e ordenação feitas no servidor) ----------
  async function carregarUsuarios(pagina) {
    const minha = ++reqUsuarios;
    A.estadoTabela(tbUsuarios, 7, "carregando", "Carregando usuários...");
    const q = new URLSearchParams({ pagina: pagina, por_pagina: POR_PAGINA_USUARIOS });
    q.set("ordenar", estUsuarios.campo);
    q.set("direcao", estUsuarios.direcao);
    if (termoUsuario) q.set("busca", termoUsuario);
    try {
      const r = await A.api("/usuarios/paginado?" + q.toString());
      if (minha !== reqUsuarios) return;
      paginaUsuarios = r.pagina;
      usuariosItens = r.itens;
      desenharUsuarios();
      A.paginacao(pagUsuarios, r, function (p) { carregarUsuarios(p); window.scrollTo(0, 0); });
    } catch (e) {
      if (minha !== reqUsuarios) return;
      A.estadoTabela(tbUsuarios, 7, "erro", e.message);
      pagUsuarios.innerHTML = "";
      A.aviso(e.message, "erro");
    }
  }

  // Atualiza contadores e a página atual depois de criar, editar ou inativar alguém
  async function recarregarUsuarios() {
    try {
      resumoUsuarios = await A.api("/usuarios/resumo");
      desenharIndicadores();
      desenharNiveis();
    } catch (e) { /* mantém os valores atuais */ }
    await carregarUsuarios(paginaUsuarios);
  }

  function desenharUsuarios() {
    A.preencherTabela(tbUsuarios, 7, usuariosItens.map(function (u) {
      const inativo = u.status_usuario === "inativo";
      const proprio = eu && u.id_usuario === eu.id_usuario;
      const alternar = proprio ? "" :
        ' <button type="button" class="botao botao--pequeno ' + (inativo ? "" : "botao--perigo") + '" data-alternar-usuario="' + u.id_usuario + '">' +
        (inativo ? "Reativar" : "Inativar") + "</button>";
      return "<tr><td>" + A.numero(u.id_usuario) + "</td><td>" + esc(u.nome) + "<br><small>" + esc(u.email) + "</small></td><td>" +
        esc(u.cpf) + "</td><td>" + esc(nomeNivel(u.nivel_acesso)) + "</td><td>" +
        A.badge(inativo ? "Inativo" : "Ativo", inativo ? "vermelho" : "verde") + "</td><td>" + A.formatarData(u.data_criacao) +
        '</td><td class="acoes"><button type="button" class="botao botao--pequeno" data-editar-usuario="' + u.id_usuario + '">Editar</button>' + alternar + "</td></tr>";
    }), termoUsuario ? "Nenhum usuário encontrado para essa pesquisa." : "Nenhum usuário cadastrado.");
  }

  const usNome = document.getElementById("us-nome");
  const usEmail = document.getElementById("us-email");
  const usCpf = document.getElementById("us-cpf");
  const usSenha = document.getElementById("us-senha");

  function erroNomeUsuario(v) {
    v = String(v || "").trim();
    if (!v) return "Informe o nome completo.";
    return v.length < 3 ? "O nome deve ter pelo menos 3 caracteres." : "";
  }
  function erroSenhaUsuario(v) {
    if (!v) return "Crie uma senha.";
    return v.length < 8 ? "A senha deve ter pelo menos 8 caracteres." : "";
  }

  function abrirUsuario(u) {
    usuarioEmEdicao = u || null;
    document.getElementById("dlg-usuario-titulo").textContent = u ? "Editar usuário" : "Novo usuário";
    document.getElementById("form-usuario").reset();
    document.getElementById("msg-usuario").hidden = true;
    document.querySelectorAll("#form-usuario .campo__msg").forEach(function (m) { m.remove(); });
    document.querySelectorAll("#form-usuario [aria-invalid]").forEach(function (c) { c.removeAttribute("aria-invalid"); });
    document.getElementById("us-nivel").innerHTML = niveis.map(function (n) {
      return '<option value="' + n.id_acesso + '">' + esc(n.nome) + "</option>";
    }).join("");
    // Na edição, CPF e senha ficam bloqueados (alteração só direto no banco)
    document.getElementById("campo-us-senha").hidden = !!u;
    usSenha.placeholder = "Mínimo de 8 caracteres";
    usCpf.readOnly = !!u;
    document.getElementById("us-cpf-ajuda").hidden = !u;
    if (u) {
      usNome.value = u.nome;
      usEmail.value = u.email;
      usCpf.value = u.cpf;
      document.getElementById("us-nivel").value = String(u.nivel_acesso);
      document.getElementById("us-status").value = u.status_usuario;
    }
    A.abrirJanela(dlgUsuario);
    usNome.focus();
  }

  A.mascaraCpf(usCpf);

  function vigiar(campo, funcaoErro) {
    campo.addEventListener("blur", function () {
      if (campo.readOnly) return;
      if (campo === usSenha && usuarioEmEdicao) return;
      A.validarCampo(campo, funcaoErro);
    });
    campo.addEventListener("input", function () {
      if (campo.getAttribute("aria-invalid") === "true") A.validarCampo(campo, funcaoErro);
    });
  }
  vigiar(usNome, erroNomeUsuario);
  vigiar(usEmail, A.erroEmail);
  vigiar(usCpf, A.erroCpf);
  vigiar(usSenha, erroSenhaUsuario);

  document.getElementById("form-usuario").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    const msg = document.getElementById("msg-usuario");
    function erro(t) { msg.textContent = t; msg.hidden = false; }
    msg.hidden = true;

    const dados = {
      nome: usNome.value.trim(),
      email: usEmail.value.trim(),
      cpf: usCpf.value.trim(),
      nivel_acesso: parseInt(document.getElementById("us-nivel").value, 10),
      status_usuario: document.getElementById("us-status").value
    };
    const senha = usuarioEmEdicao ? "" : usSenha.value;

    // Confere todos os campos de uma vez e leva o foco ao primeiro com problema
    const checagens = [[usNome, erroNomeUsuario], [usEmail, A.erroEmail]];
    if (!usuarioEmEdicao) { checagens.push([usCpf, A.erroCpf]); checagens.push([usSenha, erroSenhaUsuario]); }
    const resultados = checagens.map(function (c) { return [c[0], A.validarCampo(c[0], c[1])]; });
    const falhou = resultados.filter(function (r) { return !r[1]; })[0];
    if (falhou) { falhou[0].focus(); return; }

    if (!dados.nivel_acesso) return erro("Selecione o nível de acesso.");
    if (usuarioEmEdicao && usuarioEmEdicao.id_usuario === eu.id_usuario && dados.status_usuario === "inativo") {
      return erro("Você não pode inativar a sua própria conta.");
    }

    const botao = document.getElementById("btn-salvar-usuario");
    botao.disabled = true;
    try {
      if (usuarioEmEdicao) {
        // CPF e senha nunca são enviados na edição
        await A.api("/usuarios/" + usuarioEmEdicao.id_usuario, {
          metodo: "PUT",
          corpo: { nome: dados.nome, email: dados.email, nivel_acesso: dados.nivel_acesso, status_usuario: dados.status_usuario }
        });
      } else {
        // O cadastro sempre cria um usuário comum; nível e status são ajustados em seguida
        const criado = await A.api("/usuarios", {
          metodo: "POST",
          corpo: { nome: dados.nome, email: dados.email, cpf: dados.cpf, senha: senha, nivel_acesso: 1 }
        });
        if (dados.nivel_acesso !== 1 || dados.status_usuario !== "ativo") {
          await A.api("/usuarios/" + criado.id_usuario, {
            metodo: "PUT", corpo: { nivel_acesso: dados.nivel_acesso, status_usuario: dados.status_usuario }
          });
        }
      }
      A.fecharJanela(dlgUsuario);
      A.aviso(usuarioEmEdicao ? "Usuário atualizado." : "Usuário cadastrado.");
      await recarregarUsuarios();
    } catch (e) {
      erro(e.message);
    } finally {
      botao.disabled = false;
    }
  });

  async function alternarUsuario(id) {
    const u = usuariosItens.find(function (x) { return x.id_usuario === id; });
    if (!u) return;
    const inativar = u.status_usuario !== "inativo";
    const ok = await A.confirmar(inativar ? "Inativar usuário" : "Reativar usuário",
      inativar ? u.nome + " não conseguirá mais entrar no sistema." : u.nome + " poderá entrar no sistema novamente.");
    if (!ok) return;
    try {
      await A.api("/usuarios/" + id, { metodo: "PUT", corpo: { status_usuario: inativar ? "inativo" : "ativo" } });
      A.aviso(inativar ? "Usuário inativado." : "Usuário reativado.");
      await recarregarUsuarios();
    } catch (err) {
      A.aviso(err.message, "erro");
    }
  }

  // ---------- Eventos ----------
  document.getElementById("btn-novo-equip").addEventListener("click", function () { abrirEquip(null); });
  document.getElementById("btn-novo-usuario").addEventListener("click", function () { abrirUsuario(null); });
  // A busca de usuários também é feita no servidor (aguarda a pessoa parar de digitar)
  document.getElementById("busca-usuario").addEventListener("input", A.atrasar(function () {
    const termo = document.getElementById("busca-usuario").value.trim();
    if (termo === termoUsuario) return;
    termoUsuario = termo;
    carregarUsuarios(1);
  }, 400));

  // Clique no cabeçalho ordena a lista inteira (todas as páginas)
  A.ordenacao(document.getElementById("th-equipamentos"), estEquip, function () { carregarEquipamentos(1); });
  A.ordenacao(document.getElementById("th-usuarios"), estUsuarios, function () { carregarUsuarios(1); });

  // A busca de equipamentos é feita no servidor (aguarda o usuário parar de digitar)
  const buscarEquip = A.atrasar(function () {
    const termo = document.getElementById("busca-equip").value.trim();
    if (termo === termoEquip) return;
    termoEquip = termo;
    carregarEquipamentos(1);
  }, 400);
  document.getElementById("busca-equip").addEventListener("input", buscarEquip);

  document.getElementById("filtros-equip").addEventListener("click", function (ev) {
    const chip = ev.target.closest(".chip");
    if (!chip) return;
    filtroEquip = chip.dataset.filtro;
    document.querySelectorAll("#filtros-equip .chip").forEach(function (c) {
      c.setAttribute("aria-pressed", c === chip ? "true" : "false");
    });
    carregarEquipamentos(1);
  });

  document.addEventListener("click", function (ev) {
    const t = ev.target.closest("button");
    if (!t) return;
    if (t.dataset.detalhesEquip) abrirDetalhesEquip(parseInt(t.dataset.detalhesEquip, 10));
    if (t.dataset.editarEquip) abrirEquip(equipItens.find(function (e) { return e.id_equipamento === parseInt(t.dataset.editarEquip, 10); }));
    if (t.dataset.alternarEquip) alternarEquip(parseInt(t.dataset.alternarEquip, 10));
    if (t.dataset.editarUsuario) abrirUsuario(usuariosItens.find(function (u) { return u.id_usuario === parseInt(t.dataset.editarUsuario, 10); }));
    if (t.dataset.alternarUsuario) alternarUsuario(parseInt(t.dataset.alternarUsuario, 10));
  });

  // ---------- Início ----------
  A.ligarComuns();
  A.exigirPerfil("Administrador").then(function (u) {
    eu = u;
    A.iniciarNavegacao("dashboard");
    carregar();
  });
})();
