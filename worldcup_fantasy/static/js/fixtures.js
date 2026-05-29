// Shared flag map (mirrors team_builder.js) and fixtures renderer.
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

const STAGE_LABELS = {
  group: "Group Stage", r32: "Round of 32", r16: "Round of 16",
  qf: "Quarter-finals", sf: "Semi-finals", final: "Final"
};

function renderFixtures(fixtures, backedNation){
  const el = document.getElementById('fixtures');
  if(!fixtures.length){ el.innerHTML = '<p class="muted">No fixtures yet.</p>'; return; }

  const byStage = {};
  fixtures.forEach(f => (byStage[f.stage] = byStage[f.stage] || []).push(f));

  let html = '';
  Object.keys(STAGE_LABELS).forEach(stage => {
    const list = byStage[stage];
    if(!list) return;
    // show at most 12 per stage to keep the panel tidy
    html += `<div class="fx-stage-title">${STAGE_LABELS[stage]}</div>`;
    list.slice(0, 12).forEach(f => {
      const backed = backedNation && (f.home_team === backedNation || f.away_team === backedNation);
      const result = f.played
        ? `<span class="score">${f.home_score} – ${f.away_score}</span>`
        : `<span class="date">${f.match_date}</span>`;
      html += `<div class="fixture ${backed ? 'backed':''}">
        <span class="teams">${flag(f.home_team)} ${f.home_team}</span>
        ${result}
        <span class="teams">${f.away_team} ${flag(f.away_team)}</span>
      </div>`;
    });
  });
  el.innerHTML = html;
}
