// ---- Flag emoji helper (covers WC2026 nations) ----
const FLAGS = {
  "Mexico":"🇲🇽","South Africa":"🇿🇦","South Korea":"🇰🇷","Czechia":"🇨🇿",
  "Canada":"🇨🇦","Bosnia-Herzegovina":"🇧🇦","Qatar":"🇶🇦","Switzerland":"🇨🇭",
  "Brazil":"🇧🇷","Morocco":"🇲🇦","Haiti":"🇭🇹","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "United States":"🇺🇸","USA":"🇺🇸","Paraguay":"🇵🇾","Australia":"🇦🇺","Turkiye":"🇹🇷","Turkey":"🇹🇷",
  "Germany":"🇩🇪","Curacao":"🇨🇼","Ivory Coast":"🇨🇮","Ecuador":"🇪🇨",
  "Netherlands":"🇳🇱","Japan":"🇯🇵","Sweden":"🇸🇪","Tunisia":"🇹🇳",
  "Belgium":"🇧🇪","Egypt":"🇪🇬","Iran":"🇮🇷","New Zealand":"🇳🇿",
  "Spain":"🇪🇸","Cape Verde":"🇨🇻","Saudi Arabia":"🇸🇦","Uruguay":"🇺🇾",
  "France":"🇫🇷","Senegal":"🇸🇳","Iraq":"🇮🇶","Norway":"🇳🇴",
  "Argentina":"🇦🇷","Algeria":"🇩🇿","Austria":"🇦🇹","Jordan":"🇯🇴",
  "Portugal":"🇵🇹","Congo DR":"🇨🇩","Uzbekistan":"🇺🇿","Colombia":"🇨🇴",
  "England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croatia":"🇭🇷","Ghana":"🇬🇭","Panama":"🇵🇦"
};
const flag = n => FLAGS[n] || "🏳️";

const FORMATIONS = {
  "4-3-3": {DEF:4, MID:3, FWD:3},
  "4-4-2": {DEF:4, MID:4, FWD:2},
  "3-5-2": {DEF:3, MID:5, FWD:2},
  "3-4-3": {DEF:3, MID:4, FWD:3},
  "5-3-2": {DEF:5, MID:3, FWD:2},
};
const BUDGET = 100.0;

const state = {
  all: [],            // all players
  byId: {},
  formation: "4-3-3",
  posFilter: "ALL",
  starting: { GK:[], DEF:[], MID:[], FWD:[] },
  bench: [],          // array of player ids
  picked: new Set(),  // all picked ids
};

function msg(text, ok){
  const el = document.getElementById('msg');
  el.textContent = text; el.className = 'msg ' + (ok ? 'ok':'err');
  if(!text) el.className = 'msg';
}

async function init(){
  const [players, nations] = await Promise.all([
    fetch('/api/players').then(r=>r.json()),
    fetch('/api/nations').then(r=>r.json()),
  ]);
  state.all = players;
  players.forEach(p => state.byId[p.id] = p);

  const nf = document.getElementById('nationFilter');
  const bn = document.getElementById('backedNation');
  nations.forEach(n => {
    nf.insertAdjacentHTML('beforeend', `<option value="${n.nation}">${flag(n.nation)} ${n.nation}</option>`);
    bn.insertAdjacentHTML('beforeend', `<option value="${n.nation}">${flag(n.nation)} ${n.nation} (Grp ${n.group})</option>`);
  });
  bn.addEventListener('change', updateSaveState);
  renderMarket();
  renderPitch();
}

function setFormation(f){
  // Moving to a smaller line could orphan players; trim extras back to market.
  const need = FORMATIONS[f];
  ['DEF','MID','FWD'].forEach(pos => {
    while(state.starting[pos].length > need[pos]){
      const id = state.starting[pos].pop();
      state.picked.delete(id);
    }
  });
  state.formation = f;
  document.querySelectorAll('[data-formation]').forEach(c =>
    c.classList.toggle('active', c.dataset.formation === f));
  renderPitch(); renderMarket(); updateSaveState();
}

function setPosFilter(p){
  state.posFilter = p;
  document.querySelectorAll('[data-pos]').forEach(c =>
    c.classList.toggle('active', c.dataset.pos === p));
  renderMarket();
}

function totalCost(){
  let c = 0;
  state.picked.forEach(id => c += state.byId[id].price);
  return Math.round(c*10)/10;
}

function startingCount(){
  return state.starting.GK.length + state.starting.DEF.length +
         state.starting.MID.length + state.starting.FWD.length;
}

function canAddToStarting(pos){
  if(pos === 'GK') return state.starting.GK.length < 1;
  return state.starting[pos].length < FORMATIONS[state.formation][pos];
}

