export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { s } = req.query;
  if (!s) return res.status(400).json({ error: 'symbol required' });
  try {
    const sym = s.replace('.', '-');
    const url = `https://query2.finance.yahoo.com/v10/finance/quoteSummary/${sym}?modules=financialData,recommendationTrend,price,summaryDetail`;
    const resp = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' }
    });
    const data = await resp.json();
    res.json(data);
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
}
