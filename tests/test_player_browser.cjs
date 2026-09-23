const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../player/local_test/web/app.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));

function setup() {
  const elements = Object.fromEntries(['slide', 'slide-next', 'fallback'].map(id => {
    const classes = new Set();
    return [id, {hidden: false, classList: {add: c => classes.add(c), remove: c => classes.delete(c), contains: c => classes.has(c)}}];
  }));
  let slide = {id: 'A', path: '/slides/a.html', valid_until: null};
  const timers = new Map();
  let counter = 0;
  const context = vm.createContext({
    document: {getElementById: id => elements[id]}, Date, AbortSignal,
    setTimeout: (fn, delay) => {timers.set(++counter, {fn, delay}); return counter;},
    clearTimeout: id => timers.delete(id),
    requestAnimationFrame: fn => queueMicrotask(fn),
    fetch: async () => ({ok: true, json: async () => ({slide})})
  });
  context.window = context;
  vm.runInContext(source, context);
  return {elements, timers, setSlide: value => {slide = value;},
    poll: () => vm.runInContext('poll()', context)};
}

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