function addPlayer(id){
  if(state.picked.has(id)){ return; }
  const p = state.byId[id];
  const cost = totalCost() + p.price;
  if(cost > BUDGET){ msg(`That would cost $${cost.toFixed(1)}M — over the $100M budget.`); return; }

  if(canAddToStarting(p.position)){
    state.starting[p.position].push(id);
  } else if(state.bench.length < 3){
    state.bench.push(id);
  } else {
    msg(`No free slot for a ${p.position} in this formation, and the bench is full.`);
    return;
  }
  state.picked.add(id);
  msg('');
  renderPitch(); renderMarket(); updateSaveState();
}

function removePlayer(id){
  const p = state.byId[id];
  ['GK','DEF','MID','FWD'].forEach(pos => {
    state.starting[pos] = state.starting[pos].filter(x => x !== id);
  });
  state.bench = state.bench.filter(x => x !== id);
  state.picked.delete(id);
  msg('');
  renderPitch(); renderMarket(); updateSaveState();
}

function slotHtml(id){
  const p = state.byId[id];
  return `<div class="slot" title="${p.name}">
      <span class="x" onclick="removePlayer(${id})">×</span>
      <span class="nm">${flag(p.nation)} ${p.name.split(' ').slice(-1)[0]}</span>
      <span class="pr">$${p.price.toFixed(1)}M</span>
    </div>`;
}
function emptySlot(pos){
  return `<div class="slot empty">${pos}</div>`;
}

function renderPitch(){
  const need = FORMATIONS[state.formation];
  const pitch = document.getElementById('pitch');
  const rows = [];

  // FWD (top), MID, DEF, GK (bottom)
  const lineup = [
    ['FWD', need.FWD], ['MID', need.MID], ['DEF', need.DEF], ['GK', 1]
  ];
  lineup.forEach(([pos, n]) => {
    let cells = state.starting[pos].map(slotHtml);
    while(cells.length < n) cells.push(emptySlot(pos));
    rows.push(`<div class="pitch-row">${cells.join('')}</div>`);
  });
  pitch.innerHTML = rows.join('');

  // bench
  const benchRow = document.getElementById('benchRow');
  let bcells = state.bench.map(slotHtml);
  while(bcells.length < 3) bcells.push(emptySlot('SUB'));
  benchRow.innerHTML = bcells.join('');

  // summary + budget bar
  const cost = totalCost();
  document.getElementById('budgetUsed').textContent = `$${cost.toFixed(1)}M`;
  document.getElementById('squadCount').textContent = state.picked.size;
  const bar = document.getElementById('budgetBar');
  bar.querySelector('span').style.width = Math.min(100, (cost/BUDGET)*100) + '%';
  bar.classList.toggle('over', cost > BUDGET);
}

function renderMarket(){
  const search = (document.getElementById('search').value || '').toLowerCase();
  const nation = document.getElementById('nationFilter').value;
  const body = document.getElementById('marketBody');
  const rows = state.all.filter(p => {
    if(state.posFilter !== 'ALL' && p.position !== state.posFilter) return false;
    if(nation && p.nation !== nation) return false;
    if(search && !p.name.toLowerCase().includes(search)) return false;
    return true;
  }).slice(0, 300);

  body.innerHTML = rows.map(p => {
    const picked = state.picked.has(p.id);
    return `<tr>
      <td>${flag(p.nation)} ${p.name}</td>
      <td><span class="pos-pill pos-${p.position}">${p.position}</span></td>
      <td class="muted">${p.club || ''}</td>
      <td><b>$${p.price.toFixed(1)}</b></td>
      <td>${picked
        ? `<button class="btn sm red" onclick="removePlayer(${p.id})">Remove</button>`
        : `<button class="btn sm" onclick="addPlayer(${p.id})">Add</button>`}</td>
    </tr>`;
  }).join('') || `<tr><td colspan="5" class="muted">No players match.</td></tr>`;
}

function squadComplete(){
  const need = FORMATIONS[state.formation];
  return state.starting.GK.length === 1 &&
         state.starting.DEF.length === need.DEF &&
         state.starting.MID.length === need.MID &&
         state.starting.FWD.length === need.FWD &&
         state.bench.length === 3 &&
         totalCost() <= BUDGET;
}

function updateSaveState(){
  const backed = document.getElementById('backedNation').value;
  document.getElementById('saveBtn').disabled = !(squadComplete() && backed);
}

async function saveSquad(){
  const backed = document.getElementById('backedNation').value;
  const starting_ids = [...state.starting.GK, ...state.starting.DEF,
                        ...state.starting.MID, ...state.starting.FWD];
  const res = await fetch('/api/squad', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      starting_ids, bench_ids: state.bench,
      formation: state.formation, backed_nation: backed
    })
  });
  const data = await res.json();
  if(res.ok){ window.location = '/dashboard'; }
  else { msg(data.error || 'Could not save squad.'); }
}

init();
