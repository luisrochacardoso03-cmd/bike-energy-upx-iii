// Bike Energy - JavaScript das telas
// O Python envia os dados em JSON. Aqui mostramos nas tabelas.

let dados = null;
let telaAtual = "";
const campo = (nome) => document.getElementById(nome);

function limpar(texto) {
  // Evita que textos digitados pelos usuarios sejam interpretados como HTML.
  return String(texto ?? "").replace(/[&<>"']/g, (letra) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[letra]));
}

function numero(valor, casas = 3) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas, maximumFractionDigits: casas
  });
}

function dataHora(valor) {
  return valor ? new Date(valor).toLocaleString("pt-BR") : "—";
}

async function api(endereco, valores) {
  // Quando passamos 'valores', enviamos POST. Sem valores, usamos GET.
  const opcoes = valores === undefined ? {} : {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(valores)
  };
  let resposta;
  try {
    resposta = await fetch(endereco, opcoes);
  } catch (erro) {
    throw Error("Servidor não encontrado. Execute o arquivo INICIAR.bat, não o Go Live.");
  }
  const json = await resposta.json();
  if (!resposta.ok) throw Error(json.erro || "Não foi possível completar a ação");
  return json;
}

function aviso(texto) {
  campo("mensagem").textContent = texto;
  campo("mensagem").classList.remove("escondido");
  setTimeout(() => campo("mensagem").classList.add("escondido"), 3500);
}

async function atualizar() {
  dados = await api("/api/data");
  desenhar();
}

async function entrar() {
  await atualizar();
  campo("entrada").classList.add("escondido");
  campo("sistema").classList.remove("escondido");
  const gestor = dados.user.role === "GESTOR";
  campo("menuAluno").classList.toggle("escondido", gestor);
  campo("menuGestor").classList.toggle("escondido", !gestor);
  campo("nomeUsuario").textContent = dados.user.name;
  campo("tipoUsuario").textContent = gestor ? "Gestor da academia" : "Aluno";
  mostrarTela(gestor ? "inicioGestor" : "inicioAluno");
}

function mostrarTela(nome) {
  telaAtual = nome;
  document.querySelectorAll(".tela").forEach((tela) => {
    tela.classList.toggle("escondido", tela.id !== nome);
  });
  document.querySelectorAll("nav button").forEach((botao) => {
    botao.classList.toggle("ativo", botao.dataset.tela === nome);
  });
  const titulos = {
    inicioAluno: "Meu painel", treino: "Novo treino", historico: "Meus treinos",
    beneficiosAluno: "Meus benefícios", inicioGestor: "Painel do gestor",
    usuarios: "Usuários", bicicletas: "Bicicletas", todosTreinos: "Treinos",
    beneficiosGestor: "Benefícios", resgates: "Resgates", regras: "Regra de pontos"
  };
  campo("titulo").textContent = titulos[nome];
}

function desenhoAluno() {
  campo("primeiroNome").textContent = dados.user.name.split(" ")[0];
  const treinos = dados.sessions;
  const energia = treinos.reduce((s, t) => s + t.energy_kwh, 0);
  const minutos = treinos.reduce((s, t) => s + t.duration_minutes, 0);
  campo("energiaAluno").textContent = numero(energia) + " kWh";
  campo("saldoAluno").textContent = dados.wallet;
  campo("totalTreinosAluno").textContent = treinos.length;
  campo("tempoAluno").textContent = minutos;

  campo("tabelaHistorico").innerHTML = treinos.map((t) => `<tr>
    <td>${dataHora(t.created_at)}</td><td>${limpar(t.bike_name)}</td>
    <td>${t.duration_minutes}</td><td>${t.avg_watts}</td>
    <td>${numero(t.energy_kwh)}</td><td>${t.points}</td></tr>`).join("")
    || '<tr><td colspan="6">Nenhum treino ainda.</td></tr>';

  const bicicletas = dados.bikes.filter((b) => b.status === "ATIVA");
  campo("bikeTreino").innerHTML = bicicletas.map((b) =>
    `<option value="${b.id}">${limpar(b.name)}</option>`).join("");
  campo("formTreino").querySelector("button").disabled = bicicletas.length === 0;
  calcularPrevia();

  campo("saldoBeneficios").textContent = dados.wallet + " pontos";
  campo("listaBeneficiosAluno").innerHTML = dados.benefits.filter((b) => b.active).map((b) => `
    <div class="beneficio"><h3>${limpar(b.name)}</h3>
      <strong>${b.points_cost} pontos</strong>
      <button onclick="resgatar(${b.id})" ${dados.wallet < b.points_cost ? "disabled" : ""}>Resgatar</button>
    </div>`).join("") || "Nenhum benefício disponível.";

  campo("resgatesAluno").innerHTML = dados.redemptions.map((r) => `<tr>
    <td>${dataHora(r.created_at)}</td><td>${limpar(r.benefit_name)}</td>
    <td>${r.points_spent}</td>
    <td class="${r.status === "RETIRADO" ? "retirado" : "pendente"}">
      ${r.status === "RETIRADO" ? "Retirado" : "Aguardando retirada"}</td>
    </tr>`).join("") || '<tr><td colspan="4">Nenhum resgate realizado.</td></tr>';
}

