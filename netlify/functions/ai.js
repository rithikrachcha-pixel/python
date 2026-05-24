exports.handler = async (event) => {
  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') return { statusCode: 200, headers: cors, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: cors, body: 'Method Not Allowed' };

  const serverKey = process.env.ANTHROPIC_API_KEY;
  let body;
  try { body = JSON.parse(event.body || '{}'); } catch { return { statusCode: 400, headers: cors, body: JSON.stringify({ error: 'Bad request' }) }; }

  const apiKey = serverKey || body.userKey;
  if (!apiKey) {
    return { statusCode: 503, headers: cors, body: JSON.stringify({ error: { message: 'AI service not configured. Add ANTHROPIC_API_KEY to Netlify env vars or enter your own key.' } }) };
  }

  try {
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({
        model: body.model || 'claude-haiku-4-5-20251001',
        max_tokens: Math.min(body.max_tokens || 1000, 2000),
        system: body.system,
        messages: body.messages,
      }),
    });
    const data = await resp.json();
    return { statusCode: resp.status, headers: cors, body: JSON.stringify(data) };
  } catch (err) {
    return { statusCode: 500, headers: cors, body: JSON.stringify({ error: { message: err.message } }) };
  }
};
