export const config = { runtime: 'edge' };

const otpStore = new Map(); // { email -> { code, expires } }

export default async function handler(req) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  const { action, email, code } = await req.json().catch(() => ({}));

  if (!email || !email.includes('@')) {
    return new Response(JSON.stringify({ error: 'Invalid email' }), {
      status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  // Verify existing OTP
  if (action === 'verify') {
    const stored = otpStore.get(email.toLowerCase());
    if (!stored) return new Response(JSON.stringify({ error: 'No code found — request a new one' }), {
      status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
    if (Date.now() > stored.expires) {
      otpStore.delete(email.toLowerCase());
      return new Response(JSON.stringify({ error: 'Code expired — request a new one' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
    if (stored.code !== String(code).trim()) {
      return new Response(JSON.stringify({ error: 'Incorrect code' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
    otpStore.delete(email.toLowerCase());
    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  // Generate and send OTP
  const otp = String(Math.floor(100000 + Math.random() * 900000));
  otpStore.set(email.toLowerCase(), { code: otp, expires: Date.now() + 10 * 60 * 1000 });

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    // No email service configured — return code directly for demo mode
    return new Response(JSON.stringify({ ok: true, demo: true, code: otp }), {
      status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'TradeForage <noreply@tradeforage.com>',
        to: [email],
        subject: 'Your TradeForage verification code',
        html: `
          <div style="background:#0a0c10;padding:40px 24px;font-family:sans-serif;color:#e0e0e0;max-width:480px;margin:0 auto;border-radius:12px">
            <div style="text-align:center;margin-bottom:28px">
              <img src="https://python-5ozq-git-main-rithikrachcha-pixels-projects.vercel.app/logo.png" width="120" style="border-radius:8px" alt="TradeForage"/>
              <div style="color:#d4a020;letter-spacing:2px;font-size:11px;margin-top:8px;text-transform:uppercase">Where Intelligence Meets Capital</div>
            </div>
            <h2 style="color:#fff;text-align:center;margin:0 0 8px">Verification Code</h2>
            <p style="color:#8b90a0;text-align:center;margin:0 0 28px;font-size:14px">Use this code to sign in to TradeForage. It expires in 10 minutes.</p>
            <div style="background:#12151c;border:1px solid #1e2230;border-radius:10px;padding:28px;text-align:center;margin-bottom:24px">
              <div style="font-size:40px;font-weight:700;letter-spacing:12px;color:#00e5a0;font-family:monospace">${otp}</div>
            </div>
            <p style="color:#555;font-size:12px;text-align:center">If you didn't request this, you can safely ignore this email.</p>
          </div>`,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    return new Response(JSON.stringify({ ok: true }), {
      status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Failed to send email: ' + e.message }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}