function calcularPrevia() {
  if (!dados || dados.user.role !== "ALUNO") return;
  const watts = Number(campo("watts").value || 0);
  const minutos = Number(campo("minutos").value || 0);
  const energia = watts * minutos / 60000;
  const pontos = Math.floor(watts * minutos / 60 * dados.points_per_wh + 0.5);
  campo("previaEnergia").textContent = numero(energia) + " kWh";
  campo("previaPontos").textContent = pontos;
}

function desenhoGestor() {
  const treinos = dados.sessions;
  campo("totalUsuarios").textContent = dados.users.filter((u) => u.role === "ALUNO").length;
  campo("totalBikes").textContent = dados.bikes.filter((b) => b.status === "ATIVA").length;
  campo("energiaGeral").textContent = numero(treinos.reduce((s, t) => s + t.energy_kwh, 0)) + " kWh";
  campo("totalPendentes").textContent = dados.redemptions.filter((r) => r.status === "PENDENTE").length;

  campo("tabelaUsuarios").innerHTML = dados.users.map((u) => `<tr>
    <td>${u.id}</td><td>${limpar(u.name)}</td><td>${limpar(u.email)}</td><td>${u.role}</td></tr>`).join("");

  campo("tabelaBikes").innerHTML = dados.bikes.map((b) => `<tr>
    <td>${limpar(b.code)}</td><td>${limpar(b.name)}</td><td>${b.status}</td>
    <td><button class="acao" onclick="trocarBike(${b.id}, '${b.status === "ATIVA" ? "MANUTENCAO" : "ATIVA"}')">
    ${b.status === "ATIVA" ? "Colocar em manutenção" : "Ativar"}</button></td></tr>`).join("");

  campo("tabelaTodosTreinos").innerHTML = treinos.map((t) => `<tr>
    <td>${dataHora(t.created_at)}</td><td>${limpar(t.user_name)}</td><td>${limpar(t.bike_name)}</td>
    <td>${t.duration_minutes}</td><td>${numero(t.energy_kwh)}</td><td>${t.points}</td></tr>`).join("")
    || '<tr><td colspan="6">Nenhum treino registrado.</td></tr>';

  campo("tabelaBeneficiosGestor").innerHTML = dados.benefits.map((b) => `<tr>
    <td>${limpar(b.name)}</td><td>${b.points_cost}</td><td>${b.active ? "Ativo" : "Inativo"}</td>
    <td><button class="acao" onclick="trocarBeneficio(${b.id}, ${b.active ? 0 : 1})">
    ${b.active ? "Desativar" : "Ativar"}</button></td></tr>`).join("");

  campo("tabelaResgates").innerHTML = dados.redemptions.map((r) => `<tr>
    <td>${limpar(r.user_name)}</td><td>${limpar(r.benefit_name)}</td>
    <td>${dataHora(r.created_at)}</td><td>${r.points_spent}</td>
    <td class="${r.status === "RETIRADO" ? "retirado" : "pendente"}">
    ${r.status === "RETIRADO" ? "Retirado" : "Aguardando retirada"}</td>
    <td><button class="acao" onclick="trocarResgate(${r.id}, '${r.status === "RETIRADO" ? "PENDENTE" : "RETIRADO"}')">
    ${r.status === "RETIRADO" ? "Voltar para pendente" : "Confirmar retirada"}</button></td></tr>`).join("")
    || '<tr><td colspan="6">Nenhum benefício resgatado.</td></tr>';

  campo("pontosPorWh").value = dados.points_per_wh;
}

function desenhar() {
  if (!dados) return;
  if (dados.user.role === "GESTOR") desenhoGestor();
  else desenhoAluno();
}

