/* A fixed Full-HD canvas keeps TV layouts intact in smaller browser windows. */
(() => {
  'use strict';
  const WIDTH = 1920;
  const HEIGHT = 1080;
  const selectors = [
    '.menu-card-content', '.menu-feature-content', '.menu-fallback',
    '.news-card', '.bauernregel-card', '.namenstag-card',
    '.weisheit-card', '.zitat-card', '.weather-tomorrow-card',
    '.weather-forecast-card', '.weather-deluxe-card',
  ].join(',');
  const originals = new WeakMap();
  const prepared = new WeakSet();

  function prepareLines(box) {
    if (!box.matches('.weisheit-card') || prepared.has(box)) return;
    const text = box.querySelector('.weisheit-text');
    const lines = [...box.querySelectorAll('.weisheit-line')];
    const context = document.createElement('canvas').getContext('2d');
    if (!text || !context) return;
    const style = getComputedStyle(text);
    context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const widths = lines.map(line => context.measureText(line.textContent).width);
    // Preserve deliberate source lines; when needed, balance each into two lines.
    if (widths.some(width => width > text.clientWidth)) {
      lines.forEach((line, index) => {
        line.classList.add('weisheit-line-wrap');
        line.style.width = `${Math.ceil(widths[index] * 0.58)}px`;
      });
    }
    prepared.add(box);
  }

  function scaleCanvas() {
    const scale = Math.min(window.innerWidth / WIDTH, window.innerHeight / HEIGHT);
    document.body.classList.add('display-canvas');
    document.body.style.transform = `scale(${scale})`;
    document.body.style.left = `${(window.innerWidth - WIDTH * scale) / 2}px`;
    document.body.style.top = `${(window.innerHeight - HEIGHT * scale) / 2}px`;
  }

  function fits(box) {
    if (box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1) return false;
    const bounds = box.getBoundingClientRect();
    return [...box.querySelectorAll('*')].every(element => {
      if (!element.getClientRects().length || element.tagName === 'SCRIPT') return true;
      const rect = element.getBoundingClientRect();
      return rect.top >= bounds.top - 1 && rect.bottom <= bounds.bottom + 1 &&
        rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1 &&
        element.scrollWidth <= element.clientWidth + 1;
    });
  }

  function fitBox(box) {
    prepareLines(box);
    const elements = [box, ...box.querySelectorAll('*')].filter(element => element.tagName !== 'SCRIPT');
    // Read all sizes before writing any, including inherited/em sizes.
    elements.forEach(element => {
      if (!originals.has(element)) originals.set(element, parseFloat(getComputedStyle(element).fontSize));
    });
    const apply = factor => elements.forEach(element => {
      element.style.fontSize = `${originals.get(element) * factor}px`;
    });
    apply(1);
    if (!fits(box)) {
      let low = 0.60;
      let high = 1;
      for (let step = 0; step < 10; step += 1) {
        const middle = (low + high) / 2;
        apply(middle);
        if (fits(box)) low = middle;
        else high = middle;
      }
      apply(low);
    }
    // Oversized input remains detectable instead of being silently truncated.
    box.dataset.layoutOverflow = String(!fits(box));
  }

  function layout() {
    scaleCanvas();
    document.querySelectorAll(selectors).forEach(fitBox);
    document.documentElement.dataset.layoutReady = 'true';
  }

  let pending;
  function schedule() {
    cancelAnimationFrame(pending);
    pending = requestAnimationFrame(layout);
  }
  window.addEventListener('resize', schedule);
  window.addEventListener('load', schedule);
  if (document.fonts) document.fonts.ready.then(schedule);
  layout();
})();
