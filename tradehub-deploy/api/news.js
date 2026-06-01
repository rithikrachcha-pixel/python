export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { s } = req.query;
  if (!s) return res.status(400).json({ error: 'symbol required' });
  try {
    const query = encodeURIComponent(s);
    const url = `https://news.google.com/rss/search?q=${query}+stock&hl=en-US&gl=US&ceid=US:en`;
    const resp = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/rss+xml' }
    });
    const xml = await resp.text();
    // Parse RSS items
    const items = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;
    while ((match = itemRegex.exec(xml)) !== null && items.length < 8) {
      const item = match[1];
      const title = (/<title><!\[CDATA\[(.*?)\]\]><\/title>/.exec(item) || /<title>(.*?)<\/title>/.exec(item) || [])[1] || '';
      const link  = (/<link>(.*?)<\/link>/.exec(item) || [])[1] || '';
      const pubDate = (/<pubDate>(.*?)<\/pubDate>/.exec(item) || [])[1] || '';
      const source = (/<source[^>]*>(.*?)<\/source>/.exec(item) || [])[1] || 'Google News';
      if (title) items.push({ title: title.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>'), link, pubDate, source });
    }
    res.json({ items });
  } catch (e) {
    res.status(502).json({ error: e.message });
  }
}
