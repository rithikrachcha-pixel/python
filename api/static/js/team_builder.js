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
window.flag = flag;

const FORMATIONS = {
  "4-3-3": {DEF:4, MID:3, FWD:3},
  "4-4-2": {DEF:4, MID:4, FWD:2},
  "3-5-2": {DEF:3, MID:5, FWD:2},
  "3-4-3": {DEF:3, MID:4, FWD:3},
  "5-3-2": {DEF:5, MID:3, FWD:2},
};
const BUDGET = 150.0;

const state = {
  all: [],
  byId: {},
  formation: "4-3-3",
  posFilter: "ALL",
  starting: { GK:[], DEF:[], MID:[], FWD:[] },
  bench: [],
  picked: new Set(),
};

/* ─── Helpers ────────────────────────────────────────── */
function msg(text, ok){
  const el = document.getElementById('msg');
  el.textContent = text;
  el.className = text ? ('msg ' + (ok ? 'ok' : 'err')) : 'msg';
}

function updatePriceLabel(){
  const maxV = parseFloat(document.getElementById('maxPrice').value);
  const minV = parseFloat(document.getElementById('minPrice').value);
  document.getElementById('maxPriceLabel').textContent = `≤ $${maxV.toFixed(1)}M`;
  document.getElementById('minPriceLabel').textContent = `$${minV.toFixed(1)}M`;
}

function totalCost(){
  let c = 0;
  state.picked.forEach(id => c += state.byId[id].price);
  return Math.round(c * 10) / 10;
}

function canAddToStarting(pos){
  if (pos === 'GK') return state.starting.GK.length < 1;
  return state.starting[pos].length < FORMATIONS[state.formation][pos];
}

/* ─── Init ───────────────────────────────────────────── */
async function init(){
  const [players, nations] = await Promise.all([
    fetch('/api/players').then(r => r.json()),
    fetch('/api/nations').then(r => r.json()),
  ]);
  state.all = players;
  players.forEach(p => state.byId[p.id] = p);

  const nf = document.getElementById('nationFilter');
  const bn = document.getElementById('backedNation');
  nations.forEach(n => {
    nf.insertAdjacentHTML('beforeend', `<option value="${n.nation}">${flag(n.nation)} ${n.nation}</option>`);
    bn.insertAdjacentHTML('beforeend', `<option value="${n.nation}">${flag(n.nation)} ${n.nation} (Group ${n.group})</option>`);
  });
  bn.addEventListener('change', updateSaveState);
  updatePriceLabel();
  renderMarket();
  renderPitch();
  updateSaveState();
}

