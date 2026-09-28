"use strict";
const frames = [document.getElementById("slide"), document.getElementById("slide-next")];
const fallbackPage = document.getElementById("fallback");
let active = null;
let current = null;
let generation = 0;
let expiryTimer = null;
let lastHeartbeat = 0;
let heartbeatEnabled = false;
async function heartbeat() {
  if (!heartbeatEnabled) return;
  const now = Date.now();
  if (now - lastHeartbeat < 10000) return;
  lastHeartbeat = now;
  try {
    await fetch('/api/heartbeat', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({state: current !== null ? 'playing' : fallbackPage.hidden ? 'loading' : 'fallback', slide_id: current}),
      signal: AbortSignal.timeout(2000)});
  } catch (_) { /* A status failure must not interrupt playback. */ }
}
function fallback() {
  generation++;
  clearTimeout(expiryTimer);
  current = active = null;
  fallbackPage.hidden = false;
  for (const frame of frames) {
    frame.classList.remove("active");
    frame.classList.remove("preparing");
  }
}
function loadFrame(frame, path, packageSlide, token) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => finish(new Error("Slide load timed out")), 5000);
    function finish(error) {
      clearTimeout(timeout);
      window.removeEventListener('message', ready);
      frame.onload = frame.onerror = null;
      error ? reject(error) : resolve();
    }
    function ready(event) {
      if (event.source === frame.contentWindow && event.data?.type === 'auszeit-slide-ready'
          && event.data.token === token) finish();
    }
    window.addEventListener('message', ready);
    frame.onload = () => {
      if (generation !== token) return finish(new Error('Slide superseded'));
      frame.classList.add('preparing');
      if (packageSlide) frame.contentWindow.postMessage({type: 'auszeit-prepare', token}, '*');
      else finish();
    };
    frame.onerror = () => finish(new Error("Slide load failed"));
    frame.src = path;
  });
}
async function poll() {
  try {
    const response = await fetch("/api/state", {cache: "no-store", signal: AbortSignal.timeout(2000)});
    if (!response.ok) throw new Error("State unavailable");
    const state = await response.json();
    heartbeatEnabled = state.scenario === 'packages';
    const slide = state.slide;
    if (!slide) {
      if (current !== null || fallbackPage.hidden) fallback();
    } else if (slide.id !== current) {
      // Package test paths are immutable and served only from verified manifests.
      const localSlide = ["/slides/a.html", "/slides/b.html", "/slides/c.html"].includes(slide.path);
      const packageSlide = state.scenario === "packages" && /^\/releases\/[A-Za-z0-9_-]+\/content\/auszeit-display\/[A-Za-z0-9_./-]+\.html$/.test(slide.path)
        && !slide.path.split("/").slice(1).some(part => part === "." || part === ".." || part === "");
      if (!localSlide && !packageSlide) throw new Error("Unknown slide");
      const token = ++generation;
      const next = frames.find(frame => frame !== active);
      const check = await fetch(slide.path, {cache: "no-store", signal: AbortSignal.timeout(2000)});
      if (!check.ok) throw new Error("Slide unavailable");
      await loadFrame(next, slide.path, packageSlide, token);
      // Keep the outgoing slide visible throughout loading and layout.
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (generation !== token) return;
      const until = slide.valid_until ? Date.parse(slide.valid_until) : null;
      if (until !== null && (!Number.isFinite(until) || until <= Date.now())) {
        fallback();
        return;
      }
      next.classList.add("active");
      next.classList.remove("preparing");
      if (active) active.classList.remove("active");
      active = next;
      current = slide.id;
      fallbackPage.hidden = true;
      clearTimeout(expiryTimer);
      if (until !== null) expiryTimer = setTimeout(fallback, Math.min(until - Date.now(), 2147483647));
    }
  } catch (error) {
    fallback();
  } finally {
    void heartbeat();
    window.setTimeout(poll, 500);
  }
}
poll();
