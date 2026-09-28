const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../player/local_test/web/app.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, '../player/local_test/web/index.html'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

test('slide readiness waits for fonts, decoded images and two rendering frames', async () => {
  const server = fs.readFileSync(path.join(__dirname, '../player/package_test/server.py'), 'utf8');
  const bridge = server.match(/SLIDE_READY = """([\s\S]*?)"""/)[1];
  let onMessage, fontsReady, imageReady;
  const sent = [], frames = [];
  const parent = {postMessage: value => sent.push(value)};
  vm.runInNewContext(bridge, {
    window: {addEventListener: (_, fn) => {onMessage = fn;}}, parent,
    document: {fonts: {ready: new Promise(resolve => {fontsReady = resolve;})},
      images: [{decode: () => new Promise(resolve => {imageReady = resolve;})}]},
    requestAnimationFrame: fn => frames.push(fn),
  });
  await onMessage({source: {}, data: {type: 'auszeit-prepare', token: 7}});
  const pending = onMessage({source: parent, data: {type: 'auszeit-prepare', token: 7}});
  assert.equal(sent.length, 0);
  fontsReady();
  await settle();
  assert.equal(sent.length, 0);
  imageReady();
  await settle();
  frames.shift()();
  assert.equal(sent.length, 0);
  frames.shift()();
  await pending;
  assert.equal(sent[0].token, 7);
});

function setup(options = {}) {
  const elements = Object.fromEntries(['slide', 'slide-next', 'fallback'].map(id => {
    const classes = new Set();
    const hidden = id === 'fallback' && /<main\b[^>]*id="fallback"[^>]*\bhidden\b/.test(html);
    return [id, {hidden, classList: {add: c => classes.add(c), remove: c => classes.delete(c), contains: c => classes.has(c)}}];
  }));
  let slide = options.empty ? null : {id: 'A', path: '/slides/a.html', valid_until: null};
  let scenario = 'cycle';
  const timers = new Map();
  let counter = 0;
  const listeners = new Set();
  for (const element of Object.values(elements)) element.contentWindow = {postMessage: message => {element.message = message;}};
  const context = vm.createContext({
    document: {getElementById: id => elements[id]}, Date, AbortSignal,
    setTimeout: (fn, delay) => {timers.set(++counter, {fn, delay}); return counter;},
    clearTimeout: id => timers.delete(id),
    requestAnimationFrame: fn => queueMicrotask(fn),
    addEventListener: (type, fn) => listeners.add(fn),
    removeEventListener: (type, fn) => listeners.delete(fn),
    fetch: async () => ({ok: !options.unavailable, json: async () => ({slide, scenario})})
  });
  context.window = context;
  vm.runInContext(source, context);
  return {elements, timers, setSlide: value => {slide = value;}, setScenario: value => {scenario = value;},
    ready: (frame, source = frame.contentWindow) => {
      for (const fn of [...listeners]) fn({source, data: {type: 'auszeit-slide-ready', token: frame.message.token}});
    },
    poll: () => vm.runInContext('poll()', context)};
}

test('startup keeps fallback hidden until the first slide is ready', async () => {
  const state = setup();
  assert.equal(state.elements.fallback.hidden, true);
  await settle();
  assert.equal(state.elements.fallback.hidden, true);
  assert.equal(state.elements.slide.classList.contains('active'), false);
  await showFirst(state);
});

test('startup with empty playlist shows fallback', async () => {
  const state = setup({empty: true});
  await settle();
  assert.equal(state.elements.fallback.hidden, false);
});

test('startup with unavailable state shows fallback', async () => {
  const state = setup({unavailable: true});
  await settle();
  assert.equal(state.elements.fallback.hidden, false);
});

