/* PaintDial visualiser: the colour wheel and lighter/darker dial.
   Ported from the homepage (index.html) so it looks and behaves the same: the disc is capped
   to the saturation real paints reach at each hue and lightness, distance from the centre
   maps to saturation squared, the dial sets lightness, and the ring around the wheel is made
   of real paints. The one difference: the wheel only says where you're pointing. The page
   paints the wall with the nearest real paint to that point, so the pointer and the dial's
   centre show that paint, not the raw wheel colour.

   VisWheel.create({wheel, dial, pointer, ring, hexes, onMove, onRelease})
     onMove(hex)    while dragging the wheel or dial (once per frame at most)
     onRelease(hex) when a drag ends or a key nudge happens
   returns {setFromHex(hex), setPaint(hex), place(), currentHex()} */
(function (root) {
  'use strict';

  function hexToRgb(h) { h = h.replace('#', ''); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
  function rgbToHex(r, g, b) { return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase(); }
  function hslToRgb(h, s, l) {
    s /= 100; l /= 100;
    const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2;
    let r, g, b;
    if (h < 60) { [r, g, b] = [c, x, 0]; } else if (h < 120) { [r, g, b] = [x, c, 0]; } else if (h < 180) { [r, g, b] = [0, c, x]; }
    else if (h < 240) { [r, g, b] = [0, x, c]; } else if (h < 300) { [r, g, b] = [x, 0, c]; } else { [r, g, b] = [c, 0, x]; }
    return [(r + m) * 255, (g + m) * 255, (b + m) * 255];
  }
  function rgbToOklab(r, g, b) {
    const f = v => { v /= 255; return v > 0.04045 ? Math.pow((v + 0.055) / 1.055, 2.4) : v / 12.92; };
    const R = f(r), G = f(g), B = f(b);
    let l = 0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B,
        m = 0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B,
        s = 0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B;
    l = Math.cbrt(l); m = Math.cbrt(m); s = Math.cbrt(s);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function hexToHsl(hx) {
    const [r, g, b] = hexToRgb(hx);
    const max = Math.max(r, g, b) / 255, min = Math.min(r, g, b) / 255, l = (max + min) / 2;
    let h = 0, s = 0;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      const rr = r / 255, gg = g / 255, bb = b / 255;
      if (max === rr) h = ((gg - bb) / d + (gg < bb ? 6 : 0));
      else if (max === gg) h = (bb - rr) / d + 2;
      else h = (rr - gg) / d + 4;
      h *= 60;
    }
    return [h, s * 100, l * 100];
  }
  const radToSat = f => f * f, satToRad = f => Math.sqrt(f);

  /* Mouse and pen: press or drag to pick, as on the homepage.
     Touch: the wheel and dial sit in the middle of a page you scroll on a phone, so a finger
     dragging over them has to scroll the page, not pick. The same rule as the homepage's
     photo picker: a quick tap picks, a drag scrolls (the browser does it and sends
     pointercancel), and press-and-hold (finger still for HOLD_MS) starts a slide: the pick
     follows the finger and touchmove is cancelled so the page stays put. */
  const HOLD_MS = 350, SLOP = 10;
  function tapOrHold(el, pick, release) {
    const wrap = el.closest('.wheel-wrap, .dial-wrap') || el;
    let drag = false, tch = null, holdT = null;
    function endTouch() { clearTimeout(holdT); tch = null; wrap.classList.remove('fine'); }
    el.addEventListener('pointerdown', e => {
      if (e.pointerType !== 'touch') { drag = true; try { el.setPointerCapture(e.pointerId); } catch (x) {} pick(e); return; }
      endTouch();
      tch = { id: e.pointerId, x0: e.clientX, y0: e.clientY, moved: false, hold: false };
      holdT = setTimeout(() => {
        if (!tch || tch.moved) return;
        tch.hold = true; wrap.classList.add('fine');
        if (navigator.vibrate) navigator.vibrate(8);
        pick({ clientX: tch.x0, clientY: tch.y0 });
      }, HOLD_MS);
    });
    el.addEventListener('pointermove', e => {
      if (e.pointerType !== 'touch') { if (drag) pick(e); return; }
      if (!tch || e.pointerId !== tch.id) return;
      if (tch.hold) { pick(e); return; }
      if (Math.hypot(e.clientX - tch.x0, e.clientY - tch.y0) > SLOP) { tch.moved = true; clearTimeout(holdT); }
    });
    el.addEventListener('pointerup', e => {
      if (e.pointerType !== 'touch') { if (drag) { drag = false; release(); } return; }
      if (tch && e.pointerId === tch.id) {
        if (tch.hold) release();
        else if (!tch.moved) { pick(e); release(); }
      }
      endTouch();
    });
    el.addEventListener('pointercancel', e => {
      if (e.pointerType !== 'touch') { if (drag) { drag = false; release(); } return; }
      const held = tch && tch.hold; endTouch(); if (held) release();
    });
    el.addEventListener('touchmove', e => { if (tch && tch.hold && e.cancelable) e.preventDefault(); }, { passive: false });
    el.addEventListener('contextmenu', e => { if (tch) e.preventDefault(); });
  }

  function create(o) {
    const canvas = o.wheel, dial = o.dial, pointer = o.pointer;
    const ctx = canvas.getContext('2d'), dctx = dial.getContext('2d');
    const SIZE = 600, R = SIZE / 2;
    canvas.width = SIZE; canvas.height = SIZE;
    let hue = 200, sat = 35, light = 52, paintHex = null;

    /* ---------- paint-gamut cap (as the homepage) ---------- */
    const LIB = o.hexes.map(h => ({ hex: h, ok: rgbToOklab(...hexToRgb(h)) }));
    const HUEBUCKET = (() => {
      const b = Array.from({ length: 360 }, () => []);
      LIB.forEach(p => {
        const [r, g, bl] = hexToRgb(p.hex);
        const mx = Math.max(r, g, bl) / 255, mn = Math.min(r, g, bl) / 255, l = (mx + mn) / 2; let h = 0;
        if (mx !== mn) {
          const d = mx - mn, rr = r / 255, gg = g / 255, bb = bl / 255;
          if (mx === rr) h = ((gg - bb) / d + (gg < bb ? 6 : 0)); else if (mx === gg) h = (bb - rr) / d + 2; else h = (rr - gg) / d + 4; h *= 60;
        }
        b[Math.round(h) % 360].push({ ok: p.ok, l: l * 100 });
      });
      return b;
    })();
    const GAMUT_DE = 11;
    let SATCAP = null, SATCAP_L = -1;
    function buildSatCap() {
      if (SATCAP && Math.abs(SATCAP_L - light) < 0.5) return;
      SATCAP_L = light;
      const cands = Array.from({ length: 360 }, () => []);
      for (let h = 0; h < 360; h++) {
        let c = [];
        for (let dh = -40; dh <= 40; dh++) for (const p of HUEBUCKET[(h + dh + 360) % 360]) if (Math.abs(p.l - light) <= 25) c.push(p.ok);
        if (c.length < 10) { c = []; for (let dh = -40; dh <= 40; dh++) for (const p of HUEBUCKET[(h + dh + 360) % 360]) c.push(p.ok); }
        cands[h] = c;
      }
      const fitsAt = (h, s) => {
        const ok = rgbToOklab(...hslToRgb(h, s, light));
        let best = 1e9;
        for (const cl of cands[h]) { const d0 = ok[0] - cl[0], d1 = ok[1] - cl[1], d2 = ok[2] - cl[2]; const d = d0 * d0 + d1 * d1 + d2 * d2; if (d < best) best = d; }
        return 190 * Math.sqrt(best) <= GAMUT_DE;
      };
      const raw = new Float32Array(360);
      for (let h = 0; h < 360; h++) {
        let lo = 0, hi = 100;
        if (fitsAt(h, 100)) lo = 100; else for (let i = 0; i < 8; i++) { const mid = (lo + hi) / 2; if (fitsAt(h, mid)) lo = mid; else hi = mid; }
        raw[h] = Math.max(lo, 8);
      }
      const sm = new Float32Array(360);
      for (let h = 0; h < 360; h++) {
        let sum = 0, wsum = 0;
        for (let dh = -10; dh <= 10; dh++) { const w = 11 - Math.abs(dh); sum += raw[(h + dh + 360) % 360] * w; wsum += w; }
        sm[h] = sum / wsum;
      }
      for (let h = 0; h < 360; h++) { let s = sm[h], guard = 0; while (s > 8 && !fitsAt(h, s) && guard++ < 20) s -= 1.5; sm[h] = Math.max(s, 8); }
      const S = 1.2;
      for (let pass = 0; pass < 3; pass++) {
        for (let i = 1; i <= 720; i++) { const h = i % 360, p = (i - 1) % 360; if (sm[h] > sm[p] + S) sm[h] = sm[p] + S; }
        for (let i = 719; i >= 0; i--) { const h = i % 360, n = (i + 1) % 360; if (sm[h] > sm[n] + S) sm[h] = sm[n] + S; }
      }
      SATCAP = sm;
    }
    function satCapAt(h) { buildSatCap(); return SATCAP[((Math.round(h) % 360) + 360) % 360]; }

    function drawWheel() {
      buildSatCap();
      const img = ctx.createImageData(SIZE, SIZE);
      for (let y = 0; y < SIZE; y++) {
        for (let x = 0; x < SIZE; x++) {
          const dx = x - R, dy = y - R, dist = Math.sqrt(dx * dx + dy * dy), i = (y * SIZE + x) * 4;
          if (dist <= R) {
            const h = (Math.atan2(dy, dx) * 180 / Math.PI + 360) % 360;
            const s = radToSat(Math.min(dist / R, 1)) * satCapAt(h);
            const [r, g, b] = hslToRgb(h, s, light);
            img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = dist > R - 1.5 ? 255 * (R - dist + 0.5) : 255;
          } else img.data[i + 3] = 0;
        }
      }
      ctx.putImageData(img, 0, 0);
    }

    /* ---------- dial ---------- */
    (function () { const S = 360; dial.width = S; dial.height = S; dctx.scale(S / 180, S / 180); })();
    const DSIZE = 180, DC = DSIZE / 2, RING_R = 72, RING_W = 22, SWEEP = 270, START = 135;
    const lightToT = l => (l - 5) / 92;
    function drawDial() {
      dctx.clearRect(0, 0, DSIZE, DSIZE);
      for (let i = 0; i <= SWEEP; i += 2) {
        const t = i / SWEEP, L = 5 + t * 92, a0 = (START + i) * Math.PI / 180, a1 = (START + i + 2.4) * Math.PI / 180;
        dctx.beginPath(); dctx.arc(DC, DC, RING_R, a0, a1); dctx.lineWidth = RING_W;
        const [r, g, b] = hslToRgb(hue, sat, L);
        dctx.strokeStyle = `rgb(${r | 0},${g | 0},${b | 0})`; dctx.stroke();
      }
      // centre pot lid: the paint going on the wall
      const lid = paintHex || rgbToHex(...hslToRgb(hue, sat, light));
      dctx.beginPath(); dctx.arc(DC, DC, RING_R - RING_W / 2 - 8, 0, Math.PI * 2);
      dctx.fillStyle = lid; dctx.fill();
      dctx.lineWidth = 1; dctx.strokeStyle = 'rgba(0,0,0,.12)'; dctx.stroke();
      const ha = (START + lightToT(light) * SWEEP) * Math.PI / 180, hx = DC + Math.cos(ha) * RING_R, hy = DC + Math.sin(ha) * RING_R;
      const [cr, cg, cb] = hslToRgb(hue, sat, light);
      dctx.beginPath(); dctx.arc(hx, hy, 10, 0, Math.PI * 2);
      dctx.fillStyle = `rgb(${cr | 0},${cg | 0},${cb | 0})`; dctx.fill();
      dctx.lineWidth = 3; dctx.strokeStyle = '#fff'; dctx.stroke();
      dctx.lineWidth = 1; dctx.strokeStyle = 'rgba(0,0,0,.35)';
      dctx.beginPath(); dctx.arc(hx, hy, 11.5, 0, Math.PI * 2); dctx.stroke();
      dial.setAttribute('aria-valuenow', Math.round(light));
    }

    /* ---------- pointer ---------- */
    function place() {
      const cw = canvas.clientWidth, ch = canvas.clientHeight, scale = cw / SIZE;
      if (!cw) return;
      const rad = hue * Math.PI / 180, d = satToRad(Math.min(sat / satCapAt(hue), 1)) * R * scale;
      pointer.style.left = (canvas.offsetLeft + cw / 2 + Math.cos(rad) * d) + 'px';
      pointer.style.top = (canvas.offsetTop + ch / 2 + Math.sin(rad) * d) + 'px';
      pointer.style.background = paintHex || currentHex();
    }
    function currentHex() { return rgbToHex(...hslToRgb(hue, sat, light)); }

    /* ---------- input ---------- */
    let raf = null, wheelRaf = null;
    function moved() {
      place(); drawDial();
      if (raf) return;
      raf = requestAnimationFrame(() => { raf = null; o.onMove && o.onMove(currentHex()); });
    }
    function released() { if (raf) { cancelAnimationFrame(raf); raf = null; } o.onRelease && o.onRelease(currentHex()); }
    function pickFromEvent(e) {
      const rect = canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) * (SIZE / rect.width) - R, y = (e.clientY - rect.top) * (SIZE / rect.height) - R;
      hue = (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
      sat = radToSat(Math.min(Math.sqrt(x * x + y * y) / R, 1)) * satCapAt(hue);
      moved();
    }
    tapOrHold(canvas, pickFromEvent, released);
    canvas.addEventListener('keydown', e => {
      const k = e.key, big = e.shiftKey ? 5 : 1;
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(k)) return;
      e.preventDefault();
      if (k === 'ArrowLeft' || k === 'ArrowRight') hue = (hue + (k === 'ArrowRight' ? big : -big) + 360) % 360;
      else { const cap = satCapAt(hue), f = satToRad(Math.min(sat / cap, 1)); sat = radToSat(Math.max(0, Math.min(1, f + (k === 'ArrowUp' ? big : -big) / 100))) * cap; }
      place(); drawDial(); released();
    });

    function setLight(l) {
      light = Math.max(5, Math.min(97, l));
      if (!wheelRaf) wheelRaf = requestAnimationFrame(() => { drawWheel(); wheelRaf = null; place(); });
      moved();
    }
    function dialFromEvent(e) {
      const rect = dial.getBoundingClientRect();
      const x = (e.clientX - rect.left) * (DSIZE / rect.width) - DC, y = (e.clientY - rect.top) * (DSIZE / rect.height) - DC;
      let a = Math.atan2(y, x) * 180 / Math.PI; if (a < 0) a += 360;
      let ang = (a - START + 360) % 360;
      if (ang > SWEEP) ang = ang < SWEEP + (360 - SWEEP) / 2 ? SWEEP : 0;
      setLight(5 + (ang / SWEEP) * 92);
    }
    tapOrHold(dial, dialFromEvent, released);
    dial.addEventListener('keydown', e => {
      let d = 0;
      if (e.key === 'ArrowUp' || e.key === 'ArrowRight') d = 2; else if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') d = -2; else return;
      e.preventDefault(); light = Math.max(5, Math.min(97, light + d)); drawWheel(); place(); drawDial(); released();
    });

    /* halo of real paints around the wheel, aligned by hue (as the homepage) */
    if (o.ring) {
      const cand = o.hexes.map(hx => { const [h, s, l] = hexToHsl(hx); return { hex: hx, h, s: s / 100, l: l / 100 }; })
        .filter(p => p.s > 0.18 && p.l > 0.28 && p.l < 0.75);
      const SEG = 90, stops = [];
      for (let i = 0; i < SEG; i++) {
        const target = (i + 0.5) * 360 / SEG; let best = null, bs = 1e9;
        for (const p of cand) {
          let dh = Math.abs(p.h - target); if (dh > 180) dh = 360 - dh;
          const score = dh * 2.2 + Math.abs(p.l - 0.52) * 38 + (0.6 - Math.min(p.s, 0.6)) * 22;
          if (score < bs) { bs = score; best = p; }
        }
        stops.push(best.hex + ' ' + (i * 360 / SEG).toFixed(2) + 'deg ' + ((i + 1) * 360 / SEG).toFixed(2) + 'deg');
      }
      o.ring.style.background = 'conic-gradient(from 90deg, ' + stops.join(', ') + ')';
    }

    drawWheel(); drawDial();
    return {
      setFromHex(hx) { [hue, sat, light] = hexToHsl(hx); drawWheel(); drawDial(); place(); },
      setPaint(hx) { paintHex = hx; drawDial(); place(); },
      place, currentHex
    };
  }

  root.VisWheel = { create };
})(typeof self !== 'undefined' ? self : this);
