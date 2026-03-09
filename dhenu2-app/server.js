// ─── AGRIRITHM SERVER ─────────────────────────────────────────────────────────
// Run: npm install && node server.js
// Open: http://localhost:3000
// Debug: http://localhost:3000/api/debug  ← run this first if something breaks

import express from 'express';
import cors    from 'cors';
import fetch   from 'node-fetch';
import path    from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();

// ── CONFIG — CHANGE MODEL NAME HERE IF NEEDED ─────────────────────────────────
const PORT       = 3000;
const OLLAMA_URL = 'http://127.0.0.1:11434/api/generate';
const OLLAMA_TAG = 'http://127.0.0.1:11434/api/tags';
const MODEL      = 'dhenu2-farming:latest';  // ← must match exactly: run "ollama list" to verify

const LANG_INFO = {
  ta: { name:'Tamil',     speech:'ta-IN', tts:'ta-IN' },
  te: { name:'Telugu',    speech:'te-IN', tts:'te' },
  kn: { name:'Kannada',   speech:'kn-IN', tts:'kn-IN' },
  ml: { name:'Malayalam', speech:'ml-IN', tts:'ml-IN' },
  hi: { name:'Hindi',     speech:'hi-IN', tts:'hi-IN' },
  mr: { name:'Marathi',   speech:'mr-IN', tts:'mr-IN' },
  bn: { name:'Bengali',   speech:'bn-IN', tts:'bn-IN' },
  pa: { name:'Punjabi',   speech:'pa-IN', tts:'pa-IN' },
  en: { name:'English',   speech:'en-IN', tts:'en-IN' },
};

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── GOOGLE TRANSLATE ──────────────────────────────────────────────────────────
async function googleTranslate(text, sourceLang, targetLang) {
  if (!text?.trim() || sourceLang === targetLang) return { text, detectedLang: sourceLang };
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceLang||'auto'}&tl=${targetLang}&dt=t&dt=ld&q=${encodeURIComponent(text)}`;
    const res  = await fetch(url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`Google Translate HTTP ${res.status}`);
    const data = await res.json();
    const translated   = data[0].map(s => s[0]).join('').trim();
    const detectedLang = data[8]?.[0]?.[0] || data[2] || sourceLang;
    return { text: translated, detectedLang };
  } catch (err) {
    console.error('[TRANSLATE ERROR]', err.message);
    return { text, detectedLang: sourceLang };
  }
}

// ── LANGUAGE DETECT ───────────────────────────────────────────────────────────
async function detectLanguage(text) {
  try {
    const url  = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&dt=ld&q=${encodeURIComponent(text)}`;
    const res  = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const code = data[8]?.[0]?.[0] || data[2] || 'en';
    return { code, ...(LANG_INFO[code] || LANG_INFO['en']) };
  } catch (err) {
    console.error('[DETECT ERROR]', err.message);
    return { code: 'en', ...LANG_INFO['en'] };
  }
}

// ── GOOGLE TTS ────────────────────────────────────────────────────────────────
async function googleTTS(text, langCode) {
  const chunks  = splitChunks(text, 180);
  const buffers = [];
  for (const chunk of chunks) {
    if (!chunk.trim()) continue;
    try {
      const url = `https://translate.google.com/translate_tts?ie=UTF-8&q=${encodeURIComponent(chunk)}&tl=${langCode}&client=tw-ob&ttsspeed=0.9`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' },
        signal: AbortSignal.timeout(10000)
      });
      if (!res.ok) throw new Error(`TTS HTTP ${res.status}`);
      buffers.push(Buffer.from(await res.arrayBuffer()));
    } catch (err) {
      console.error('[TTS CHUNK ERROR]', err.message);
    }
  }
  return buffers.length ? Buffer.concat(buffers) : null;
}

function splitChunks(text, maxLen) {
  const sentences = text.split(/(?<=[.!?।\n])\s+/);
  const chunks = [];
  let cur = '';
  for (const s of sentences) {
    if ((cur + ' ' + s).length > maxLen) {
      if (cur) chunks.push(cur.trim());
      cur = s;
    } else {
      cur += (cur ? ' ' : '') + s;
    }
  }
  if (cur) chunks.push(cur.trim());
  return chunks.length ? chunks : [text.substring(0, maxLen)];
}

// ── OLLAMA CALL ───────────────────────────────────────────────────────────────
async function askOllama(prompt) {
  console.log(`[OLLAMA] → POST ${OLLAMA_URL}`);
  console.log(`[OLLAMA] model: "${MODEL}"`);
  console.log(`[OLLAMA] prompt: "${prompt.substring(0,100)}..."`);

  const body = JSON.stringify({
    model:  MODEL.trim(),
    prompt: `You are Agririthm, an expert agricultural AI assistant for Indian farmers.
Give practical, clear, and helpful farming advice in 3-5 sentences.
Answer directly and specifically. Do not include greetings or repeat the question.

Farmer question: ${prompt}`,
    stream: false,
    options: { temperature: 0.7, num_predict: 300 }
  });

  const res = await fetch(OLLAMA_URL, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal: AbortSignal.timeout(120000)
  });

  console.log(`[OLLAMA] ← HTTP ${res.status}`);

  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`Ollama returned HTTP ${res.status}: ${errText || res.statusText}`);
  }

  const data = await res.json();
  const reply = (data.response || '').trim();
  console.log(`[OLLAMA] reply: "${reply.substring(0,100)}..."`);
  return reply;
}

