const PROGRESSION = [
  { key: "win",    label: "Group Win",     pts: 5   },
  { key: "r32",    label: "Round of 32",   pts: 8   },
  { key: "r16",    label: "Round of 16",   pts: 10  },
  { key: "qf",     label: "Quarter-Final", pts: 20  },
  { key: "sf",     label: "Semi-Final",    pts: 30  },
  { key: "final",  label: "Final",         pts: 50  },
  { key: "winner", label: "🏆 Champions",  pts: 100 },
];

let myRank = '—';
let squadData = null;
let captainId = null;
let activeBooster = null;
let usedTripleCaptain = false;
let usedBenchBoost = false;

/* ─── Stats ──────────────────────────────────────────── */
function renderStats(p, lb){
  document.getElementById('statTotal').textContent = p.total;
  document.getElementById('statPlayers').textContent = p.player_points;
  document.getElementById('statBonus').textContent = '+' + p.progression_bonus;

  const me = window.MY_USERNAME;
  const row = lb.find(r => r.username === me);
  myRank = row ? row.rank : '—';
  document.getElementById('statRank').textContent = row ? '#' + row.rank : '—';
}

/* ─── Progression track ──────────────────────────────── */
function renderProgression(p){
  const nation = p.backed_nation || '—';
  const flagFn = typeof flag === 'function' ? flag : (n => '');
  document.getElementById('progNation').textContent = flagFn(nation) + ' ' + nation;
  const achieved = new Set(p.progression_stages || []);
  document.getElementById('progressTrack').innerHTML = PROGRESSION.map(s => {
    const done = achieved.has(s.key);
    return `<div class="stage ${done ? 'done' : ''}">
      ${s.label}<span class="pts">+${s.pts}</span>
    </div>`;
  }).join('');
  const bonusPts = p.progression_bonus;
  document.getElementById('progBacked').textContent = bonusPts > 0
    ? `${flagFn(nation)} ${nation} has earned ${bonusPts} bonus points so far.`
    : `${flagFn(nation)} ${nation} hasn't advanced yet — bonus points unlock as they progress.`;
}

/* ─── Breakdown table ────────────────────────────────── */
function renderBreakdown(p){
  const flagFn = typeof flag === 'function' ? flag : (n => '');
  const body = document.getElementById('breakdownBody');
  body.innerHTML = (p.breakdown || []).map(r => {
    const isCap = captainId && r.id === captainId;
    const capBadge = isCap ? `<span style="background:gold;color:#333;border-radius:50%;font-weight:700;font-size:.7rem;padding:1px 5px;margin-left:5px;">C</span>` : '';
    return `<tr class="breakdown-row">
      <td>
        <span>${flagFn(r.nation)}</span>
        <span style="font-weight:600;margin-left:5px;">${r.name}</span>
        ${r.multiplier > 1 ? '<span class="mult-badge">1.5×</span>' : ''}
        ${capBadge}
      </td>
      <td><span class="pos-pill pos-${r.position}">${r.position}</span></td>
      <td style="text-align:center;">${r.goals}</td>
      <td style="text-align:center;">${r.assists}</td>
      <td style="text-align:center;">${r.clean_sheets}</td>
      <td style="text-align:center;">${r.saves || 0}</td>
      <td><b style="color:var(--gold);font-family:'Oswald',sans-serif;font-size:1rem;">${r.points}</b></td>
    </tr>`;
  }).join('') || '<tr><td colspan="7" style="color:var(--text3);padding:24px;text-align:center;">No starters found.</td></tr>';
}

