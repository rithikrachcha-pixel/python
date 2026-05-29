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
window.flag = window.flag || flag;

const STAGE_LABELS = {
  group: "⚽ Group Stage", r32: "🔥 Round of 32", r16: "🔥 Round of 16",
  qf: "🔥 Quarter-finals", sf: "🔥 Semi-finals", final: "🏆 Final"
};

function fmtDate(d){
  if(!d) return '';
  const dt = new Date(d + 'T12:00:00Z');
  return dt.toLocaleDateString('en-GB', {weekday:'short', day:'numeric', month:'short'});
}

function renderFixtures(fixtures, backedNation){
  const el = document.getElementById('fixtures');
  if(!fixtures || !fixtures.length){ el.innerHTML = '<p class="muted">No fixtures yet.</p>'; return; }

  // Group by date first (within group stage), then by stage
  const today = new Date().toISOString().slice(0,10);

  // Separate played vs upcoming
  const played = fixtures.filter(f => f.played);
  const upcoming = fixtures.filter(f => !f.played);

  // Find backed nation's matches
  const myMatches = fixtures.filter(f =>
    backedNation && (f.home_team === backedNation || f.away_team === backedNation)
  );

  let html = '';

  // ── Backed nation matches first ──
  if(myMatches.length && backedNation){
    html += `<div class="fx-stage-title">🌟 ${flag(backedNation)} ${backedNation}'s Fixtures</div>`;
    myMatches.forEach(f => {
      html += fixtureHtml(f, backedNation, true);
    });
    html += '<div class="divider"></div>';
  }

  // ── Recent results ──
  if(played.length){
    html += `<div class="fx-stage-title">✅ Recent Results</div>`;
    played.slice(-6).reverse().forEach(f => {
      html += fixtureHtml(f, backedNation, false);
    });
    html += '<div class="divider"></div>';
  }

  // ── Upcoming by date ──
  const byDate = {};
  upcoming.forEach(f => {
    const d = f.match_date || 'TBC';
    (byDate[d] = byDate[d] || []).push(f);
  });

  const sortedDates = Object.keys(byDate).sort();
  const showDates = sortedDates.slice(0, 4); // show next 4 match days

  if(showDates.length){
    html += `<div class="fx-stage-title">📅 Upcoming Fixtures</div>`;
    showDates.forEach(date => {
      html += `<div style="font-size:.75rem;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:1px;margin:10px 0 6px;padding-left:4px;">${fmtDate(date)}</div>`;
      byDate[date].forEach(f => html += fixtureHtml(f, backedNation, false));
    });
  }

  el.innerHTML = html || '<p class="muted">No fixtures.</p>';
}

function fixtureHtml(f, backedNation, highlight){
  const backed = highlight || (backedNation && (f.home_team === backedNation || f.away_team === backedNation));
  const scoreHtml = f.played
    ? `<span class="score">${f.home_score} – ${f.away_score}</span>`
    : `<span class="vs">vs</span>`;
  return `<div class="fixture ${backed ? 'backed' : ''}">
    <span class="teams">${flag(f.home_team)} <span>${f.home_team}</span></span>
    ${scoreHtml}
    <span class="teams"><span>${f.away_team}</span> ${flag(f.away_team)}</span>
  </div>`;
}