// ── /api/debug ────────────────────────────────────────────────────────────────
// Visit http://localhost:3000/api/debug to test all connections
app.get('/api/debug', async (req, res) => {
  console.log('\n[DEBUG] Running full diagnostic...');
  const out = {};

  // 1. Ollama ping
  try {
    const r = await fetch('http://127.0.0.1:11434/', { signal: AbortSignal.timeout(3000) });
    const t = await r.text();
    out.step1_ollama_ping = { ok: true, response: t.trim() };
  } catch(e) {
    out.step1_ollama_ping = { ok: false, error: e.message, fix: 'Run: ollama serve' };
  }

  // 2. List models
  try {
    const r = await fetch(OLLAMA_TAG, { signal: AbortSignal.timeout(3000) });
    const d = await r.json();
    const models = d.models?.map(m => m.name) || [];
    const hasModel = models.some(m => m.startsWith(MODEL.split(':')[0]));
    out.step2_model_list = {
      ok: true,
      models,
      looking_for: MODEL,
      found: hasModel,
      fix: hasModel ? null : `Model "${MODEL}" not found. Run: ollama pull ${MODEL} OR change MODEL in server.js to one of: ${models.join(', ')}`
    };
  } catch(e) {
    out.step2_model_list = { ok: false, error: e.message };
  }

  // 3. Test generate
  try {
    const r = await fetch(OLLAMA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: MODEL, prompt: 'Reply with just: OK', stream: false }),
      signal: AbortSignal.timeout(30000)
    });
    if (!r.ok) {
      const t = await r.text();
      throw new Error(`HTTP ${r.status}: ${t}`);
    }
    const d = await r.json();
    out.step3_generate = { ok: true, response: d.response?.trim() };
  } catch(e) {
    out.step3_generate = { ok: false, error: e.message };
  }

  // 4. Google Translate
  try {
    const r = await googleTranslate('hello farmer', 'en', 'ta');
    out.step4_translate = { ok: true, result: r.text };
  } catch(e) {
    out.step4_translate = { ok: false, error: e.message };
  }

  console.log('[DEBUG RESULT]', JSON.stringify(out, null, 2));
  res.json(out);
});

// ── /api/chat ─────────────────────────────────────────────────────────────────
app.post('/api/chat', async (req, res) => {
  const { message } = req.body;
  if (!message?.trim()) return res.status(400).json({ error: 'Empty message' });

  console.log(`\n[CHAT] New message: "${message}"`);

  try {
    // 1. Detect language
    const langInfo = await detectLanguage(message);
    console.log(`[CHAT] Language: ${langInfo.name} (${langInfo.code})`);

    // 2. Translate input to English
    let englishText = message;
    if (langInfo.code !== 'en') {
      const r = await googleTranslate(message, langInfo.code, 'en');
      englishText = r.text;
      console.log(`[CHAT] Translated to EN: "${englishText}"`);
    }

    // 3. Ask Ollama
    const englishReply = await askOllama(englishText);

    // 4. Translate reply back
    let localReply = englishReply;
    if (langInfo.code !== 'en') {
      const r = await googleTranslate(englishReply, 'en', langInfo.code);
      localReply = r.text;
      console.log(`[CHAT] Translated reply to ${langInfo.name}: "${localReply.substring(0,80)}..."`);
    }

    res.json({
      reply:           localReply,
      originalReply:   langInfo.code !== 'en' ? englishReply : null,
      translatedInput: langInfo.code !== 'en' ? englishText  : null,
      detectedLang:    langInfo.name,
      langCode:        langInfo.code,
      speechLang:      langInfo.speech,
      ttsLang:         langInfo.tts,
    });

  } catch (err) {
    console.error('[CHAT ERROR]', err.message);
    res.status(500).json({
      error: err.message,
      tip: 'Run http://localhost:3000/api/debug to diagnose'
    });
  }
});

// ── /api/tts ──────────────────────────────────────────────────────────────────
app.post('/api/tts', async (req, res) => {
  const { text, lang } = req.body;
  if (!text?.trim()) return res.status(400).send('No text');
  console.log(`[TTS] "${text.substring(0,50)}" → ${lang}`);
  const audio = await googleTTS(text, lang || 'en-IN');
  if (!audio) return res.status(500).json({ error: 'TTS failed' });
  res.set({ 'Content-Type':'audio/mpeg', 'Content-Length':audio.length, 'Cache-Control':'no-cache' });
  res.send(audio);
});

// ── /api/detect ───────────────────────────────────────────────────────────────
app.post('/api/detect', async (req, res) => {
  const { text } = req.body;
  if (!text?.trim()) return res.json({ code:'en', ...LANG_INFO['en'] });
  res.json(await detectLanguage(text));
});

// ── /api/health ───────────────────────────────────────────────────────────────
app.get('/api/health', async (req, res) => {
  try {
    const r = await fetch('http://127.0.0.1:11434/', { signal: AbortSignal.timeout(3000) });
    const t = await r.text();
    res.json({ status:'ok', ollama: t.includes('running') ? 'online' : 'unknown', model: MODEL });
  } catch {
    res.json({ status:'ok', ollama:'offline', model: MODEL });
  }
});

// ── START ─────────────────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('  🌾  AGRIRITHM SERVER');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`  App    → http://localhost:${PORT}`);
  console.log(`  Debug  → http://localhost:${PORT}/api/debug`);
  console.log(`  Model  → ${MODEL}`);
  console.log(`  Ollama → ${OLLAMA_URL}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('\n  ⚡ Open /api/debug in browser to test connections\n');
});
