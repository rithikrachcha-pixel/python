export const config = { runtime: 'edge' };

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });

// Stateless HMAC-OTP: deterministic from (email + 10-min time window + secret).
// No DB or Map needed — works across serverless invocations.
async function makeOTP(email, secret, windowOffset = 0) {
  const window = Math.floor(Date.now() / (10 * 60 * 1000)) + windowOffset;
  const msg = new TextEncoder().encode(email.toLowerCase() + ':' + window);
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = new Uint8Array(await crypto.subtle.sign('HMAC', key, msg));
  const num = ((sig[0] << 24) | (sig[1] << 16) | (sig[2] << 8) | sig[3]) & 0x7fffffff;
  return String(num % 1000000).padStart(6, '0');
}

export default async function handler(req) {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

  const body = await req.json().catch(() => ({}));
  const { action, email, code } = body;

  if (!email || !email.includes('@')) return json({ error: 'Invalid email' }, 400);

  const secret = process.env.RESEND_API_KEY || 'tf-demo-secret-2026';

  // ── VERIFY ──────────────────────────────────────────────────────────────
  if (action === 'verify') {
    const entered = String(code || '').trim();
    // Accept current window and the previous window (handles edge-of-window timing)
    const valid0 = await makeOTP(email, secret, 0);
    const valid1 = await makeOTP(email, secret, -1);
    if (entered !== valid0 && entered !== valid1) {
      return json({ error: 'Incorrect or expired code. Request a new one.' }, 400);
    }
    return json({ ok: true });
  }

  // ── SEND ─────────────────────────────────────────────────────────────────
  const otp = await makeOTP(email, secret, 0);
  const apiKey = process.env.RESEND_API_KEY;

  if (!apiKey) {
    // Demo mode — show code in response (no email sent)
    return json({ ok: true, demo: true, code: otp });
  }

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'TradeForage <onboarding@resend.dev>',
        to: [email],
        subject: `${otp} is your TradeForage verification code`,
        html: `
<div style="background:#0a0c10;padding:40px 24px;font-family:sans-serif;color:#e0e0e0;max-width:480px;margin:0 auto;border-radius:12px;border:1px solid #1e2230">
  <div style="text-align:center;margin-bottom:28px">
    <img src="https://python-5ozq-git-main-rithikrachcha-pixels-projects.vercel.app/logo.png"
         width="130" style="border-radius:10px" alt="TradeForage"/>
  </div>
  <h2 style="color:#fff;text-align:center;margin:0 0 8px;font-size:20px">Verification Code</h2>
  <p style="color:#8b90a0;text-align:center;margin:0 0 28px;font-size:14px">
    Use this code to access TradeForage. It expires in <strong style="color:#e0e0e0">10 minutes</strong>.
  </p>
  <div style="background:#12151c;border:1px solid #1e2230;border-radius:12px;padding:32px;text-align:center;margin-bottom:24px">
    <div style="font-size:44px;font-weight:700;letter-spacing:14px;color:#00e5a0;font-family:monospace;padding-left:14px">${otp}</div>
  </div>
  <p style="color:#555;font-size:12px;text-align:center;margin:0">
    If you didn't request this code, you can safely ignore this email.
  </p>
</div>`,
      }),
    });
    const resText = await res.text();
    if (!res.ok) throw new Error(resText);
    return json({ ok: true });
  } catch (e) {
    return json({ error: 'Failed to send email: ' + e.message }, 500);
  }
}