/* ─── Boosters ───────────────────────────────────────── */
function renderBoosters(){
  const container = document.getElementById('boostersList');
  if(!container) return;

  const boosters = [
    { key: 'triple_captain', label: '🚀 Triple Captain', desc: 'Your captain scores 3× points this gameweek', used: usedTripleCaptain },
    { key: 'bench_boost',    label: '🪑 Bench Boost',    desc: 'Your bench players also score points this gameweek', used: usedBenchBoost },
  ];

  container.innerHTML = `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:10px;">` +
    boosters.map(b => {
      const isActive = activeBooster === b.key;
      let statusLabel, disabled;
      if(isActive){
        statusLabel = '<span style="color:limegreen;font-weight:700;">✅ Active this GW</span>';
        disabled = true;
      } else if(b.used){
        statusLabel = '<span style="color:var(--text3);">Used</span>';
        disabled = true;
      } else {
        statusLabel = '<span style="color:#7ec8e3;">Available</span>';
        disabled = false;
      }
      return `<div style="background:var(--card-bg,#1a1a2e);border:1px solid var(--border,#333);border-radius:10px;padding:14px 18px;min-width:200px;flex:1;">
        <div style="font-weight:700;font-size:1rem;margin-bottom:4px;">${b.label}</div>
        <div style="font-size:.8rem;color:var(--text3);margin-bottom:10px;">${b.desc}</div>
        <div style="margin-bottom:10px;">${statusLabel}</div>
        <button class="btn sm${isActive || b.used ? ' ghost' : ''}" ${disabled ? 'disabled' : ''} onclick="activateBooster('${b.key}')">
          ${isActive ? 'Active' : b.used ? 'Used' : 'Activate'}
        </button>
      </div>`;
    }).join('') +
  `</div>`;
}

async function activateBooster(booster){
  try {
    const res = await fetch('/api/activate-booster', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({booster})
    });
    const data = await res.json();
    if(res.ok){
      activeBooster = data.active_booster;
      if(booster === 'triple_captain') usedTripleCaptain = true;
      if(booster === 'bench_boost') usedBenchBoost = true;
      renderBoosters();
      refresh();
    } else {
      alert(data.error || 'Could not activate booster.');
    }
  } catch(e){
    alert('Failed to activate booster.');
  }
}

/* ─── Leaderboard ────────────────────────────────────── */
function renderLeaderboard(rows){
  const me = window.MY_USERNAME;
  const flagFn = typeof flag === 'function' ? flag : (n => '');
  const body = document.getElementById('leaderboardBody');
  body.innerHTML = rows.map(r => {
    const rankClass = r.rank <= 3 ? `rank-${r.rank}` : '';
    const medal = r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : '';
    const isMe = r.username === me;
    return `<tr class="${isMe ? 'me' : ''}">
      <td class="rank ${rankClass}">${medal || r.rank}</td>
      <td style="font-weight:${isMe ? '700' : '500'};">${r.username}${isMe ? ' 👈' : ''}</td>
      <td style="font-size:.88rem;">${flagFn(r.backed_nation)} ${r.backed_nation || '—'}</td>
      <td><b style="color:var(--gold);font-family:'Oswald',sans-serif;">${r.total}</b></td>
    </tr>`;
  }).join('') || '<tr><td colspan="4" style="color:var(--text3);padding:24px;text-align:center;">No managers yet.</td></tr>';
}

/* ─── Refresh ────────────────────────────────────────── */
async function refresh(){
  try {
    const [points, lb, fixtures, squad] = await Promise.all([
      fetch('/api/points').then(r => r.json()),
      fetch('/api/leaderboard').then(r => r.json()),
      fetch('/api/fixtures').then(r => r.json()),
      fetch('/api/squad').then(r => r.json()),
    ]);

    // Sync captain/booster state from squad
    captainId = squad.captain_id || null;
    activeBooster = squad.active_booster || null;
    usedTripleCaptain = squad.used_triple_captain || false;
    usedBenchBoost = squad.used_bench_boost || false;

    renderStats(points, lb);
    renderProgression(points);
    renderBreakdown(points);
    renderBoosters();
    renderLeaderboard(lb);
    if(typeof renderFixtures === 'function'){
      renderFixtures(fixtures, points.backed_nation);
    }
    document.getElementById('lastUpdate').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch(e){
    console.error('Refresh failed', e);
    document.getElementById('lastUpdate').textContent = 'Update failed';
  }
}

refresh();
setInterval(refresh, 30000);