/* ─── Formation ──────────────────────────────────────── */
function setFormation(f){
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

/* ─── Position filter ────────────────────────────────── */
function setPosFilter(p){
  state.posFilter = p;
  document.querySelectorAll('[data-pos]').forEach(c =>
    c.classList.toggle('active', c.dataset.pos === p));
  renderMarket();
}

/* ─── Add / Remove player ────────────────────────────── */
function addPlayer(id){
  if(state.picked.has(id)) return;
  const p = state.byId[id];
  const cost = totalCost() + p.price;
  if(cost > BUDGET){
    msg(`Over budget — that would cost $${cost.toFixed(1)}M / $${BUDGET}M.`);
    return;
  }
  if(canAddToStarting(p.position)){
    state.starting[p.position].push(id);
  } else if(state.bench.length < 3){
    state.bench.push(id);
  } else {
    msg(`No free ${p.position} slot in this formation and bench is full.`);
    return;
  }
  state.picked.add(id);
  msg('');
  renderPitch(); renderMarket(); updateSaveState();
}

function removePlayer(id){
  ['GK','DEF','MID','FWD'].forEach(pos => {
    state.starting[pos] = state.starting[pos].filter(x => x !== id);
  });
  state.bench = state.bench.filter(x => x !== id);
  state.picked.delete(id);
  msg('');
  renderPitch(); renderMarket(); updateSaveState();
}

/* ─── Pitch rendering ────────────────────────────────── */
function slotHtml(id){
  const p = state.byId[id];
  const lastName = p.name.split(' ').slice(-1)[0];
  return `<div class="slot" title="${p.name} · ${p.nation} · $${p.price.toFixed(1)}M">
    <button class="remove-btn" onclick="removePlayer(${id})">×</button>
    <span class="flag-big">${flag(p.nation)}</span>
    <span class="nm">${lastName}</span>
    <span class="pr">$${p.price.toFixed(1)}M</span>
  </div>`;
}
function emptySlot(pos){
  return `<div class="slot empty">
    <span style="font-size:1.1rem;opacity:.45;">+</span>
    <span style="margin-top:3px;font-size:.65rem;">${pos}</span>
  </div>`;
}

function renderPitch(){
  const need = FORMATIONS[state.formation];
  const pitch = document.getElementById('pitch');
  const lineup = [['FWD', need.FWD], ['MID', need.MID], ['DEF', need.DEF], ['GK', 1]];
  pitch.innerHTML = lineup.map(([pos, n]) => {
    let cells = state.starting[pos].map(slotHtml);
    while(cells.length < n) cells.push(emptySlot(pos));
    return `<div class="pitch-row">${cells.join('')}</div>`;
  }).join('');

  const benchRow = document.getElementById('benchRow');
  let bcells = state.bench.map(slotHtml);
  while(bcells.length < 3) bcells.push(emptySlot('SUB'));
  benchRow.innerHTML = bcells.join('');

  const cost = totalCost();
  const remaining = Math.max(0, BUDGET - cost);
  document.getElementById('budgetUsed').textContent = `$${cost.toFixed(1)}M`;
  document.getElementById('budgetRemaining').textContent = `$${remaining.toFixed(1)}M`;
  document.getElementById('squadCount').textContent = state.picked.size;
  const bar = document.getElementById('budgetBar');
  bar.querySelector('span').style.width = Math.min(100, (cost / BUDGET) * 100) + '%';
  bar.classList.toggle('over', cost > BUDGET);
}

/* ─── Market rendering ───────────────────────────────── */
function renderMarket(){
  const search = (document.getElementById('search').value || '').toLowerCase().trim();
  const nation = document.getElementById('nationFilter').value;
  const sort = document.getElementById('sortSelect').value;
  const maxPrice = parseFloat(document.getElementById('maxPrice').value);
  const minPrice = parseFloat(document.getElementById('minPrice').value);
  const affordableOnly = document.getElementById('affordableToggle') && document.getElementById('affordableToggle').checked;

  const remaining = BUDGET - totalCost();

  let rows = state.all.filter(p => {
    if(state.posFilter !== 'ALL' && p.position !== state.posFilter) return false;
    if(nation && p.nation !== nation) return false;
    if(search && !p.name.toLowerCase().includes(search) && !p.nation.toLowerCase().includes(search)) return false;
    if(p.price > maxPrice) return false;
    if(p.price < minPrice) return false;
    if(affordableOnly && !state.picked.has(p.id) && p.price > remaining) return false;
    return true;
  });

  if(sort === 'price_desc') rows.sort((a,b) => b.price - a.price);
  else if(sort === 'price_asc') rows.sort((a,b) => a.price - b.price);
  else if(sort === 'name_asc') rows.sort((a,b) => a.name.localeCompare(b.name));
  else if(sort === 'points_desc') rows.sort((a,b) => (b.points||0) - (a.points||0));

  const total = rows.length;
  rows = rows.slice(0, 400);

  const body = document.getElementById('marketBody');
  body.innerHTML = rows.map(p => {
    const picked = state.picked.has(p.id);
    const affordable = totalCost() + p.price <= BUDGET;
    const dim = !picked && !affordable;
    return `<tr class="${picked ? 'picked' : ''}" style="${dim ? 'opacity:.45;' : ''}">
      <td>
        <span style="font-size:.95rem;">${flag(p.nation)}</span>
        <span style="font-weight:600;margin-left:5px;">${p.name}</span>
      </td>
      <td><span class="pos-pill pos-${p.position}">${p.position}</span></td>
      <td style="color:var(--text3);font-size:.81rem;">${p.club || '—'}</td>
      <td><span class="price-tag">$${p.price.toFixed(1)}M</span></td>
      <td>${picked
        ? `<button class="btn sm red" onclick="removePlayer(${p.id})">✕</button>`
        : `<button class="btn sm ${dim ? 'ghost' : ''}" onclick="addPlayer(${p.id})" ${dim ? 'title="Not enough budget"' : ''}>+ Add</button>`
      }</td>
    </tr>`;
  }).join('') || `<tr><td colspan="5" style="color:var(--text3);padding:24px;text-align:center;">No players match your filters.</td></tr>`;

  document.getElementById('marketCount').textContent = `Showing ${rows.length} of ${total} players`;
}

/* ─── Save state ─────────────────────────────────────── */
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
  const btn = document.getElementById('saveBtn');
  const complete = squadComplete() && backed;
  btn.disabled = !complete;

  if(complete){
    btn.textContent = '🔒 Lock In Squad & Start Playing';
    return;
  }

  const need = FORMATIONS[state.formation];
  const gkMissing = 1 - state.starting.GK.length;
  const defMissing = need.DEF - state.starting.DEF.length;
  const midMissing = need.MID - state.starting.MID.length;
  const fwdMissing = need.FWD - state.starting.FWD.length;
  const benchMissing = 3 - state.bench.length;
  const totalMissing = gkMissing + defMissing + midMissing + fwdMissing + benchMissing;

  if(totalMissing > 0){
    btn.textContent = `Pick ${totalMissing} more player${totalMissing > 1 ? 's' : ''}`;
  } else if(!backed){
    btn.textContent = 'Select a nation to back';
  } else {
    btn.textContent = '🔒 Lock In Squad';
  }
}

/* ─── Save squad ─────────────────────────────────────── */
async function saveSquad(){
  const backed = document.getElementById('backedNation').value;
  const starting_ids = [
    ...state.starting.GK,
    ...state.starting.DEF,
    ...state.starting.MID,
    ...state.starting.FWD
  ];
  const btn = document.getElementById('saveBtn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  const res = await fetch('/api/squad', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      starting_ids,
      bench_ids: state.bench,
      formation: state.formation,
      backed_nation: backed
    })
  });
  const data = await res.json();
  if(res.ok){
    window.location = '/dashboard';
  } else {
    msg(data.error || 'Could not save squad.');
    btn.disabled = false;
    updateSaveState();
  }
}

init();
