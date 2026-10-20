'use strict';
const $ = id => document.getElementById(id);
const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const number = (value, digits=3) => Number(value).toLocaleString('pt-BR', {minimumFractionDigits:digits, maximumFractionDigits:digits});
const date = value => new Date(value).toLocaleString('pt-BR', {timeZone:'America/Sao_Paulo', dateStyle:'short', timeStyle:'short'});
const statusText = status => status === 'collected' ? 'Retirado' : 'Aguardando retirada';
const empty = (columns, message='Nenhum registro encontrado.') => `<tr><td colspan="${columns}">${safe(message)}</td></tr>`;
let state = null, busy = false, rewardEditing = null;
const pendingKeys = new Map();
const views = {
  studentDashboard:['ALUNO','Visão geral'], sessionView:['ALUNO','Nova sessão'], historyView:['ALUNO','Histórico'], benefitsView:['ALUNO','Benefícios'],
  managerDashboard:['GESTOR','Painel da academia'], bikesView:['GESTOR','Bicicletas'], benefitsManageView:['GESTOR','Benefícios'],
  redemptionsView:['GESTOR','Resgates'], rulesView:['GESTOR','Regra de pontos'], studentsView:['GESTOR','Alunos'], reportView:['GESTOR','Relatórios']
};
async function api(path, payload) {
  let response;
  try {
    response = await fetch(path, {method:payload === undefined ? 'GET':'POST', credentials:'same-origin',
      headers:payload === undefined ? {} : {'Content-Type':'application/json'}, body:payload === undefined ? undefined : JSON.stringify(payload)});
  } catch { throw new Error('Servidor indisponível. Verifique o terminal e tente novamente.'); }
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && state) leaveApp();
    throw new Error(data.error || 'Não foi possível concluir a operação.');
  }
  return data;
}
function toast(message) {
  $('toast').textContent = message; $('toast').classList.add('show');
  setTimeout(() => $('toast').classList.remove('show'), 4500);
}
async function run(action) {
  if (busy) return;
  busy = true;
  const buttons = [...document.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled)')];
  buttons.forEach(button => button.disabled = true);
  $('loginError').textContent = $('appError').textContent = '';
  try { await action(); }
  catch (error) { (state ? $('appError'):$('loginError')).textContent = error.message; }
  finally { busy = false; buttons.forEach(button => button.disabled = false); if(state?.user.role==='aluno') $('finishSessionBtn').disabled=!state.bikes.some(b=>b.active); }
}
async function refresh() { state = await api('/api/state'); renderAll(); }
async function mutate(path, payload, message, idempotent=false) {
  const identity = path + JSON.stringify(payload);
  if (idempotent) {
    if (!pendingKeys.has(identity)) pendingKeys.set(identity, crypto.randomUUID());
    payload = {...payload, request_id:pendingKeys.get(identity)};
  }
  const result = await api(path, payload);
  await refresh();
  pendingKeys.delete(identity);
  toast(message); return result;
}
function leaveApp() {
  state = null; pendingKeys.clear(); $('appView').classList.add('hidden'); $('loginView').classList.remove('hidden'); $('loginPassword').value = '';
}
function enterApp() {
  const manager = state.user.role === 'gestor';
  $('loginView').classList.add('hidden'); $('appView').classList.remove('hidden');
  $('studentNav').classList.toggle('hidden', manager); $('managerNav').classList.toggle('hidden', !manager);
  $('userName').textContent = state.user.name; $('userRole').textContent = manager ? 'Gestor da academia':'Aluno';
  $('avatar').textContent = state.user.name.split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase();
  showView(manager ? 'managerDashboard':'studentDashboard');
}
function showView(id) {
  if (!state || !views[id] || ((views[id][0] === 'GESTOR') !== (state.user.role === 'gestor'))) return;
  document.querySelectorAll('.view').forEach(el => el.classList.toggle('hidden', el.id !== id));
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === id);
    if (el.dataset.view === id) el.setAttribute('aria-current','page'); else el.removeAttribute('aria-current');
  });
  [$('pageEyebrow').textContent, $('pageTitle').textContent] = views[id];
  renderAll(); $('mainContent').focus({preventScroll:true});
}
function renderStudent() {
  const s = state.summary;
  $('greeting').textContent = `Continue pedalando, ${state.user.name.split(' ')[0]}!`;
  $('studentKwh').textContent = `${number(s.month_wh / 1000)} kWh`;
  $('studentPoints').textContent = `${s.balance} pts`; $('studentSessions').textContent = s.sessions; $('studentMinutes').textContent = `${s.minutes} min`;
  $('pointsRuleText').textContent = `${number(state.points_per_wh,1)} ponto(s) por Wh`;
  const progress = Math.min(100, Math.round(s.month_wh / state.user.goal_wh * 100));
  $('goalPercent').textContent = `${progress}%`; $('progressRing').style.setProperty('--progress', `${progress*3.6}deg`);
  if (document.activeElement !== $('goalInput')) $('goalInput').value = state.user.goal_wh;
  $('recentSessions').innerHTML = state.rides.slice(0,3).map(r=>`<div class="session-item"><div><strong>${safe(r.bike_name)}</strong><span>${safe(date(r.created_at))}</span></div><div><strong>${r.minutes} min</strong><span>tempo simulado</span></div><div><strong>${number(r.kwh)} kWh</strong><span>energia simulada</span></div><div><strong>${r.points} pts</strong><span>pontos</span></div></div>`).join('') || '<div class="empty">Nenhuma sessão registrada.</div>';
  const rewards = state.rewards.filter(r=>r.active && r.stock>0).sort((a,b)=>a.cost-b.cost);
  const next = rewards.find(r=>r.cost>s.balance) || rewards[rewards.length-1];
  $('nextBenefitName').textContent = next?.name || 'Nenhum benefício disponível'; $('nextBenefitPoints').textContent = next ? `${next.cost} pts`:'—';
  $('benefitProgress').style.width = next ? `${Math.min(100,s.balance/next.cost*100)}%`:'0%';
  $('benefitHint').textContent = next ? (s.balance >= next.cost ? 'Você pode resgatar esta recompensa.' : `Faltam ${next.cost-s.balance} pontos.`) : 'Aguarde novos benefícios da academia.';
  $('historyTable').innerHTML = state.rides.map(r=>`<tr><td>${safe(date(r.started_at))} → ${safe(date(r.ended_at))}</td><td>${safe(r.bike_name)}</td><td>${r.minutes} min</td><td>${r.watts} W</td><td>${number(r.kwh,6)} kWh</td><td><strong>${r.points} pts</strong></td></tr>`).join('') || empty(6);
  const selected = $('bikeSelect').value, bikes = state.bikes.filter(b=>b.active);
  $('bikeSelect').innerHTML = bikes.map(b=>`<option value="${b.id}">${safe(b.name)} • BK-${b.id}</option>`).join('');
  if (bikes.some(b=>String(b.id)===selected)) $('bikeSelect').value = selected;
  $('finishSessionBtn').disabled = !bikes.length; updateSimulation();
  $('benefitsPoints').textContent = s.balance;
  $('benefitsGrid').innerHTML = state.rewards.map(r=>`<article class="benefit-card"><div class="benefit-icon" aria-hidden="true">🎁</div><h3>${safe(r.name)}</h3><p>${safe(r.description)}</p><p>${r.stock} unidade(s) disponível(is). Sem equivalência financeira direta com a energia.</p><footer><span class="cost">${r.cost} pts</span><button data-redeem="${r.id}" ${s.balance<r.cost || !r.stock ? 'disabled':''}>Resgatar</button></footer></article>`).join('') || '<div class="empty">Nenhum benefício disponível.</div>';
  $('studentRedemptions').innerHTML = state.redemptions.map(r=>`<div class="manager-benefit-row"><div><strong>#${r.id} · ${safe(r.reward_name)}</strong><span>${safe(date(r.created_at))}</span></div><span>${r.cost} pts · ${statusText(r.status)}${r.collected_at ? ' · '+safe(date(r.collected_at)):''}</span></div>`).join('') || '<div class="empty">Nenhum benefício resgatado ainda.</div>';
}
function updateSimulation() {
  if (!state) return;
  const watts = Number($('wattsRange').value), minutes = Number($('minutesRange').value), kwh = watts * minutes / 60000;
  const points = Math.floor((watts * minutes * Math.round(state.points_per_wh*10)+300)/600);
  $('wattsValue').textContent = $('liveWatts').textContent = watts; $('minutesValue').textContent = minutes;
  $('liveKwh').textContent = `${number(kwh,6)} kWh`; $('livePoints').textContent = `${points} pts`;
  $('formulaResult').textContent = `${watts} W × ${number(minutes/60,3)} h = ${number(kwh,6)} kWh`;
}
function renderManager() {
  $('managerKwh').textContent = `${number(state.summary.energy_wh/1000)} kWh`; $('managerPoints').textContent = `${state.summary.points} pts`;
  $('managerSessions').textContent = state.summary.sessions; $('activeBikes').textContent = state.bikes.filter(b=>b.active).length;
  $('managerRule').textContent = `${number(state.points_per_wh,1)} ponto(s) por Wh`;
  $('bikesGrid').innerHTML = state.bikes.map(b=>`<article class="bike-card"><header><strong>${safe(b.name)}</strong><span class="status ${b.active?'on':'off'}">${b.active?'Ativa':'Manutenção'}</span></header><div class="bike-icon" aria-hidden="true">🚲</div><small>Identificador: BK-${b.id}</small><p><button class="small-action secondary" data-bike="${b.id}">${b.active?'Colocar em manutenção':'Ativar bicicleta'}</button></p></article>`).join('');
  $('managerBenefitsList').innerHTML = state.rewards.map(r=>`<div class="manager-benefit-row"><div><strong>${safe(r.name)}</strong><p>${r.cost} pts · ${r.stock} em estoque · ${r.active?'Ativo':'Inativo'}</p></div><div class="row-actions"><button class="small-action secondary" data-edit-reward="${r.id}">Editar</button><button class="small-action secondary" data-toggle-reward="${r.id}">${r.active?'Desativar':'Ativar'}</button></div></div>`).join('') || '<p>Nenhum benefício cadastrado.</p>';
  $('redemptionsTable').innerHTML = state.redemptions.map(r=>`<tr><td>#${r.id} · ${safe(date(r.created_at))}</td><td>${safe(r.student)}</td><td>${safe(r.reward_name)}</td><td>${r.cost} pts</td><td><span class="redemption-status ${r.status==='collected'?'done':'pending'}">${statusText(r.status)}</span>${r.collected_at ? '<br>'+safe(date(r.collected_at)):''}</td><td><button class="small-action ${r.status==='collected'?'secondary':''}" data-pickup="${r.id}">${r.status==='collected'?'Voltar para pendente':'Confirmar retirada'}</button></td></tr>`).join('') || empty(6,'Nenhum resgate realizado até o momento.');
  if (document.activeElement !== $('pointsPerWhInput')) $('pointsPerWhInput').value = state.points_per_wh;
  ruleExample(); renderStudents();
}
function renderStudents() {
  if (!state?.students) return;
  const term = $('studentSearch').value.toLocaleLowerCase('pt-BR');
  $('studentsTable').innerHTML = state.students.filter(u=>(u.name+' '+u.email).toLocaleLowerCase('pt-BR').includes(term)).map(u=>`<tr><td>${safe(u.name)}</td><td>${safe(u.email)}</td><td>${u.balance} pts</td><td>${safe(date(u.created_at))}</td></tr>`).join('') || empty(4);
}
function ruleExample() { $('ruleExample').textContent = `0,050 kWh = ${Math.round(50*Number($('pointsPerWhInput').value || 1))} pontos`; }
function renderAll() { if (!state) return; if (state.user.role === 'gestor') renderManager(); else renderStudent(); }
function resetReward() {
  rewardEditing = null; $('rewardFormTitle').textContent = 'Novo benefício'; $('benefitNameInput').value = $('benefitDescription').value = '';
  $('benefitPointsInput').value = 200; $('benefitStock').value = 20; $('addBenefitBtn').textContent = 'Adicionar benefício';
}
function toggleRegister(register) { $('loginForm').classList.toggle('hidden',register); $('registerForm').classList.toggle('hidden',!register); $('loginError').textContent = ''; }
$('loginForm').onsubmit = event => {event.preventDefault();run(async()=>{await api('/api/login',{email:$('loginEmail').value,password:$('loginPassword').value});$('loginPassword').value='';await refresh();enterApp();});};
$('registerForm').onsubmit = event => {event.preventDefault();run(async()=>{await api('/api/register',{name:$('registerName').value,email:$('registerEmail').value,password:$('registerPassword').value});$('loginEmail').value=$('registerEmail').value;$('registerForm').reset();toggleRegister(false);toast('Cadastro salvo no banco. Entre com sua senha.');});};
$('registerToggle').onclick = ()=>toggleRegister(true); $('loginToggle').onclick = ()=>toggleRegister(false);
$('logoutBtn').onclick = ()=>run(async()=>{await api('/api/logout',{});leaveApp();});
document.querySelectorAll('.nav-item,[data-go]').forEach(button=>button.onclick=()=>run(async()=>{await refresh();showView(button.dataset.view || button.dataset.go);}));
$('wattsRange').oninput = $('minutesRange').oninput = updateSimulation;
$('finishSessionBtn').onclick = ()=>run(async()=>{await mutate('/api/rides',{bike_id:Number($('bikeSelect').value),minutes:Number($('minutesRange').value),watts:Number($('wattsRange').value)},'Sessão e pontos gravados no banco.',true);showView('studentDashboard');});
$('benefitsGrid').onclick = event => {
  const button = event.target.closest('[data-redeem]'); if (!button || button.disabled) return;
  const r = state.rewards.find(r=>r.id===Number(button.dataset.redeem));
  if (confirm(`Resgatar “${r.name}” por ${r.cost} pontos?`)) run(()=>mutate('/api/redemptions',{reward_id:r.id},'Resgate registrado. Aguarde a retirada.',true));
};
$('redemptionsTable').onclick = event => {
  const button = event.target.closest('[data-pickup]'); if (!button) return;
  const r = state.redemptions.find(r=>r.id===Number(button.dataset.pickup)); run(()=>mutate('/api/pickup',{id:r.id,collected:r.status!=='collected'},'Status da retirada atualizado.'));
};
$('bikesGrid').onclick = event => {
  const button = event.target.closest('[data-bike]'); if (!button) return;
  const bike = state.bikes.find(b=>b.id===Number(button.dataset.bike)); run(()=>mutate('/api/bikes',{...bike,active:!bike.active},'Status da bicicleta atualizado.'));
};
$('bikeForm').onsubmit = event => {event.preventDefault();run(async()=>{await mutate('/api/bikes',{name:$('bikeName').value,active:true},'Bicicleta cadastrada.');$('bikeForm').reset();});};
$('managerBenefitsList').onclick = event => {
  const button = event.target.closest('button'); if (!button) return;
  const r = state.rewards.find(r=>r.id===Number(button.dataset.editReward || button.dataset.toggleReward)); if (!r) return;
  if (button.dataset.toggleReward) return run(()=>mutate('/api/reward-status',{id:r.id,active:!r.active},'Benefício atualizado.'));
  rewardEditing=r;$('rewardFormTitle').textContent='Editar benefício';$('benefitNameInput').value=r.name;$('benefitPointsInput').value=r.cost;
  $('benefitDescription').value=r.description;$('benefitStock').value=r.stock;$('addBenefitBtn').textContent='Salvar benefício';$('benefitNameInput').focus();
};
$('cancelBenefitEdit').onclick = resetReward;
$('addBenefitBtn').onclick = ()=>{
  if (!['benefitNameInput','benefitPointsInput','benefitStock'].every(id=>$(id).reportValidity())) return;
  run(async()=>{await mutate('/api/rewards',{...(rewardEditing?{id:rewardEditing.id,version:rewardEditing.version}:{}),name:$('benefitNameInput').value,description:$('benefitDescription').value,cost:Number($('benefitPointsInput').value),stock:Number($('benefitStock').value),active:rewardEditing?!!rewardEditing.active:true},'Benefício salvo.');resetReward();});
};
$('pointsPerWhInput').oninput=ruleExample;
$('saveRuleBtn').onclick=()=>{if($('pointsPerWhInput').reportValidity())run(()=>mutate('/api/rate',{points_per_wh:Number($('pointsPerWhInput').value)},'Regra salva para as próximas sessões.'));};
$('goalForm').onsubmit=event=>{event.preventDefault();run(()=>mutate('/api/goal',{goal_wh:Number($('goalInput').value)},'Meta mensal salva.'));};
$('studentSearch').oninput=renderStudents;
$('reportForm').onsubmit=event=>{event.preventDefault();run(async()=>{
  const query=new URLSearchParams({start:$('reportStart').value,end:$('reportEnd').value});
  const report=await api('/api/report?'+query);
  $('reportTable').innerHTML=report.rows.map(r=>`<tr><td>${safe(r.name)}</td><td>${r.sessions}</td><td>${r.minutes}</td><td>${number(r.kwh,6)}</td><td>${r.points}</td></tr>`).join('')||empty(5);
  $('reportDownload').href='/api/report.csv?'+query;$('reportDownload').classList.remove('hidden');
});};
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
$('reportEnd').value=today;$('reportStart').value=today.slice(0,7)+'-01';
api('/api/state').then(data=>{state=data;enterApp();}).catch(error=>{if(error.message!=='Entre novamente no sistema.')$('loginError').textContent=error.message;});
