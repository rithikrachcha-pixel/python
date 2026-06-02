import { createHmac } from 'node:crypto';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function makeOTP(email, secret, windowOffset = 0) {
  const win = Math.floor(Date.now() / (10 * 60 * 1000)) + windowOffset;
  const msg = email.toLowerCase() + ':' + win;
  const sig = createHmac('sha256', secret).update(msg).digest();
  const num = ((sig[0] << 24) | (sig[1] << 16) | (sig[2] << 8) | sig[3]) & 0x7fffffff;
  return String(num % 1000000).padStart(6, '0');
}

export default async function handler(req, res) {
  Object.entries(CORS).forEach(([k, v]) => res.setHeader(k, v));

  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: 'Method not allowed' }); return; }

  const { action, email, code } = req.body || {};
  if (!email || !email.includes('@')) { res.status(400).json({ error: 'Invalid email' }); return; }

  const secret = process.env.RESEND_API_KEY || 'tf-demo-secret-2026';

  if (action === 'verify') {
    const entered = String(code || '').trim();
    const valid0 = makeOTP(email, secret, 0);
    const valid1 = makeOTP(email, secret, -1);
    if (entered !== valid0 && entered !== valid1) {
      res.status(400).json({ error: 'Incorrect or expired code. Request a new one.' });
      return;
    }
    res.status(200).json({ ok: true });
    return;
  }

  const otp = makeOTP(email, secret, 0);
  const apiKey = process.env.RESEND_API_KEY;

  if (!apiKey) {
    res.status(200).json({ ok: true, demo: true, code: otp });
    return;
  }

  try {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'TradeForage <onboarding@resend.dev>',
        to: [email],
        subject: `${otp} is your TradeForage verification code`,
        html: `<div style="background:#0a0c10;padding:40px 24px;font-family:sans-serif;color:#e0e0e0;max-width:480px;margin:0 auto;border-radius:12px;border:1px solid #1e2230">
  <h2 style="color:#fff;text-align:center;margin:0 0 8px;font-size:20px">Verification Code</h2>
  <p style="color:#8b90a0;text-align:center;margin:0 0 28px;font-size:14px">Use this code to access TradeForage. It expires in <strong style="color:#e0e0e0">10 minutes</strong>.</p>
  <div style="background:#12151c;border:1px solid #1e2230;border-radius:12px;padding:32px;text-align:center;margin-bottom:24px">
    <div style="font-size:44px;font-weight:700;letter-spacing:14px;color:#00e5a0;font-family:monospace;padding-left:14px">${otp}</div>
  </div>
  <p style="color:#555;font-size:12px;text-align:center;margin:0">If you didn't request this code, you can safely ignore this email.</p>
</div>`,
      }),
    });
    const resText = await r.text();
    if (!r.ok) throw new Error(resText);
    res.status(200).json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: 'Failed to send email: ' + e.message });
  }
}
