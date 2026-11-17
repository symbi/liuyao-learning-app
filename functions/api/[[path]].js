const OWNER = 'symbi';
const REPO = 'liuyao-learning-app';
const API_VERSION = '2022-11-28';
const SESSION_COOKIE = '__Host-ly_session';

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers }
  });
}
function redirect(url, headers = {}) {
  return new Response(null, { status: 302, headers: { location: url, 'cache-control': 'no-store', ...headers } });
}
function cookieValue(request, name) {
  const cookies = request.headers.get('cookie') || '';
  const part = cookies.split(';').map(v => v.trim()).find(v => v.startsWith(name + '='));
  return part ? decodeURIComponent(part.slice(name.length + 1)) : null;
}
function setCookie(value, maxAge) {
  return `${SESSION_COOKIE}=${encodeURIComponent(value)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}
function clearCookie() {
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}
function randomHex(bytes = 32) {
  const data = new Uint8Array(bytes); crypto.getRandomValues(data);
  return [...data].map(v => v.toString(16).padStart(2, '0')).join('');
}
function base64Url(bytes) {
  let binary = ''; for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}
async function pkceChallenge(verifier) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}
function b64Utf8(text) {
  const bytes = new TextEncoder().encode(text); let binary = '';
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}
function decodeBase64Utf8(value) {
  const binary = atob(value.replace(/\n/g, ''));
  const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}
function dateIsValid(date) { if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false; const parsed = new Date(date + 'T00:00:00Z'); return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date; }
function recordPath(date) { return `daily-records/${date.slice(0, 4)}/${date.slice(5, 7)}/${date}.json`; }
async function githubFetch(path, token, init = {}) {
  return fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${token}`,
      'x-github-api-version': API_VERSION,
      'user-agent': 'liuyao-learning-app-phase1',
      ...(init.headers || {})
    }
  });
}
async function getSession(request, env) {
  const sid = cookieValue(request, SESSION_COOKIE);
  if (!sid) return null;
  const key = `session:${sid}`;
  const session = await env.SESSIONS.get(key, 'json');
  if (!session) return null;
  if (session.expiresAt < Date.now() + 60_000) {
    if (!session.refreshToken) return null;
    const refresh = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST', headers: { accept: 'application/json', 'content-type': 'application/json' },
      body: JSON.stringify({ client_id: env.GITHUB_APP_CLIENT_ID, client_secret: env.GITHUB_APP_CLIENT_SECRET, grant_type: 'refresh_token', refresh_token: session.refreshToken })
    });
    const refreshed = await refresh.json();
    if (!refresh.ok || !refreshed.access_token) { await env.SESSIONS.delete(key); return null; }
    session.accessToken = refreshed.access_token;
    session.refreshToken = refreshed.refresh_token || session.refreshToken;
    session.expiresAt = Date.now() + Number(refreshed.expires_in || 28800) * 1000;
    await env.SESSIONS.put(key, JSON.stringify(session), { expirationTtl: 60 * 60 * 24 * 30 });
  }
  return { ...session, sid, key };
}
async function handleLogin(request, env) {
  const state = randomHex();
  const verifier = randomHex(48);
  const challenge = await pkceChallenge(verifier);
  await env.SESSIONS.put(`oauth:${state}`, JSON.stringify({ verifier }), { expirationTtl: 600 });
  const url = new URL('https://github.com/login/oauth/authorize');
  url.searchParams.set('client_id', env.GITHUB_APP_CLIENT_ID);
  url.searchParams.set('redirect_uri', env.GITHUB_APP_REDIRECT_URI);
  url.searchParams.set('state', state);
  url.searchParams.set('code_challenge', challenge);
  url.searchParams.set('code_challenge_method', 'S256');
  return redirect(url.toString());
}
async function handleCallback(request, env) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  if (!code || !state) return json({ error: 'Missing OAuth code or state' }, 400);
  const stateKey = `oauth:${state}`;
  const oauthState = await env.SESSIONS.get(stateKey, 'json');
  await env.SESSIONS.delete(stateKey);
  if (!oauthState?.verifier) return json({ error: 'OAuth state expired or invalid' }, 400);
  const exchange = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST', headers: { accept: 'application/json', 'content-type': 'application/json' },
    body: JSON.stringify({ client_id: env.GITHUB_APP_CLIENT_ID, client_secret: env.GITHUB_APP_CLIENT_SECRET, code, redirect_uri: env.GITHUB_APP_REDIRECT_URI, code_verifier: oauthState.verifier })
  });
  const token = await exchange.json();
  if (!exchange.ok || !token.access_token) return json({ error: token.error_description || token.error || 'GitHub authorization failed' }, 401);
  const userResponse = await githubFetch('/user', token.access_token);
  const user = await userResponse.json();
  if (!userResponse.ok || user.login?.toLowerCase() !== (env.ALLOWED_GITHUB_LOGIN || OWNER).toLowerCase()) return json({ error: 'This GitHub account is not allowed to use this personal app' }, 403);
  const repoResponse = await githubFetch(`/repos/${OWNER}/${REPO}`, token.access_token);
  const repo = await repoResponse.json();
  if (!repoResponse.ok || repo.permissions?.push !== true) return json({ error: 'The authorized GitHub App must have write access to this repository' }, 403);
  const sid = randomHex();
  const session = {
    login: user.login,
    accessToken: token.access_token,
    refreshToken: token.refresh_token || null,
    expiresAt: Date.now() + Number(token.expires_in || 28800) * 1000
  };
  await env.SESSIONS.put(`session:${sid}`, JSON.stringify(session), { expirationTtl: 60 * 60 * 24 * 30 });
  return redirect('/', { 'set-cookie': setCookie(sid, 60 * 60 * 24 * 30) });
}
async function handleRecords(request, env, session, date) {
  if (!dateIsValid(date)) return json({ error: 'Invalid date; expected YYYY-MM-DD' }, 400);
  const path = recordPath(date);
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  const apiPath = `/repos/${OWNER}/${REPO}/contents/${encodedPath}`;
  if (request.method === 'GET') {
    const response = await githubFetch(apiPath, session.accessToken);
    if (response.status === 404) return json({ record: null, sha: null });
    const data = await response.json();
    if (!response.ok) return json({ error: data.message || 'Unable to read GitHub file' }, response.status);
    if (data.type !== 'file' || !data.content) return json({ error: 'Unexpected GitHub file response' }, 502);
    try { return json({ record: JSON.parse(decodeBase64Utf8(data.content)), sha: data.sha }); }
    catch { return json({ error: 'The saved daily JSON is invalid' }, 502); }
  }
  if (request.method === 'PUT') {
    const origin = request.headers.get('origin');
    if (origin && origin !== new URL(request.url).origin) return json({ error: 'Cross-origin write blocked' }, 403);
    const length = Number(request.headers.get('content-length') || 0);
    if (length > 1_000_000) return json({ error: 'Daily record is too large' }, 413);
    let body;
    try { body = await request.json(); } catch { return json({ error: 'Invalid JSON request body' }, 400); }
    const record = body?.record;
    if (!record || record.recordDate !== date || !Array.isArray(record.additionalQuestions)) return json({ error: 'Daily record structure is invalid' }, 400);
    if (record.dailyFortune && !Array.isArray(record.dailyFortune.lines)) return json({ error: 'Daily fortune casting is invalid' }, 400);
    const currentResponse = await githubFetch(apiPath, session.accessToken);
    let current = null;
    if (currentResponse.ok) current = await currentResponse.json();
    else if (currentResponse.status !== 404) return json({ error: 'Unable to check current GitHub file' }, currentResponse.status);
    const currentSha = current?.sha || null;
    if (currentSha !== (body.sha || null)) return json({ error: 'GitHub record changed since it was loaded. Reload and merge before saving.', conflict: true, currentSha }, 409);
    const payload = {
      message: `Update daily Liuyao record ${date}`,
      content: b64Utf8(JSON.stringify(record, null, 2)),
      ...(currentSha ? { sha: currentSha } : {})
    };
    const write = await githubFetch(apiPath, session.accessToken, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });
    const result = await write.json();
    if (!write.ok) return json({ error: result.message || 'GitHub save failed' }, write.status);
    return json({ saved: true, sha: result.content?.sha || null, commit: result.commit?.sha || null });
  }
  return json({ error: 'Method not allowed' }, 405, { allow: 'GET, PUT' });
}


