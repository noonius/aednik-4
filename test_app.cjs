const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
class Element {
  constructor(tagName = 'DIV') { this.tagName = tagName; this.hidden = false; this.value = ''; this.style = {}; this.events = {}; this.children = []; }
  addEventListener(type, handler) { this.events[type] = handler; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this[name] = value; }
  focus() { focused = this; }
  scrollIntoView(options) { this.lastScroll = options; }
  click() { this.events.click?.({ target: this }); }
}
let focused;
const html = fs.readFileSync('docs/index.html', 'utf8');
const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new Element()]));
elements.mode.value = 'image'; elements.group.value = '';
const parts = Object.fromEntries(['.question-area', '.plant-list'].map(name => [name, new Element()]));
const memory = new Map(); const keyboard = {};
const context = vm.createContext({
  window: { STANDALONE: true }, document: { getElementById: id => { assert.ok(elements[id], id); return elements[id]; },
    querySelector: selector => { assert.ok(parts[selector], selector); return parts[selector]; },
    createElement: tag => new Element(tag.toUpperCase()), createDocumentFragment: () => new Element(),
    addEventListener: (type, handler) => { keyboard[type] = handler; } },
  localStorage: { getItem: key => memory.get(key), setItem: (key, value) => memory.set(key, value) },
  navigator: {}, location: { protocol: 'file:' }, console, setTimeout, Blob, URL
});
for (const filename of ['taimed.js', 'study.js', 'app.js']) vm.runInContext(fs.readFileSync('docs/' + filename, 'utf8'), context);
assert.match(elements.count.textContent, /kaarti/);
assert.equal(elements.answer.hidden, true);
elements.reveal.click(); assert.equal(elements.answer.hidden, false); assert.ok(elements.estonian.textContent);
assert.equal(focused, elements['answer-content']);
assert.match(elements['session-count'].textContent, /0\/20/);
// Numeric shortcuts must also work when an answer button has focus.
keyboard.keydown({ key: '2', code: 'Digit2', target: { tagName: 'BUTTON' }, preventDefault() {} });
assert.equal(elements.answer.hidden, true);
let saved = JSON.parse(memory.get('aednik-taimenimed-progress-v1')); assert.equal(Object.keys(saved.progress).length, 1);
assert.equal(Object.values(saved.progress)[0].level, 1);
assert.equal(focused, elements['question-title']);
assert.match(elements['session-count'].textContent, /1\/20/);
assert.equal(elements.undo.hidden, false);
elements.undo.click();
assert.equal(Object.keys(JSON.parse(memory.get('aednik-taimenimed-progress-v1')).progress).length, 0);
assert.equal(elements.answer.hidden, false);
assert.equal(focused, elements['answer-content']);
assert.equal(elements.undo.hidden, true);
elements.known.click();
elements.reveal.click(); elements.again.click();
saved = JSON.parse(memory.get('aednik-taimenimed-progress-v1')); assert.ok(Object.values(saved.progress).some(s => s.level === 0));
assert.match(elements['session-count'].textContent, /korduskaarti ootel/);
elements.undo.click();
assert.ok(!Object.values(JSON.parse(memory.get('aednik-taimenimed-progress-v1')).progress).some(s => s.level === 0));
elements.mode.value = 'et-latin'; elements.mode.events.change();
assert.equal(elements['plant-image'].hidden, true); assert.ok(elements['name-question'].textContent);
assert.match(elements['name-question']['aria-label'], /Mis on ladinakeelne nimi/);
elements.reveal.click(); elements.known.click();
assert.equal(focused, elements['name-question']);
elements.group.value = 'Püsililled'; elements.group.events.change(); assert.equal(elements['plant-group'].textContent, 'Püsililled');
elements.mode.value = 'et-latin'; elements.group.value = 'Kahjustajad'; elements.group.events.change();
assert.equal(elements.empty.hidden, false); assert.equal(elements.practice.hidden, true);
elements.search.value = 'Aconitum'; elements.search.events.input(); assert.match(elements['list-count'].textContent, /1 kirjet/);
assert.equal(elements.download.hidden, true);
assert.match(elements['offline-help'].textContent, /eraldi allalaadimist vaja/);
elements['plant-image'].events.error();
assert.ok(!elements.feedback.textContent.includes('internetiga'));
assert.deepEqual(JSON.parse(memory.get('aednik-taimenimed-preferences-v1')), {mode: 'et-latin', group: 'Kahjustajad'});
elements.mode.value = 'image'; elements.group.value = '';
const reopened = vm.createContext({...context, window: {STANDALONE: true}});
for (const filename of ['taimed.js', 'study.js', 'app.js']) vm.runInContext(fs.readFileSync('docs/' + filename, 'utf8'), reopened);
assert.equal(elements.mode.value, 'et-latin'); assert.equal(elements.group.value, 'Kahjustajad');
elements.group.value = 'Invasiivsed taimed'; elements.group.events.change();
vm.runInContext('progress = {}; save(); start(true);', reopened);
for (let i = 0; i < 6; i++) { elements.reveal.click(); elements.known.click(); }
assert.equal(elements.empty.hidden, false);
assert.match(elements['session-count'].textContent, /6\/6/);
elements.undo.click(); assert.equal(elements.empty.hidden, true);
assert.equal(elements.answer.hidden, false);
assert.match(elements['session-count'].textContent, /5\/6/);
const before = JSON.parse(memory.get('aednik-taimenimed-progress-v1'));
elements.known.click(); elements.undo.click();
assert.deepEqual(JSON.parse(memory.get('aednik-taimenimed-progress-v1')), before);
console.log('OK: rakenduse käivitumine, vastuse avamine, hindamine, klahvid, salvestamine, filtrid, tühi rühm ja nimeotsing.');
// Scores must follow grading, undo, and the selected exercise independently.
elements.search.value = vm.runInContext('current.estonian', reopened);
parts['.plant-list'].open = true;
parts['.plant-list'].events.toggle({ target: parts['.plant-list'] });
const rowScore = () => elements.plants.children[0].children[0].children[2];
assert.equal(rowScore().children[0].textContent, '0/6');
assert.equal(rowScore().children[1].textContent, 'Õppimata');
elements.known.click();
assert.equal(rowScore().children[0].textContent, '1/6');
assert.match(elements['score-summary'].textContent, /1\/1 kaarti harjutatud/);
elements.undo.click();
assert.equal(rowScore().children[0].textContent, '0/6');
elements.again.click();
assert.equal(rowScore().children[1].textContent, 'Harjuta uuesti');
elements.undo.click();
elements.mode.value = 'image'; elements.mode.events.change();
assert.equal(rowScore().children[0].textContent, '0/6');
assert.match(elements['score-summary'].textContent, /Pilt → nimed/);
elements.search.value = 'tamme äkksurm'; elements.search.events.input();
assert.equal(rowScore().children[1].textContent, 'Kaart puudub');
assert.match(elements['score-summary'].textContent, /pole valitud harjutuse kaarte/);
console.log('OK: õppeskoor muutub hindamisel ja tagasivõtmisel; harjutused ja puuduva kaardi olek eristuvad.');

reopened.window.matchMedia = () => ({matches: true});
elements['answer-content'].lastScroll = undefined;
parts['.question-area'].lastScroll = undefined;
elements.reveal.click();
assert.equal(elements['answer-content'].lastScroll, undefined);
assert.equal(focused, elements['answer-content']);
elements.known.click();
assert.equal(parts['.question-area'].lastScroll, undefined);
assert.ok(html.indexOf('id="group"') > html.indexOf('id="known"'));
console.log('OK: valikud on kaardi järel; vastuse avamine ja hindamine ei keri mobiilivaadet.');
