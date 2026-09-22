"use strict";
const frame = document.getElementById("slide");
let current = null;
let generation = 0;
function fallback() {
  generation++;
  current = null;
  frame.hidden = true;
  frame.removeAttribute("src");
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
      // This is a synthetic local test, not an arbitrary HTML feed consumer.
      if (!["/slides/a.html", "/slides/b.html", "/slides/c.html"].includes(slide.path)) throw new Error("Unknown slide");
      const token = ++generation;
      frame.hidden = true;
      const check = await fetch(slide.path, {cache: "no-store", signal: AbortSignal.timeout(2000)});
      if (!check.ok) throw new Error("Slide unavailable");
      current = slide.id;
      frame.onload = () => { if (generation === token) frame.hidden = false; };
      frame.src = slide.path;
    }
  } catch (error) {
    fallback();
  } finally {
    window.setTimeout(poll, 500);
  }
}
poll();
