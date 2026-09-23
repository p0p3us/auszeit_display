"use strict";
const frames = [document.getElementById("slide"), document.getElementById("slide-next")];
const fallbackPage = document.getElementById("fallback");
let active = null;
let current = null;
let generation = 0;
let expiryTimer = null;
function fallback() {
  generation++;
  clearTimeout(expiryTimer);
  current = active = null;
  fallbackPage.hidden = false;
  for (const frame of frames) frame.classList.remove("active");
}
function loadFrame(frame, path) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => finish(new Error("Slide load timed out")), 5000);
    function finish(error) {
      clearTimeout(timeout);
      frame.onload = frame.onerror = null;
      error ? reject(error) : resolve();
    }
    frame.onload = () => finish();
    frame.onerror = () => finish(new Error("Slide load failed"));
    frame.src = path;
  });
}
async function poll() {
  try {
    const response = await fetch("/api/state", {cache: "no-store", signal: AbortSignal.timeout(2000)});
    if (!response.ok) throw new Error("State unavailable");
    const state = await response.json();
    const slide = state.slide;
    if (!slide) {
      if (current !== null) fallback();
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
      await loadFrame(next, slide.path);
      // Keep the outgoing slide visible throughout loading and layout.
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (generation !== token) return;
      const until = slide.valid_until ? Date.parse(slide.valid_until) : null;
      if (until !== null && (!Number.isFinite(until) || until <= Date.now())) {
        fallback();
        return;
      }
      next.classList.add("active");
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
    window.setTimeout(poll, 500);
  }
}
poll();