// Eventos de login e cadastro
campo("formLogin").onsubmit = async function(evento) {
  evento.preventDefault();
  try {
    await api("/api/login", {email: campo("emailLogin").value, password: campo("senhaLogin").value});
    await entrar();
  } catch (erro) { alert(erro.message); }
};

campo("formCadastro").onsubmit = async function(evento) {
  evento.preventDefault();
  try {
    await api("/api/register", {
      name: campo("nomeCadastro").value,
      email: campo("emailCadastro").value,
      password: campo("senhaCadastro").value
    });
    campo("voltarLogin").click();
    aviso("Aluno cadastrado no banco! Agora faça login.");
  } catch (erro) { alert(erro.message); }
};

campo("abrirCadastro").onclick = () => {
  campo("formLogin").classList.add("escondido");
  campo("formCadastro").classList.remove("escondido");
};
campo("voltarLogin").onclick = () => {
  campo("formCadastro").classList.add("escondido");
  campo("formLogin").classList.remove("escondido");
};
campo("demoAluno").onclick = () => {
  campo("emailLogin").value = "camila@bikeenergy.com";
  campo("senhaLogin").value = "";
  campo("senhaLogin").focus();
};
campo("demoGestor").onclick = () => {
  campo("emailLogin").value = "gestor@bikeenergy.com";
  campo("senhaLogin").value = "";
  campo("senhaLogin").focus();
};
campo("sair").onclick = async () => {
  await api("/api/logout", {});
  dados = null;
  campo("sistema").classList.add("escondido");
  campo("entrada").classList.remove("escondido");
  campo("senhaLogin").value = "";
};
document.querySelectorAll("nav button").forEach((botao) => {
  botao.onclick = () => mostrarTela(botao.dataset.tela);
});

// Eventos do aluno
campo("watts").oninput = calcularPrevia;
campo("minutos").oninput = calcularPrevia;
campo("formTreino").onsubmit = async function(evento) {
  evento.preventDefault();
  try {
    const resposta = await api("/api/sessions", {
      bike_id: Number(campo("bikeTreino").value),
      watts: Number(campo("watts").value),
      minutes: Number(campo("minutos").value)
    });
    await atualizar();
    mostrarTela("inicioAluno");
    aviso("Treino salvo! Você ganhou " + resposta.points + " pontos.");
  } catch (erro) { alert(erro.message); }
};
async function resgatar(id) {
  if (!confirm("Deseja trocar seus pontos por este benefício?")) return;
  try {
    await api("/api/redeem", {id: id});
    await atualizar();
    aviso("Benefício resgatado. Aguarde a entrega pela academia.");
  } catch (erro) { alert(erro.message); }
}

// Eventos do gestor
campo("formBike").onsubmit = async function(evento) {
  evento.preventDefault();
  try {
    await api("/api/bikes", {name: campo("nomeBike").value, code: campo("codigoBike").value});
    campo("formBike").reset(); await atualizar(); aviso("Bicicleta cadastrada!");
  } catch (erro) { alert(erro.message); }
};
async function trocarBike(id, status) {
  await acaoGestor("/api/bike-status", {id: id, status: status});
}
campo("formBeneficio").onsubmit = async function(evento) {
  evento.preventDefault();
  try {
    await api("/api/benefits", {name: campo("nomeBeneficio").value, points_cost: Number(campo("custoBeneficio").value)});
    campo("formBeneficio").reset(); await atualizar(); aviso("Benefício cadastrado!");
  } catch (erro) { alert(erro.message); }
};
async function trocarBeneficio(id, active) {
  await acaoGestor("/api/benefit-status", {id: id, active: active});
}
async function trocarResgate(id, status) {
  await acaoGestor("/api/redemption-status", {id: id, status: status});
}
campo("formRegra").onsubmit = async function(evento) {
  evento.preventDefault();
  await acaoGestor("/api/rule", {points_per_wh: Number(campo("pontosPorWh").value)});
};
async function acaoGestor(caminho, valores) {
  try {
    await api(caminho, valores);
    await atualizar();
    aviso("Alteração salva no banco de dados!");
  } catch (erro) { alert(erro.message); }
}

// Quando a página abre, verifica se o usuario ja esta logado.
(async function() {
  try {
    const resposta = await api("/api/me");
    if (resposta.user) await entrar();
  } catch (erro) {
    aviso(erro.message);
  }
})();
