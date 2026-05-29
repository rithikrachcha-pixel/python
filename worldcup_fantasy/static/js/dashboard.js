const PROGRESSION = [
  { key:"win",    label:"Group Win",    pts:5   },
  { key:"r32",    label:"Round of 32",  pts:8   },
  { key:"r16",    label:"Round of 16",  pts:10  },
  { key:"qf",     label:"Quarter-Final",pts:20  },
  { key:"sf",     label:"Semi-Final",   pts:30  },
  { key:"final",  label:"Final",        pts:50  },
  { key:"winner", label:"🏆 Champions", pts:100 },
];

let myRank = '—';

function renderStats(p, lb){
  document.getElementById('statTotal').textContent = p.total;
  document.getElementById('statPlayers').textContent = p.player_points;
  document.getElementById('statBonus').textContent = '+' + p.progression_bonus;
  // find rank
  const me = window.MY_USERNAME;
  const row = lb.find(r => r.username === me);
  document.getElementById('statRank').textContent = row ? '#' + row.rank : '—';
}

function renderProgression(p){
  const nation = p.backed_nation || '—';
  document.getElementById('progNation').textContent = (typeof flag==='function' ? flag(nation) : '') + ' ' + nation;
  const achieved = new Set(p.progression_stages || []);
  document.getElementById('progressTrack').innerHTML = PROGRESSION.map(s => {
    const done = achieved.has(s.key);
    return `<div class="stage ${done ? 'done' : ''}">
      ${s.label}<span class="pts">+${s.pts}</span>
    </div>`;
  }).join('');
  const bonusPts = p.progression_bonus;
  document.getElementById('progBacked').textContent = bonusPts > 0
    ? `${nation} has earned ${bonusPts} bonus points so far.`
    : `${nation} hasn't advanced yet — bonus points unlock as they progress.`;
}

function renderBreakdown(p){
  const body = document.getElementById('breakdownBody');
  body.innerHTML = (p.breakdown || []).map(r => `
    <tr class="breakdown-row">
      <td>
        <span>${typeof flag==='function' ? flag(r.nation) : ''}</span>
        <span style="font-weight:600;margin-left:4px;">${r.name}</span>
        ${r.multiplier > 1 ? '<span class="mult-badge">1.5×</span>' : ''}
      </td>
      <td><span class="pos-pill pos-${r.position}">${r.position}</span></td>
      <td>${r.goals}</td>
      <td>${r.assists}</td>
      <td>${r.clean_sheets}</td>
      <td>${r.saves || 0}</td>
      <td><b style="color:var(--gold);font-family:'Oswald',sans-serif;font-size:1rem;">${r.points}</b></td>
    </tr>`).join('') || '<tr><td colspan="7" style="color:var(--text3);padding:20px;text-align:center;">No starters found.</td></tr>';
}

function renderLeaderboard(rows){
  const me = window.MY_USERNAME;
  const body = document.getElementById('leaderboardBody');
  body.innerHTML = rows.map(r => {
    const rankClass = r.rank <= 3 ? `rank-${r.rank}` : '';
    const medal = r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : '';
    return `<tr class="${r.username === me ? 'me' : ''}">
      <td class="rank ${rankClass}">${medal || r.rank}</td>
      <td style="font-weight:${r.username===me?'700':'500'};">${r.username}${r.username===me?' 👈':''}</td>
      <td style="font-size:.9rem;">${typeof flag==='function' ? flag(r.backed_nation) : ''} ${r.backed_nation || '—'}</td>
      <td><b style="color:var(--gold);font-family:'Oswald',sans-serif;">${r.total}</b></td>
    </tr>`;
  }).join('') || '<tr><td colspan="4" style="color:var(--text3);padding:20px;text-align:center;">No managers yet.</td></tr>';
}

async function refresh(){
  try {
    const [points, lb, fixtures] = await Promise.all([
      fetch('/api/points').then(r=>r.json()),
      fetch('/api/leaderboard').then(r=>r.json()),
      fetch('/api/fixtures').then(r=>r.json()),
    ]);
    renderStats(points, lb);
    renderProgression(points);
    renderBreakdown(points);
    renderLeaderboard(lb);
    renderFixtures(fixtures, points.backed_nation);
    document.getElementById('lastUpdate').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch(e){
    console.error('Refresh failed', e);
    document.getElementById('lastUpdate').textContent = 'Update failed';
  }
}

refresh();
setInterval(refresh, 30000);