test('first slide timeout shows fallback and can recover', async () => {
  const state = setup();
  await settle();
  [...state.timers.values()].find(timer => timer.delay === 5000).fn();
  await settle();
  assert.equal(state.elements.fallback.hidden, false);
  const retry = state.poll();
  await settle();
  state.elements.slide.onload();
  await retry;
  assert.equal(state.elements.fallback.hidden, true);
  assert.equal(state.elements.slide.classList.contains('active'), true);
});

async function showFirst(state) {
  await settle();
  state.elements.slide.onload();
  await settle();
  assert.equal(state.elements.slide.classList.contains('active'), true);
  assert.equal(state.elements.fallback.hidden, true);
}

test('old slide stays visible during delayed load; fallback never flashes', async () => {
  const state = setup();
  await showFirst(state);
  state.setSlide({id: 'B', path: '/slides/b.html', valid_until: null});
  const pending = state.poll();
  await settle();
  assert.equal(state.elements.slide.classList.contains('active'), true);
  assert.equal(state.elements['slide-next'].classList.contains('active'), false);
  assert.equal(state.elements.fallback.hidden, true);
  state.elements['slide-next'].onload();
  await pending;
  assert.equal(state.elements['slide-next'].classList.contains('active'), true);
  assert.equal(state.elements.slide.classList.contains('active'), false);
  assert.equal(state.elements.fallback.hidden, true);
});

test('verified package URL loads without exposing fallback', async () => {
  const state = setup();
  await showFirst(state);
  state.setScenario('packages');
  state.setSlide({id: 'display-1:A', path: '/releases/display-1/content/auszeit-display/a.html', valid_until: null});
  const pending = state.poll();
  await settle();
  assert.equal(state.elements.fallback.hidden, true);
  assert.equal(state.elements['slide-next'].src, '/releases/display-1/content/auszeit-display/a.html');
  state.elements['slide-next'].onload();
  await settle();
  assert.equal(state.elements.slide.classList.contains('active'), true);
  state.ready(state.elements['slide-next'], {});
  await settle();
  assert.equal(state.elements.slide.classList.contains('active'), true);
  state.ready(state.elements['slide-next']);
  await pending;
  assert.equal(state.elements['slide-next'].classList.contains('active'), true);
  assert.equal(state.elements.fallback.hidden, true);
});

test('package URL containing traversal is refused', async () => {
  const state = setup();
  await showFirst(state);
  state.setScenario('packages');
  state.setSlide({id: 'bad', path: '/releases/display-1/content/auszeit-display/../a.html', valid_until: null});
  await state.poll();
  assert.equal(state.elements['slide-next'].src, undefined);
  assert.equal(state.elements.fallback.hidden, false);
});

test('empty playlist displays fallback and hides frames', async () => {
  const state = setup();
  await showFirst(state);
  state.setSlide(null);
  await state.poll();
  assert.equal(state.elements.fallback.hidden, false);
  assert.equal(state.elements.slide.classList.contains('active'), false);
});

test('load timeout displays fallback instead of stale content', async () => {
  const state = setup();
  await showFirst(state);
  state.setSlide({id: 'B', path: '/slides/b.html', valid_until: null});
  const pending = state.poll();
  await settle();
  [...state.timers.values()].find(timer => timer.delay === 5000).fn();
  await pending;
  assert.equal(state.elements.fallback.hidden, false);
});

test('expiry during loading prevents late load from hiding fallback', async () => {
  const state = setup();
  await showFirst(state);
  state.setSlide({id: 'B', path: '/slides/b.html', valid_until: new Date(Date.now() + 30000).toISOString()});
  const second = state.poll();
  await settle();
  state.elements['slide-next'].onload();
  await second;
  state.setSlide({id: 'C', path: '/slides/c.html', valid_until: null});
  const third = state.poll();
  await settle();
  [...state.timers.values()].find(timer => timer.delay > 10000).fn();
  state.elements.slide.onload();
  await third;
  assert.equal(state.elements.fallback.hidden, false);
  assert.equal(state.elements.slide.classList.contains('active'), false);
});