async function handleListRecords(env, session) {
  // Resolve main to the latest commit, then retrieve its complete Git tree.
  const commitResponse = await githubFetch('/repos/' + OWNER + '/' + REPO + '/commits/main', session.accessToken);
  const commit = await commitResponse.json();
  if (!commitResponse.ok) return json({ error: commit.message || 'Unable to read GitHub commit' }, commitResponse.status);
  const treeSha = commit.commit?.tree?.sha;
  if (!treeSha) return json({ error: 'GitHub commit did not include a tree SHA' }, 502);

  const treeResponse = await githubFetch('/repos/' + OWNER + '/' + REPO + '/git/trees/' + encodeURIComponent(treeSha) + '?recursive=1', session.accessToken);
  const tree = await treeResponse.json();
  if (!treeResponse.ok) return json({ error: tree.message || 'Unable to list GitHub records' }, treeResponse.status);
  if (tree.truncated) return json({ error: 'The GitHub record tree is too large to list completely' }, 502);

  const files = (tree.tree || []).filter(entry =>
    entry.type === 'blob' &&
    /^daily-records\/\d{4}\/\d{2}\/\d{4}-\d{2}-\d{2}\.json$/.test(entry.path || '')
  );
  const records = [];
  let skippedFiles = 0;

  // Read a small batch at a time to avoid sending too many GitHub requests at once.
  for (let offset = 0; offset < files.length; offset += 8) {
    const batch = files.slice(offset, offset + 8);
    const results = await Promise.all(batch.map(async entry => {
      try {
        const response = await githubFetch('/repos/' + OWNER + '/' + REPO + '/git/blobs/' + encodeURIComponent(entry.sha), session.accessToken);
        const blob = await response.json();
        if (!response.ok || blob.encoding !== 'base64' || typeof blob.content !== 'string') return null;
        const parsed = JSON.parse(decodeBase64Utf8(blob.content));
        const match = entry.path.match(/^daily-records\/(\d{4})\/(\d{2})\/(\d{4}-\d{2}-\d{2})\.json$/);
        const date = match?.[3];
        if (!dateIsValid(date) || match[1] !== date.slice(0, 4) || match[2] !== date.slice(5, 7)) return null;

        const dayRecords = [];
        if (parsed?.dailyFortune && Array.isArray(parsed.dailyFortune.lines)) {
          dayRecords.push({
            ...parsed.dailyFortune,
            date,
            timezone: parsed.timezone || 'Asia/Tokyo',
            dailyMemo: parsed.dailyMemo || parsed.dailyFortune.dailyMemo || '',
            recordType: 'dailyFortune'
          });
        }
        if (Array.isArray(parsed?.additionalQuestions)) {
          parsed.additionalQuestions.forEach(item => {
            if (item && Array.isArray(item.lines)) {
              dayRecords.push({
                ...item,
                date,
                timezone: parsed.timezone || 'Asia/Tokyo',
                dailyMemo: parsed.dailyMemo || item.dailyMemo || '',
                recordType: 'additionalQuestion'
              });
            }
          });
        }
        return dayRecords;
      } catch {
        return null;
      }
    }));
    for (const result of results) {
      if (result) records.push(...result);
      else skippedFiles += 1;
    }
  }

  records.sort((a, b) =>
    String(b.date || '').localeCompare(String(a.date || '')) ||
    String(b.savedAt || '').localeCompare(String(a.savedAt || ''))
  );
  return json({ records, files: files.length, skippedFiles });
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname.replace(/^\/api\/?/, '');
  if (request.method === 'GET' && path === 'auth/login') return handleLogin(request, env);
  if (request.method === 'GET' && path === 'auth/callback') return handleCallback(request, env);
  if (request.method === 'POST' && path === 'auth/logout') {
    const sid = cookieValue(request, SESSION_COOKIE);
    if (sid) await env.SESSIONS.delete(`session:${sid}`);
    return json({ ok: true }, 200, { 'set-cookie': clearCookie() });
  }
  const session = await getSession(request, env);
  if (request.method === 'GET' && path === 'me') return json({ authenticated: !!session, login: session?.login || null });
  if (!session) return json({ error: 'Not authenticated' }, 401);
  if (request.method === 'GET' && path === 'records') return handleListRecords(env, session);
  const match = path.match(/^records\/(\d{4}-\d{2}-\d{2})$/);
  if (match) return handleRecords(request, env, session, match[1]);
  return json({ error: 'Not found' }, 404);
}