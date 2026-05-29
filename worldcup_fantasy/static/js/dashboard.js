// Dashboard: pulls points, leaderboard, fixtures, tournament and renders.
// Auto-refreshes every 30 seconds.

const PROGRESSION = [
  { key:"win",    label:"Group Win", pts:5  },
  { key:"r32",    label:"Round of 32", pts:8 },
  { key:"r16",    label:"Round of 16", pts:10 },
  { key:"qf",     label:"Quarter-final", pts:20 },
  { key:"sf",     label:"Semi-final", pts:30 },
  { key:"final",  label:"Final", pts:50 },
  { key:"winner", label:"Champions", pts:100 },
];

function renderStats(p){
  document.getElementById('statTotal').textContent = p.total;
  document.getElementById('statPlayers').textContent = p.player_points;
  document.getElementById('statBonus').textContent = '+' + p.progression_bonus;
  document.getElementById('statBacked').textContent =
    (window.flag ? window.flag(p.backed_nation) : '') + ' ' + (p.backed_nation || '—');
}

function renderProgression(p){
  document.getElementById('progNation').textContent = p.backed_nation || 'Your Nation';
  const achieved = new Set(p.progression_stages || []);
  document.getElementById('progressTrack').innerHTML = PROGRESSION.map(s => {
    const done = achieved.has(s.key);
    return `<div class="stage ${done ? 'done':''}">${s.label}<span class="pts">+${s.pts}</span></div>`;
  }).join('');
}

function renderBreakdown(p){
  const body = document.getElementById('breakdownBody');
  body.innerHTML = (p.breakdown || []).map(r => `
    <tr>
      <td>${(typeof flag==='function'?flag(r.nation):'')} ${r.name}
        ${r.multiplier > 1 ? '<span class="mult-badge">1.5×</span>' : ''}</td>
      <td><span class="pos-pill pos-${r.position}">${r.position}</span></td>
      <td>${r.goals}</td><td>${r.assists}</td><td>${r.clean_sheets}</td>
      <td><b>${r.points}</b></td>
    </tr>`).join('') || '<tr><td colspan="6" class="muted">No starters found.</td></tr>';
}

function renderLeaderboard(rows){
  const me = window.MY_USERNAME;
  const body = document.getElementById('leaderboardBody');
  body.innerHTML = rows.map(r => `
    <tr class="${r.username === me ? 'me':''}">
      <td class="rank">${r.rank}</td>
      <td>${r.username}</td>
      <td>${(typeof flag==='function'?flag(r.backed_nation):'')} ${r.backed_nation || '—'}</td>
      <td><b>${r.total}</b></td>
    </tr>`).join('') || '<tr><td colspan="4" class="muted">No managers yet.</td></tr>';
}

async function refresh(){
  try {
    const [points, lb, fixtures] = await Promise.all([
      fetch('/api/points').then(r=>r.json()),
      fetch('/api/leaderboard').then(r=>r.json()),
      fetch('/api/fixtures').then(r=>r.json()),
    ]);
    renderStats(points);
    renderProgression(points);
    renderBreakdown(points);
    renderLeaderboard(lb);
    renderFixtures(fixtures, points.backed_nation);
    document.getElementById('lastUpdate').textContent =
      'updated ' + new Date().toLocaleTimeString();
  } catch(e){
    console.error('refresh failed', e);
  }
}

refresh();
setInterval(refresh, 30000);
