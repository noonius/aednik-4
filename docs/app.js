'use strict';
const plants = window.PLANTS;
const S = window.Study;
const $ = id => document.getElementById(id);
const STORAGE = 'aednik-taimenimed-progress-v1';
const PREFERENCES = 'aednik-taimenimed-preferences-v1';
let progress = {};
let queue = [];
let attempts = 0;
let knownCount = 0;
let initialCount = 0;
let revealed = false;
let current = null;
let retries = new Set();
let answered = new Set();
let lastRating = null;
let mode = 'image';
let group = '';
let registration;
function warnStorage() {
  $('storage-warning').hidden = false;
  $('storage-warning').textContent = 'Brauser ei luba õpiedu salvestada. Õppida saad edasi, kuid enne lehe sulgemist salvesta õpiedu failina.';
}
const validKeys = new Set(plants.flatMap(p => ['image', 'et-latin', 'latin-et'].filter(m => S.eligible(p, m)).map(m => S.key(p, m))));
try {
  const saved = localStorage.getItem(STORAGE);
  if (saved) progress = S.validateBackup(JSON.parse(saved), validKeys);
} catch { warnStorage(); }
function save() {
  try { localStorage.setItem(STORAGE, JSON.stringify({ version: 1, progress })); }
  catch { warnStorage(); }
}
for (const name of new Set(plants.map(p => p.group))) {
  const option = document.createElement('option'); option.value = name; option.textContent = name; $('group').append(option);
}
$('total').textContent = `${plants.length} kirjet`;
try {
  const settings = JSON.parse(localStorage.getItem(PREFERENCES) || 'null');
  if (settings && ['image', 'et-latin', 'latin-et'].includes(settings.mode)) $('mode').value = settings.mode;
  if (settings && (settings.group === '' || plants.some(p => p.group === settings.group))) $('group').value = settings.group;
} catch { /* Invalid saved choices do not affect learning progress. */ }
function eligiblePlants() { return plants.filter(p => S.eligible(p, mode) && (!group || p.group === group)); }
function focusQuestion() {
  (current ? $(mode === 'image' ? 'question-title' : 'name-question') : $('empty-title')).focus({ preventScroll: true });
}
function updateCount() {
  const eligible = eligiblePlants();
  const due = eligible.filter(p => !progress[S.key(p, mode)] || progress[S.key(p, mode)].due <= Date.now()).length;
  $('count').textContent = `${eligible.length} kaarti · ${due} õppimiseks valmis`;
  const pending = queue.filter(p => answered.has(p.id)).length;
  $('session-count').textContent = initialCount ? `${answered.size}/${initialCount} kaarti hinnatud${pending ? ` · ${pending} korduskaarti ootel` : ''}` : '';
  $('progress-bar').style.transform = `scaleX(${initialCount ? answered.size / initialCount : 0})`;
  $('undo').hidden = !lastRating;
  if (document.querySelector('.plant-list').open) renderList();
}
function showEmpty() {
  current = null; revealed = false;
  document.querySelector('.question-area').hidden = true;
  $('card').style.gridTemplateColumns = '1fr';
  $('hidden-answer').hidden = true; $('answer').hidden = true; $('empty').hidden = false;
  const eligible = eligiblePlants();
  $('empty-title').textContent = attempts ? 'Selleks korraks tehtud.' : eligible.length ? 'Praegu pole kordamisi ootel.' : 'Selles kategoorias pole selle harjutuse kaarte.';
  let text = attempts ? `Vastasid ${attempts} korda, neist ${knownCount} korral teadsid vastust.` : '';
  if (!eligible.length) text += ' Vali teine harjutus või vaata allpool õpinimekirja.';
  else {
    const remaining = eligible.filter(p => !progress[S.key(p, mode)] || progress[S.key(p, mode)].due <= Date.now()).length;
    if (attempts && remaining) text += ` Õppimiseks on veel ${remaining} kaarti valmis.`;
    const due = eligible.map(p => progress[S.key(p, mode)]?.due || 0).sort((a, b) => a - b)[0];
    if (due > Date.now()) text += ` Järgmine kaart ootab ${new Date(due).toLocaleString('et-EE', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })}.`;
    text += ' Soovi korral võid kohe edasi harjutada.';
  }
  $('empty-copy').textContent = text.trim(); $('practice').hidden = !eligible.length;
  $('practice-actions').hidden = !eligible.length;
  updateCount();
}
function showCard() {
  current = queue[0];
  if (!current) { showEmpty(); return; }
  revealed = false;
  document.querySelector('.question-area').hidden = false;
  $('card').style.gridTemplateColumns = '';
  $('empty').hidden = true; $('answer').hidden = true; $('hidden-answer').hidden = false;
  $('plant-group').textContent = current.group;
  const pictureMode = mode === 'image';
  $('plant-image').hidden = !pictureMode; $('name-question').hidden = pictureMode;
  if (pictureMode) $('plant-image').src = current.image;
  else {
    $('name-question').textContent = mode === 'et-latin' ? current.estonian : current.latin;
    $('name-question').lang = mode === 'latin-et' ? 'la' : 'et';
  }
  $('question-title').textContent = pictureMode ? 'Mis on pildil?' : mode === 'et-latin' ? 'Mis on ladinakeelne nimi?' : 'Mis on eestikeelne nimi?';
  $('name-question').setAttribute('aria-label', `${$('name-question').textContent}. ${$('question-title').textContent}`);
  $('estonian').textContent = current.estonian;
  $('latin').textContent = current.latin;
  $('latin').hidden = !current.latin;
  $('answer-content').setAttribute('aria-labelledby', current.latin ? 'estonian latin' : 'estonian');
  $('source').textContent = pictureMode ? current.source : '';
  $('source').hidden = !pictureMode || !current.source;
  const next = S.schedule(progress[S.key(current, mode)], true, Date.now());
  const days = Math.round((next.due - Date.now()) / 86400000);
  $('next-review').textContent = `Kui teadsid, korda ${days === 1 ? 'homme' : `${days} päeva pärast`}.`;
  updateCount();
}
function start(practice = false) {
  mode = $('mode').value; group = $('group').value;
  try { localStorage.setItem(PREFERENCES, JSON.stringify({ mode, group })); } catch { warnStorage(); }
  queue = S.select(plants, progress, mode, group, Date.now(), practice);
  attempts = 0; knownCount = 0; initialCount = queue.length; retries = new Set(); answered = new Set(); lastRating = null;
  $('feedback').textContent = ''; showCard();
}
function reveal() {
  if (!current || revealed) return;
  revealed = true; $('hidden-answer').hidden = true; $('answer').hidden = false;
  $('answer-content').focus({ preventScroll: true });
}
function rate(known) {
  if (!current || !revealed) return;
  const plant = current; const id = S.key(plant, mode);
  lastRating = { id, previous: progress[id], queue: [...queue], attempts, knownCount,
    retries: new Set(retries), answered: new Set(answered) };
  progress[id] = S.schedule(progress[id], known, Date.now()); save();
  queue.shift(); attempts++; answered.add(plant.id); if (known) knownCount++;
  // shortcut: one retry per card per session; further failures remain due in ten minutes.
  if (!known && !retries.has(id)) { queue.splice(Math.min(3, queue.length), 0, plant); retries.add(id); }
  $('feedback').textContent = known ? 'Vastus märgitud. Järgmine kaart.' : 'See kaart tuleb veel harjutamiseks tagasi.';
  showCard();
  focusQuestion();
}
$('undo').addEventListener('click', () => {
  if (!lastRating) return;
  const last = lastRating;
  if (last.previous) progress[last.id] = last.previous;
  else delete progress[last.id];
  queue = last.queue; attempts = last.attempts; knownCount = last.knownCount;
  retries = last.retries; answered = last.answered; lastRating = null;
  save(); showCard(); reveal();
  $('feedback').textContent = 'Viimane hinnang on tagasi võetud. Hinda seda kaarti uuesti.';
});
$('reveal').addEventListener('click', reveal);
$('again').addEventListener('click', () => rate(false)); $('known').addEventListener('click', () => rate(true));
$('mode').addEventListener('change', () => start()); $('group').addEventListener('change', () => start());
$('practice').addEventListener('click', () => { start(true); $('reveal').focus({ preventScroll: true }); });
document.addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.repeat || /INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) return;
  if (event.code === 'Space' && !revealed && current && !/BUTTON|SUMMARY|A/.test(event.target.tagName)) { event.preventDefault(); reveal(); }
  else if (revealed && ['1', '2'].includes(event.key)) { event.preventDefault(); rate(event.key === '2'); }
});
function renderList() {
  const query = $('search').value.toLocaleLowerCase('et-EE').trim();
  const results = plants.filter(p => `${p.estonian} ${p.latin} ${p.group}`.toLocaleLowerCase('et-EE').includes(query));
  $('list-count').textContent = `${results.length} kirjet`;
  const eligible = results.filter(p => S.eligible(p, mode));
  const studied = eligible.filter(p => progress[S.key(p, mode)]?.reviews > 0).length;
  const average = eligible.length ? eligible.reduce((sum, p) => sum + (progress[S.key(p, mode)]?.level || 0), 0) / eligible.length : 0;
  const modes = { image: 'Pilt → nimed', 'et-latin': 'Eesti → ladina', 'latin-et': 'Ladina → eesti' };
  $('score-summary').textContent = eligible.length ? `${modes[mode]} · Keskmine õppeskoor ${average.toLocaleString('et-EE', { maximumFractionDigits: 1 })}/6 · ${studied}/${eligible.length} kaarti harjutatud` : 'Otsingu tulemustes pole valitud harjutuse kaarte.';
  const fragment = document.createDocumentFragment();
  for (const plant of results) {
    const li = document.createElement('li');
    if (plant.image) { const img = document.createElement('img'); img.src = plant.image; img.loading = 'lazy'; img.alt = ''; li.append(img); }
    else { const placeholder = document.createElement('span'); placeholder.className = 'no-image'; placeholder.setAttribute('aria-hidden', 'true'); li.append(placeholder); }
    const description = document.createElement('div');
    const estonian = document.createElement('strong'); estonian.textContent = plant.estonian || plant.latin;
    const latin = document.createElement('em'); latin.lang = 'la'; latin.textContent = plant.latin;
    const groupLabel = document.createElement('small'); groupLabel.textContent = plant.group + (!plant.image ? ' · Pilt puudub' : '');
    const score = document.createElement('div'); score.className = 'learning-score';
    const value = document.createElement('span');
    const status = document.createElement('small');
    const state = progress[S.key(plant, mode)];
    const available = S.eligible(plant, mode);
    value.textContent = available ? `${state?.level || 0}/6` : '—';
    value.setAttribute('aria-label', available ? `Õppeskoor ${state?.level || 0} kuuest` : 'Õppeskoor puudub');
    status.textContent = !available ? 'Kaart puudub' : !state?.reviews ? 'Õppimata' : state.level === 0 ? 'Harjuta uuesti' : 'Õppeskoor';
    score.append(value, status);
    description.append(estonian, latin, groupLabel); li.append(description, score); fragment.append(li);
  }
  $('plants').replaceChildren(fragment);
}
$('search').addEventListener('input', renderList);
document.querySelector('.plant-list').addEventListener('toggle', event => { if (event.target.open) renderList(); });
$('export').addEventListener('click', () => {
  const file = new Blob([JSON.stringify({ version: 1, progress }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(file); const link = document.createElement('a');
  link.href = url; link.download = 'aednik-opiedu.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  $('feedback').textContent = 'Õpiedu fail on salvestamiseks valmis.';
});
$('import').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 2000000) throw new Error('Õpiedu fail on liiga suur. Vali tööriistast salvestatud JSON-fail.');
    const incoming = S.validateBackup(JSON.parse(await file.text()), validKeys);
    for (const [id, state] of Object.entries(incoming)) if (!progress[id] || state.updated > progress[id].updated) progress[id] = state;
    save(); start(); $('feedback').textContent = 'Õpiedu on taastatud. Uuemad vastused jäid alles.';
  } catch (error) { $('feedback').textContent = error instanceof SyntaxError ? 'See fail ei ole loetav õpiedu varukoopia. Vali selle tööriista kaudu salvestatud JSON-fail.' : error.message || 'Õpiedu lugemine ei õnnestunud.'; }
  event.target.value = '';
});
$('plant-image').addEventListener('error', () => {
  $('feedback').textContent = window.STANDALONE ? 'Pilt ei avanenud. Proovi fail uuesti avada; kui viga kordub, kasuta värsket õppimistööriista faili.' : location.protocol === 'file:' ? 'Pilt ei laadinud. Hoia HTML-fail ja pildid samas kaustas ning ava leht uuesti.' : 'Pilt ei laadinud. Ava leht internetiga ja laadi materjal offline-kasutuseks alla.';
});
async function setupOffline() {
  if (window.STANDALONE) $('offline-help').textContent = 'See HTML-fail sisaldab pilte ja nimesid. Ava see brauseris; õppimiseks pole internetti ega eraldi allalaadimist vaja. Õpiedu säilitamiseks kasuta sama brauserit ja failiaadressi.';
  else if (location.protocol === 'file:') $('offline-help').textContent = 'Hoia õppimistööriista failid ja pildikaust koos. Telefoni avakuvale lisamiseks kasuta HTTPS-aadressil olevat veebiversiooni.';
  if (!('serviceWorker' in navigator) || location.protocol === 'file:') {
    $('download').hidden = true;
    $('offline-status').textContent = location.protocol === 'file:' ? (window.STANDALONE ? 'Pildid ja nimed on selles failis. Õppimiseks pole internetti vaja.' : 'Avatud kohalikust kaustast. Hoia kõik failid koos; õpiedu salvestamine sõltub brauserist.') : 'See brauser ei toeta offline-salvestamist.';
    return;
  }
  try {
    registration = await navigator.serviceWorker.register('sw.js');
    await navigator.serviceWorker.ready;
    $('offline-status').textContent = navigator.onLine ? 'Offline õppimiseks laadi materjal alla.' : 'Oled võrguühenduseta. Kasutan seadmesse salvestatud materjali.';
    const cache = await caches.open('aednik-offline-v1');
    if (await cache.match('offline-ready')) $('offline-status').textContent = 'Materjal on offline-kasutuseks valmis.';
  } catch { $('offline-status').textContent = 'Offline-salvestamine ei õnnestunud. Ava leht HTTPS-aadressilt või proovi teist brauserit.'; }
}
$('download').addEventListener('click', async () => {
  const button = $('download'); button.disabled = true;
  try {
    if (!registration) throw new Error('Offline-salvestamine pole veel valmis. Oota hetk ja proovi uuesti.');
    const manifest = await fetch('offline.json'); if (!manifest.ok) throw new Error('Materjali nimekiri ei laadinud. Proovi internetiühendusega uuesti.');
    const assets = await manifest.json(); const cache = await caches.open('aednik-offline-v1');
    let completed = 0;
    const remaining = [...assets];
    const results = await Promise.allSettled(Array.from({ length: 4 }, async () => {
      while (remaining.length) {
        const path = remaining.shift();
        if (!(await cache.match(path))) {
          const response = await fetch(path);
          if (!response.ok || response.redirected || (path.endsWith('.jpg') && !response.headers.get('content-type')?.startsWith('image/'))) {
            throw new Error('Kõik failid ei laadinud. Kontrolli ühendust ja vajuta uuesti.');
          }
          await cache.put(path, response);
        }
        completed++; $('offline-status').textContent = `Materjali allalaadimine: ${completed}/${assets.length} faili. Hoia leht avatuna.`;
      }
    }));
    const failure = results.find(result => result.status === 'rejected');
    if (failure) throw failure.reason;
    await cache.put('offline-ready', new Response('ready'));
    if (navigator.storage?.persist) await navigator.storage.persist().catch(() => false);
    $('offline-status').textContent = 'Materjal on offline-kasutuseks valmis.';
  } catch (error) { $('offline-status').textContent = error.message || 'Salvestamine ei õnnestunud. Proovi uuesti.'; }
  finally { button.disabled = false; }
});
start(); setupOffline();
