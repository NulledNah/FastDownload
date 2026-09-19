const T = {
  en: {
    sub: "Everything in one place, but FAST",
    search_ph: "Search for a song or video...",
    search: "Search",
    sort_rel: "Search relevance",
    sort_q_desc: "Audio quality (high \u2192 low)",
    sort_q_asc: "Audio quality (low \u2192 high)",
    sort_d_desc: "Duration (long \u2192 short)",
    sort_d_asc: "Duration (short \u2192 long)",
    ready: "Ready.",
    searching: "Searching...",
    search_failed: "Search failed: {err}",
    results: "{n} results. Click to watch, then download.",
    no_results: "No results.",
    select_hint: "Select a result to watch it here.",
    no_video: "No video selected",
    preview_loading: "Loading preview...",
    analyzing: "Analyzing BPM and key...",
    preview_unavailable: "Preview unavailable. Use \"Open on YouTube\".",
    open_yt: "Open on YouTube",
    download_fmt: "Download {fmt}",
    src_all: "All sources",
    src_youtube: "YouTube",
    src_soundcloud: "SoundCloud",
    src_archive: "archive.org (FLAC)",
    src_mono: "Monochrome (FLAC)",
    offline: "offline",
    update_ytdlp: "Update yt-dlp",
    updating_ytdlp: "Updating yt-dlp...",
    ytdlp_ok: "yt-dlp updated: {v}",
    ytdlp_fail: "yt-dlp update failed",
    quality: "Source: {q}",
    lossy_note: "lossy source - FLAC/WAV disabled",
    more_info: "Download for more info",
    fmt_unavailable: "Format {fmt} is not available for this source.",
    buffering: "Buffering...",
    err_drm: "DRM protected \u00b7 preview not available",
    err_unavailable: "Preview not available",
    folder: "Folder...",
    open_folder: "Open folder",
    save_hint: "Project not saved \u2014 save it to keep downloads in its folder.",
    downloading: "Downloading {fmt}: {title}",
    eta: "ETA {t}",
    converting: "Converting...",
    saved: "Saved: {path}",
    saved_hint: "File saved. Refresh FL Studio's browser to see it.",
    download_failed: "Download failed: {err}",
    download_busy: "Download already in progress.",
    to_dark: "Switch to dark mode",
    to_light: "Switch to light mode",
  },
  it: {
    sub: "Tutto in un posto, ma FAST",
    search_ph: "Cerca una canzone o un video...",
    search: "Cerca",
    sort_rel: "Accuratezza ricerca",
    sort_q_desc: "Qualit\u00e0 audio (alta \u2192 bassa)",
    sort_q_asc: "Qualit\u00e0 audio (bassa \u2192 alta)",
    sort_d_desc: "Durata (lunga \u2192 corta)",
    sort_d_asc: "Durata (corta \u2192 lunga)",
    ready: "Pronto.",
    searching: "Ricerca in corso...",
    search_failed: "Ricerca fallita: {err}",
    results: "{n} risultati. Clicca per guardare, poi scarica.",
    no_results: "Nessun risultato.",
    select_hint: "Seleziona un risultato per guardarlo qui.",
    no_video: "Nessun video selezionato",
    preview_loading: "Carico anteprima...",
    analyzing: "Analizzo BPM e tonalità...",
    preview_unavailable: "Anteprima non disponibile. Usa \"Apri su YouTube\".",
    open_yt: "Apri su YouTube",
    download_fmt: "Scarica {fmt}",
    src_all: "Tutte le fonti",
    src_youtube: "YouTube",
    src_soundcloud: "SoundCloud",
    src_archive: "archive.org (FLAC)",
    src_mono: "Monochrome (FLAC)",
    offline: "offline",
    update_ytdlp: "Aggiorna yt-dlp",
    updating_ytdlp: "Aggiorno yt-dlp...",
    ytdlp_ok: "yt-dlp aggiornato: {v}",
    ytdlp_fail: "Aggiornamento di yt-dlp fallito",
    quality: "Sorgente: {q}",
    lossy_note: "sorgente lossy - FLAC/WAV disattivati",
    more_info: "Scarica per pi\u00f9 info",
    fmt_unavailable: "Formato {fmt} non disponibile per questa fonte.",
    buffering: "Buffering...",
    err_drm: "protetto da DRM \u00b7 anteprima non disponibile",
    err_unavailable: "Anteprima non disponibile",
    folder: "Cartella...",
    open_folder: "Apri cartella",
    save_hint: "Progetto non salvato \u2014 salvalo per tenere i download nella sua cartella.",
    downloading: "Scarico {fmt}: {title}",
    eta: "ETA {t}",
    converting: "Conversione in corso...",
    saved: "Salvato: {path}",
    saved_hint: "File salvato. Aggiorna il browser di FL Studio per vederlo.",
    download_failed: "Download fallito: {err}",
    download_busy: "Download già in corso.",
    to_dark: "Passa alla modalità scura",
    to_light: "Passa alla modalità chiara",
  },
};

const MOON = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">'
  + '<path d="M20.7 13.3A8.5 8.5 0 1 1 10.7 3.3a6.6 6.6 0 0 0 10 10z" fill="currentColor"/></svg>';
const SUN = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" '
  + 'stroke="currentColor" stroke-width="2" stroke-linecap="round">'
  + '<circle cx="12" cy="12" r="4" fill="currentColor" stroke="none"/>'
  + '<path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M19.1 4.9l-1.5 1.5M6.4 17.6l-1.5 1.5"/></svg>';

let api=null, items=[], sel=-1, loadToken=0, polling=false, searchToken=0;

const SOURCES = [
  {v:'all', k:'src_all'},
  {v:'youtube', k:'src_youtube'},
  {v:'soundcloud', k:'src_soundcloud'},
  {v:'archive', k:'src_archive'},
  {v:'monochrome', k:'src_mono'},
];
let srcValue = 'all', srcStatus = null;
let lang = window.__lang || 'en', lastState = null, phKey = 'select_hint';

const $ = id => document.getElementById(id);
function setStatus(s){ $('status').textContent = s; }
function esc(s){ return String(s).replace(/[&<>"]/g,
  c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function t(k, p){
  let s = (T[lang] && T[lang][k]) || T.en[k] || k;
  if(p) for(const key in p) s = s.split('{' + key + '}').join(p[key]);
  return s;
}

function fmtBytes(n){
  if(n == null) return '';
  const u = ['B', 'KB', 'MB', 'GB'];
  let v = n, i = 0;
  while(v >= 1024 && i < u.length - 1){ v /= 1024; i++; }
  return v.toFixed(i === 0 ? 0 : 1) + ' ' + u[i];
}

function fmtEta(sec){
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  const mm = h ? String(m).padStart(2, '0') : String(m);
  return (h ? h + ':' : '') + mm + ':' + String(r).padStart(2, '0');
}

function renderStatus(s){
  if(!s || !s.msg){ setStatus(t('ready')); return; }
  if(s.state === 'downloading'){
    const title = (s.msg.p && s.msg.p.title) || '';
    if(s.phase === 'convert'){
      setStatus(t('converting') + (title ? ' \u00b7 ' + title : ''));
      return;
    }
    const p = Object.assign({}, s.msg.p, {
      fmt: String((s.msg.p && s.msg.p.fmt) || '').toUpperCase()});
    let line = t('downloading', p) + ' ' + Math.round(s.pct || 0) + '%';
    if(s.speed) line += ' \u00b7 ' + fmtBytes(s.speed) + '/s';
    if(s.eta != null) line += ' \u00b7 ' + t('eta', {t: fmtEta(s.eta)});
    setStatus(line);
  } else {
    setStatus(t(s.msg.k, s.msg.p));
  }
}

let toastTimer = 0;
function showToast(msg){
  const el = $('toast');
  el.textContent = msg;
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=> el.classList.remove('on'), 8000);
}
function hideToast(){
  clearTimeout(toastTimer);
  $('toast').classList.remove('on');
}

function setLocal(k, p){
  lastState = {state: 'idle', pct: 0, msg: {k: k, p: p || {}}};
  renderStatus(lastState);
}

function setPlaceholder(key){
  phKey = key;
  $('ph').textContent = t(key);
  $('ph').style.display = 'flex';
  $('load').classList.remove('on');
}

function updateDownloadLabel(){
  $('dl').textContent = t('download_fmt', {fmt: ($('fmt').value || 'wav').toUpperCase()});
}

let fmtToken = 0;
let rowQualities = [];
let rowMetas = [];
let view = [];                 // indici di `items` nell'ordine mostrato
let sortKey = 'relevance';     // relevance | quality_desc/asc | duration_desc/asc

function renderRowFmt(i, q){
  const el = document.querySelector('.row[data-i="' + i + '"] .f');
  if(!el) return;
  el.classList.remove('err');
  if(q === null || q === undefined){
    el.innerHTML = '<span class="mini"><i></i></span>';
    return;
  }
  if(q.error){
    el.innerHTML = '';
    el.classList.add('err');
    el.textContent = t(q.error === 'drm' ? 'err_drm' : 'err_unavailable');
    return;
  }
  const pills = q.lossless ? ['FLAC', 'WAV', 'MP3'] : ['MP3'];
  el.innerHTML = pills.map(p=>'<span class="pill">' + p + '</span>').join('');
}

function renderRowMeta(i, info){
  const el = document.querySelector('.row[data-i="' + i + '"] .m');
  if(!el) return;
  if(info === null || info === undefined){        // in corso
    el.classList.remove('hint');
    el.innerHTML = '<span class="mini"><i></i></span>';
    return;
  }
  const bits = [];
  if(info.bpm) bits.push(info.bpm + ' BPM');
  if(info.key) bits.push(info.key);
  if(info.camelot) bits.push(info.camelot);
  if(bits.length){
    el.classList.remove('hint');
    el.textContent = bits.join(' \u00b7 ');
  } else {
    el.classList.add('hint');
    el.textContent = t('more_info');
  }
}

function bufferedPct(){
  const v = $('yt');
  if(!v.duration || !v.buffered || !v.buffered.length) return 0;
  return Math.min(100, Math.round(v.buffered.end(v.buffered.length - 1) / v.duration * 100));
}

function setLoading(msg, pct){
  const el = $('load');
  if(msg === null){ el.classList.remove('on'); return; }
  el.classList.add('on');
  $('lmsg').textContent = msg || '';
  $('lfill').style.width = (pct == null ? 0 : pct) + '%';
}

async function loadFormats(){
  const my = ++fmtToken;
  const snapshot = items.slice();
  const payload = snapshot.map(r=>({id:r.id, url:r.url, source:r.source,
    title:r.title, bpm:r.bpm, key:r.key, camelot:r.camelot}));
  for(let round = 0; round < 40; round++){
    if(my !== fmtToken) return;
    let qs = [], ms = [];
    try{ qs = await api.qualities(payload); }
    catch(e){ return; }
    try{ ms = await api.row_meta(payload); }
    catch(e){ ms = []; }
    if(my !== fmtToken) return;
    (qs || []).forEach((q, i)=>{ rowQualities[i] = q; });
    (ms || []).forEach((m, i)=>{ rowMetas[i] = m; });
    const before = view.join(',');
    sortView();
    if(view.join(',') !== before) render();   // riordina solo se cambia
    paintRows();
    const pending = (qs || []).some(q=>!q) || (ms || []).some(m=>m === null);
    if(!pending) return;
    await new Promise(r=>setTimeout(r, 900));
  }
}

function applyQuality(q){  const sel = $('fmt');
  const lossless = !!(q && q.lossless);
  sel.querySelector('option[value=flac]').disabled = !lossless;
  sel.querySelector('option[value=wav]').disabled = !lossless;
  if(!lossless && (sel.value === 'flac' || sel.value === 'wav')) sel.value = 'mp3';
  let text = '';
  if(q && q.label){
    text = t('quality', {q: q.label + (q.abr ? ' ' + q.abr + ' kbps' : '')});
    if(!lossless) text += ' \u00b7 ' + t('lossy_note');
  }
  $('qbadge').textContent = text;
  updateDownloadLabel();
}

function applyI18n(){
  document.documentElement.setAttribute('lang', lang);
  document.querySelectorAll('[data-i18n]').forEach(el=> el.textContent = t(el.dataset.i18n));
  document.querySelectorAll('[data-i18n-ph]').forEach(el=> el.placeholder = t(el.dataset.i18nPh));
  if(sel < 0){ $('nowTitle').textContent = t('no_video'); $('nowChan').textContent = ''; }
  if($('ph').style.display !== 'none') $('ph').textContent = t(phKey);
  $('theme').title = t(document.documentElement.getAttribute('data-theme') === 'dark'
    ? 'to_light' : 'to_dark');
  renderStatus(lastState);
  if(items.length) renderList();
  renderSourceMenu();
  if($('upd').style.display !== 'none') $('upd').textContent = t('update_ytdlp');
  updateDownloadLabel();
}

function renderSourceMenu(){
  const st = srcStatus || {};
  const menu = $('srcmenu');
  menu.innerHTML = SOURCES.map(s=>{
    const off = s.v !== 'all' && st[s.v] === false;
    const sel = s.v === srcValue;
    return '<div class="srcopt' + (off ? ' off' : '') + (sel ? ' sel' : '')
      + '" data-v="' + s.v + '" role="option">'
      + '<span class="srcname">' + esc(t(s.k)) + '</span>'
      + (off ? '<span class="offbadge">' + esc(t('offline')) + '</span>' : '')
      + '</div>';
  }).join('');
  menu.querySelectorAll('.srcopt').forEach(el=>{
    el.onclick = ()=>{ if(el.classList.contains('off')) return; setSource(el.dataset.v); };
  });
  const cur = SOURCES.find(s=>s.v === srcValue) || SOURCES[0];
  const offCur = srcValue !== 'all' && st[srcValue] === false;
  $('srclabel').textContent = t(cur.k) + (offCur ? ' \u00b7 ' + t('offline') : '');
  $('srcbtn').classList.toggle('off', offCur);
}

function setSource(v){
  srcValue = v;
  $('srcpick').classList.remove('open');
  $('srcbtn').setAttribute('aria-expanded', 'false');
  renderSourceMenu();
  saveState(false);
}

async function refreshSources(){
  let st = null;
  try{ st = await api.sources_status(); }catch(e){ return; }
  if(!st || typeof st !== 'object') return;
  srcStatus = st;
  renderSourceMenu();
}

let projKey = null;
async function refreshProject(){
  let info = null;
  try{ info = await api.project_info(); }catch(e){ return; }
  if(!info) return;
  const key = (info.name || '') + '|' + (info.saved ? '1' : '0');
  if(key === projKey) return;                 // niente cambi: esci
  projKey = key;
  $('projwarn').classList.toggle('on', !info.saved);
  try{ $('folder').textContent = await api.get_folder(); }catch(e){}
}

async function refreshDeps(){
  let d = null;
  try{ d = await api.deps_info(); }catch(e){ return; }
  const btn = $('upd');
  if(!btn) return;
  if(d && d.stale){
    btn.style.display = '';
    btn.textContent = t('update_ytdlp');
    btn.title = t('update_ytdlp');
  } else {
    btn.style.display = 'none';
  }
}

async function updateYtdlp(){
  const btn = $('upd');
  if(btn.disabled) return;
  btn.disabled = true; btn.textContent = t('updating_ytdlp');
  let res = null;
  try{ res = await api.update_deps(); }catch(e){}
  btn.disabled = false;
  showToast(res && res.ok ? t('ytdlp_ok', {v: res.version || ''}) : t('ytdlp_fail'));
  refreshDeps();
}

function srcLabel(s){
  return s === 'soundcloud' ? 'SC' : s === 'archive' ? 'AR'
    : s === 'monochrome' ? 'MC' : 'YT';
}

function durSeconds(d){
  const m = /^(\d+):(\d{2})$/.exec(d || '');
  return m ? (+m[1]) * 60 + (+m[2]) : null;
}

function qualityScore(q){
  if(!q || q.error) return null;
  return q.lossless ? 100000 + (q.abr || 0) : (q.abr || 0);
}

function compareIdx(a, b, dir, keyFn){
  const va = keyFn(a), vb = keyFn(b);
  if(va === null && vb === null) return a - b;
  if(va === null) return 1;                 // dati mancanti in fondo
  if(vb === null) return -1;
  if(va === vb) return a - b;
  return dir < 0 ? vb - va : va - vb;
}

function sortView(){
  view = items.map((_, i)=>i);
  let keyFn = null;
  if(sortKey.startsWith('quality')) keyFn = i => qualityScore(rowQualities[i]);
  else if(sortKey.startsWith('duration')) keyFn = i => durSeconds(items[i].duration);
  if(keyFn){
    const dir = sortKey.endsWith('_asc') ? 1 : -1;
    view.sort((a, b)=> compareIdx(a, b, dir, keyFn));
  }
}

function paintRows(){
  items.forEach((_, i)=>{
    renderRowFmt(i, rowQualities[i]);
    renderRowMeta(i, rowMetas[i] === undefined ? null : rowMetas[i]);
  });
}

function renderList(){
  render();
  paintRows();
}

function snapshotState(){
  return {query: $('q').value, source: srcValue, sort: sortKey,
          fmt: $('fmt').value, sel: sel, items: items};
}

function saveState(beacon){
  const state = snapshotState();
  if(beacon && navigator.sendBeacon){
    try{
      navigator.sendBeacon('/api/save_state',
        new Blob([JSON.stringify({token: window.FD_TOKEN || '', state: state})],
                 {type: 'application/json'}));
      return;
    }catch(e){}
  }
  try{ api.save_state(state); }catch(e){}
}

let saveTimer = 0;
function scheduleSave(){                 // autosave: canale primario di persistenza
  clearTimeout(saveTimer);
  saveTimer = setTimeout(()=> saveState(false), 350);
}

function restoreState(st){
  if(!st || typeof st !== 'object') return;
  if(typeof st.query === 'string') $('q').value = st.query;
  if(SOURCES.some(s=> s.v === st.source)) srcValue = st.source;
  if(typeof st.sort === 'string' && /^(relevance|quality_|duration_)/.test(st.sort)){
    sortKey = st.sort; $('sort').value = st.sort;
  }
  if(['wav','flac','mp3'].indexOf(st.fmt) >= 0) $('fmt').value = st.fmt;
  renderSourceMenu();
  updateDownloadLabel();
  if(Array.isArray(st.items) && st.items.length){
    items = st.items;
    rowQualities = items.map(()=>null);
    rowMetas = items.map(()=>undefined);
    sortView();
    renderList();
    setLocal('results', {n: items.length});
    api.prefetch(items.map(r=>({id:r.id, url:r.url, source:r.source, title:r.title,
      bpm:r.bpm, key:r.key, camelot:r.camelot})));
    loadFormats();
    if(typeof st.sel === 'number' && st.sel >= 0 && st.sel < items.length){
      select(st.sel);        // ricarica l'anteprima in pausa (nessun autoplay)
    }
  }
}

function render(){
  const list = $('list');
  if(!items.length){ list.innerHTML = '<div class="empty">' + esc(t('no_results')) + '</div>'; return; }
  list.innerHTML = view.map(i => { const r = items[i]; return `
    <div class="row" data-i="${i}">
      <div class="t">${esc(r.title)}</div>
      <div class="src">${srcLabel(r.source)}</div>
      <div class="c">${esc(r.channel)}</div>
      <div class="d">${esc(r.duration)}</div>
      <div class="f"></div>
      <div class="m"></div>
    </div>`; }).join('');
  list.querySelectorAll('.row').forEach(el=> el.onclick = ()=> select(+el.dataset.i));
  if(sel >= 0){
    const el = list.querySelector('.row[data-i="' + sel + '"]');
    if(el) el.classList.add('active');
  }
}

async function select(i){
  sel = i;
  saveState(false);
  const r = items[i];
  document.querySelectorAll('.row[data-i]').forEach(el=>
    el.classList.toggle('active', +el.dataset.i === i));
  if(rowQualities[i]) applyQuality(rowQualities[i]);
  const v = $('yt');
  v.pause(); v.removeAttribute('src'); v.load();
  v.poster = r.thumb || '';
  $('ph').style.display = 'none';
  setLoading(t('preview_loading'), 0);
  $('nowTitle').textContent = r.title;
  $('nowChan').textContent = r.channel;
  $('dl').disabled = false;
  $('meta').textContent = t('analyzing');

  const token = ++loadToken;
  loadMeta(r, token);
  let res;
  try{ res = await api.resolve(r.id, r.url, r.source); }
  catch(e){ res = {url: ''}; }
  if(token !== loadToken) return;
  applyQuality(res && res.quality);
  if(res && res.url){
    v.src = res.url;
    v.load();
    $('ph').style.display = 'none';
  } else {
    setPlaceholder(res && res.error === 'drm' ? 'err_drm' : 'preview_unavailable');
  }
}

async function loadMeta(r, token){
  let m = {};
  try{ m = await api.meta(r.id, r.url, r.title, r.source) || {}; }catch(e){}
  if(token !== loadToken) return;
  const bits = [];
  if(m.bpm) bits.push(m.bpm + ' BPM');
  if(m.key) bits.push(m.key);
  if(m.camelot) bits.push(m.camelot);
  if(m.spotify_year) bits.push(m.spotify_year);
  if(m.spotify_title && !$('nowTitle').textContent) $('nowTitle').textContent = m.spotify_title;
  $('meta').textContent = bits.length ? bits.join(' \u00b7 ') : '';
}

async function doSearch(){
  const q = $('q').value.trim();
  if(!q) return;
  const btn = $('searchBtn');
  const my = ++searchToken;
  btn.disabled = true; btn.textContent = '...';
  setLocal('searching');
  $('results').classList.add('searching');
  const sources = srcValue === 'all'
    ? ['youtube', 'soundcloud', 'archive', 'monochrome'] : [srcValue];
  try{
    const res = await api.search(q, sources);
    if(Array.isArray(res)){
      items = res; sel = -1;
      rowQualities = res.map(()=>null);
      rowMetas = res.map(()=>undefined);
      sortView();
      renderList();
      const v=$('yt'); v.pause(); v.removeAttribute('src'); v.load();
      v.poster = '';
      setPlaceholder('select_hint');
      $('nowTitle').textContent = t('no_video');
      $('nowChan').textContent = '';
      $('meta').textContent = '';
      $('qbadge').textContent = '';
      $('dl').disabled = true;
      setLocal('results', {n: res.length});
      api.prefetch(res.map(r=>({id:r.id, url:r.url, source:r.source, title:r.title,
        bpm:r.bpm, key:r.key, camelot:r.camelot})));
      loadFormats();
      saveState(false);
    } else {
      const e = (res && res.error) || {k: 'search_failed', p: {err: ''}};
      lastState = {state: 'error', pct: 0, msg: e};
      renderStatus(lastState);
    }
  } catch(e){ setLocal('search_failed', {err: e}); }
  if(my === searchToken) $('results').classList.remove('searching');
  btn.disabled = false; btn.textContent = t('search');
}

async function doDownload(){
  if(sel < 0) return;
  const r = items[sel];
  $('dl').disabled = true;
  const res = await api.download(r.id, r.url, r.source, r.title, $('fmt').value);
  if(res && res.error){
    setStatus(t(res.error.k, res.error.p));
    $('dl').disabled = false;
  }
}

async function poll(){
  if(polling) return;
  polling = true;
  try{
    const s = await api.status();
    const was = lastState && lastState.state;
    lastState = s;
    if(s.state === 'done' && was !== 'done') showToast(t('saved_hint'));
    else if(s.state === 'downloading' && was !== 'downloading') hideToast();
    const pending = s.state === 'downloading' && s.phase !== 'convert' && !(s.pct > 0);
    document.querySelector('.bar').classList.toggle('pending', pending);
    $('bar').style.width = (pending ? 35 : (s.pct || 0)) + '%';
    renderStatus(s);
    if(s.state === 'done' || s.state === 'error') $('dl').disabled = sel < 0;
  } catch(e){}
  polling = false;
}

function applyTheme(tm){
  document.documentElement.setAttribute('data-theme', tm);
  try{ localStorage.setItem('fd-theme', tm); }catch(e){}
  $('theme').innerHTML = tm === 'dark' ? SUN : MOON;
  $('theme').title = t(tm === 'dark' ? 'to_light' : 'to_dark');
}

function applyLang(l){
  lang = l;
  try{ localStorage.setItem('fd-lang', l); }catch(e){}
  $('lang').textContent = l.toUpperCase();
  applyI18n();
}

async function boot(){
  $('folder').textContent = await api.get_folder();
  $('lang').textContent = lang.toUpperCase();
  $('lang').onclick = ()=> applyLang(lang === 'en' ? 'it' : 'en');
  $('theme').onclick = ()=> applyTheme(
    document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  $('upd').onclick = updateYtdlp;
  $('searchBtn').onclick = doSearch;
  $('srcbtn').onclick = (e)=>{
    e.stopPropagation();
    const open = $('srcpick').classList.toggle('open');
    $('srcbtn').setAttribute('aria-expanded', open ? 'true' : 'false');
    if(open) refreshSources();
  };
  document.addEventListener('click', ()=>{
    $('srcpick').classList.remove('open');
    $('srcbtn').setAttribute('aria-expanded', 'false');
  });
  $('srcmenu').addEventListener('click', e=> e.stopPropagation());
  try{
    const s = localStorage.getItem('fd-sort');
    if(s){ sortKey = s; $('sort').value = s; }
  }catch(e){}
  $('sort').onchange = ()=>{
    sortKey = $('sort').value;
    try{ localStorage.setItem('fd-sort', sortKey); }catch(e){}
    sortView();
    renderList();
    saveState(false);
  };
  $('dl').onclick = doDownload;
  $('fmt').addEventListener('change', ()=>{ updateDownloadLabel(); saveState(false); });
  $('q').addEventListener('input', scheduleSave);
  $('q').addEventListener('keydown', e=>{ if(e.key === 'Enter') doSearch(); });
  document.addEventListener('visibilitychange', ()=>{ if(document.hidden) saveState(true); });
  window.addEventListener('pagehide', ()=> saveState(true));
  window.addEventListener('beforeunload', ()=> saveState(true));
  $('pick').onclick = async()=>{ $('folder').textContent = await api.pick_folder(); };
  $('open').onclick = ()=> api.open_folder();
  $('ext').onclick = ()=>{ if(sel >= 0) api.open_external(items[sel].url); };
  const v = $('yt');
  v.addEventListener('loadstart', ()=> setLoading(t('preview_loading'), 0));
  v.addEventListener('progress', ()=>{ $('lfill').style.width = bufferedPct() + '%'; });
  v.addEventListener('waiting', ()=> setLoading(t('buffering'), bufferedPct()));
  v.addEventListener('loadeddata', ()=> setLoading(null));   // pronta: attende il play
  v.addEventListener('canplay', ()=> setLoading(null));
  v.addEventListener('playing', ()=> setLoading(null));
  v.addEventListener('error', ()=>{ if(v.src) setPlaceholder('preview_unavailable'); });
  applyTheme(document.documentElement.getAttribute('data-theme'));
  applyLang(lang);
  setLocal('ready');
  try{
    const st = await api.load_state();   // stato del progetto corrente
    restoreState(st);
  }catch(e){}
  renderSourceMenu();
  refreshSources();
  setInterval(refreshSources, 60000);
  refreshProject();
  setInterval(refreshProject, 4000);
  refreshDeps();
  setInterval(poll, 120);
}

window.addEventListener('pywebviewready', ()=>{ api = window.pywebview.api; boot(); });
