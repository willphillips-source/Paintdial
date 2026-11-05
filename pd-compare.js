/* PaintDial compare view
   Tap the expand button on a match card and the two colours fill the screen,
   touching, with a seam you can drag (or tap anywhere to move it). One file
   shared by the homepage tool and every generated page, so the behaviour can't
   drift between them. The trigger button is plain HTML on the card; this script
   only listens for it, so it can load deferred and cards can be rendered before
   it runs. No divider line along the seam, on purpose: if you can't find the
   seam, that's the answer. */
(function () {
  'use strict';
  var CSS =
    '#pd-cmp{position:fixed;inset:0;z-index:1000;overflow:hidden;touch-action:none;-webkit-user-select:none;user-select:none;font-family:"Archivo",-apple-system,"Segoe UI",Roboto,sans-serif;color:#211F1B;--x:50%}' +
    '#pd-cmp[hidden]{display:none}' +
    '.pd-cmp-pane{position:absolute;top:0;bottom:0;overflow:hidden;container-type:inline-size}' +
    /* A label disappears once its pane is too narrow to show it (and, on the right,
       once it would collide with the close button). Browsers without container
       queries just truncate it instead. */
    '@container (max-width:118px){.pd-cmp-a .pd-cmp-lbl{display:none}}' +
    '@container (max-width:176px){.pd-cmp-b .pd-cmp-lbl{display:none}}' +
    '.pd-cmp-a{left:0;right:calc(100% - var(--x))}' +
    '.pd-cmp-b{left:var(--x);right:0}' +
    '.pd-cmp-lbl{position:absolute;top:12px;max-width:min(calc(100% - 20px),260px);background:rgba(255,255,255,.88);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);border-radius:9px;padding:6px 9px;line-height:1.2;pointer-events:none;box-shadow:0 1px 3px rgba(0,0,0,.14)}' +
    '.pd-cmp-a .pd-cmp-lbl{right:10px;text-align:right}' +
    '.pd-cmp-b .pd-cmp-lbl{left:10px;max-width:min(calc(100% - 66px),260px)}' +
    '.pd-cmp-lbl b{display:block;font-family:"Fraunces Amp","Fraunces",Georgia,serif;font-weight:600;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.pd-cmp-lbl small{display:block;font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;color:#665F54;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.pd-cmp-h{position:absolute;left:var(--x);top:50%;width:42px;height:42px;transform:translate(-50%,-50%);border-radius:50%;background:rgba(255,255,255,.9);box-shadow:0 2px 10px rgba(0,0,0,.28);display:flex;align-items:center;justify-content:center;cursor:ew-resize;color:#211F1B}' +
    '.pd-cmp-h:focus-visible{outline:2px solid #5E7E8B;outline-offset:2px}' +
    '.pd-cmp-h svg{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}' +
    '.pd-cmp-x{position:absolute;top:12px;right:10px;width:36px;height:36px;border:none;border-radius:50%;background:rgba(255,255,255,.88);-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);box-shadow:0 1px 3px rgba(0,0,0,.14);cursor:pointer;display:flex;align-items:center;justify-content:center;color:#211F1B;padding:0;font-family:inherit}' +
    '.pd-cmp-x:focus-visible{outline:2px solid #5E7E8B;outline-offset:2px}' +
    '.pd-cmp-x svg{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}' +
    '.pd-cmp-s{position:absolute;left:0;right:0;bottom:0;background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);padding:10px 16px max(12px,env(safe-area-inset-bottom));display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:6px 12px;text-align:center;touch-action:auto}' +
    '.pd-cmp-word{font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#211F1B;border:1px solid #E3DFD5;border-radius:99px;padding:4px 10px;background:#F7F5F0;white-space:nowrap}' +
    '.pd-cmp-word:empty{display:none}' +
    '.pd-cmp-diff{font-size:13px;color:#211F1B;line-height:1.4;flex-basis:100%}' +
    '.pd-cmp-diff:empty{display:none}' +
    '.pd-cmp-note{font-size:12px;color:#665F54;line-height:1.4}';

  /* How the right-hand colour differs from the left, in the same measured words as the
     alternatives pages (diff_bits() in gen_pages.py, which this mirrors): lighter or darker
     in LRV points, warmer or cooler on OKLab's yellow-blue axis, more saturated or softer
     on OKLab chroma. "Slightly" and "noticeably" are the 75th and 90th percentiles of real
     close-match pairs, so the wording is measured, not guessed. */
  function lin(v) { v /= 255; return v > 0.04045 ? Math.pow((v + 0.055) / 1.055, 2.4) : v / 12.92; }
  function rgb(h) { h = String(h || '').replace('#', ''); return [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function oklab(h) {
    var c = rgb(h).map(lin), r = c[0], g = c[1], b = c[2];
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b),
        m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b),
        s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function lrv(h) { var c = rgb(h).map(lin); return 100 * (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]); }
  // The site's match distance: hue weighted twice, lightness discounted (dmatch() in gen_pages.py).
  function dist(a, b) {
    var p = oklab(a), q = oklab(b), cp = Math.hypot(p[1], p[2]), cq = Math.hypot(q[1], q[2]);
    var dh = Math.abs(Math.atan2(p[2], p[1]) - Math.atan2(q[2], q[1])); if (dh > Math.PI) dh = 2 * Math.PI - dh;
    var hh = 2 * Math.sqrt(Math.max(cp * cq, 0)) * Math.sin(dh / 2);
    return 190 * Math.sqrt(Math.pow((p[0] - q[0]) / 1.3, 2) + Math.pow(cp - cq, 2) + 4 * hh * hh);
  }
  function closeness(a, b) { var d = dist(a, b); return d < 2 ? 'near-identical' : d < 5 ? 'very close' : d < 10 ? 'close' : ''; }
  function diffBits(a, b) {
    var bits = [], dl = lrv(b) - lrv(a), pa = oklab(a), pb = oklab(b);
    if (Math.abs(dl) >= 1.5) {
      var pts = Math.round(Math.abs(dl));
      bits.push((Math.abs(dl) >= 4 ? 'noticeably ' : '') + (dl > 0 ? 'lighter' : 'darker') + ' (about ' + pts + ' LRV point' + (pts !== 1 ? 's' : '') + ')');
    }
    var db = pb[2] - pa[2];
    if (Math.abs(db) >= 0.010) bits.push((Math.abs(db) >= 0.020 ? 'noticeably ' : 'slightly ') + (db > 0 ? 'warmer' : 'cooler'));
    var dc = Math.hypot(pb[1], pb[2]) - Math.hypot(pa[1], pa[2]);
    if (Math.abs(dc) >= 0.010) bits.push((Math.abs(dc) >= 0.020 ? 'noticeably ' : 'slightly ') + (dc > 0 ? 'more saturated' : 'softer'));
    return bits;
  }
  function joinBits(b) { return b.length < 2 ? (b[0] || '') : b.slice(0, -1).join(', ') + ' and ' + b[b.length - 1]; }
  function diffSentence(a, b, aName, bName) {
    var bits = diffBits(a, b), them = aName === 'Your colour' ? 'your colour' : aName;
    if (!bits.length) return 'No real difference in lightness, warmth or saturation.';
    return bName + ' is ' + joinBits(bits) + ' than ' + them + '.';
  }

  /* Brands whose values come from a stockist because the brand publishes none, as
     brand: stockist. Must match SOURCE_NOTE in gen_pages.py, which asserts it on every
     build. When either side of the comparison is one of these, the strip says so. */
  var SOURCED = {"Zoffany": "Brewers", "Sanderson": "Brewers"};
  var BASE_NOTE = 'Screens vary. Compare these two to each other, then order testers before you buy.';

  var ov = null, handle = null, wordEl = null, diffEl = null, noteEl = null, lastBtn = null, x = 50, dragging = false;

  function build() {
    var st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);

    ov = document.createElement('div');
    ov.id = 'pd-cmp';
    ov.setAttribute('role', 'dialog');
    ov.setAttribute('aria-modal', 'true');
    ov.hidden = true;
    ov.innerHTML =
      '<div class="pd-cmp-pane pd-cmp-a"><div class="pd-cmp-lbl"><b></b><small></small></div></div>' +
      '<div class="pd-cmp-pane pd-cmp-b"><div class="pd-cmp-lbl"><b></b><small></small></div></div>' +
      '<div class="pd-cmp-h" role="slider" tabindex="0" aria-label="Seam between the two colours: drag, or use the arrow keys" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50">' +
        '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M9 7l-5 5 5 5M15 7l5 5-5 5"/></svg></div>' +
      '<button class="pd-cmp-x" type="button" aria-label="Close the comparison" title="Close">' +
        '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button>' +
      '<div class="pd-cmp-s"><span class="pd-cmp-word"></span>' +
        '<span class="pd-cmp-diff"></span><span class="pd-cmp-note"></span></div>';
    document.body.appendChild(ov);
    handle = ov.querySelector('.pd-cmp-h');
    wordEl = ov.querySelector('.pd-cmp-word');
    noteEl = ov.querySelector('.pd-cmp-note');
    diffEl = ov.querySelector('.pd-cmp-diff');

    // The seam follows your finger: press anywhere on the colours and it jumps
    // there, keep moving and it follows. Pointer capture keeps the drag alive
    // even if the finger leaves the window.
    ov.addEventListener('pointerdown', function (e) {
      if (e.target.closest('.pd-cmp-x, .pd-cmp-s')) return;
      if (e.button !== undefined && e.button !== 0) return;
      dragging = true;
      try { ov.setPointerCapture(e.pointerId); } catch (err) {}
      setX(e.clientX);
      e.preventDefault();
    });
    ov.addEventListener('pointermove', function (e) { if (dragging) setX(e.clientX); });
    ov.addEventListener('pointerup', function () { dragging = false; });
    ov.addEventListener('pointercancel', function () { dragging = false; });

    handle.addEventListener('keydown', function (e) {
      var step = e.shiftKey ? 20 : 5, nx = null;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') nx = x - step;
      else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') nx = x + step;
      else if (e.key === 'Home') nx = 0;
      else if (e.key === 'End') nx = 100;
      if (nx === null) return;
      e.preventDefault();
      setPct(nx);
    });

    ov.querySelector('.pd-cmp-x').addEventListener('click', close);
  }

  function setX(clientX) {
    var w = ov.clientWidth || window.innerWidth || 1;
    setPct(clientX / w * 100);
  }
  function setPct(p) {
    x = Math.max(0, Math.min(100, p));
    ov.style.setProperty('--x', x + '%');
    handle.setAttribute('aria-valuenow', String(Math.round(x)));
  }

  function fill(sel, name, sub) {
    var el = ov.querySelector(sel);
    el.querySelector('b').textContent = name;
    el.querySelector('small').textContent = sub;
  }

  function open(btn) { openPair(btn.dataset, btn); }

  /* Open any two colours. d has ahex/aname/abrand and bhex/bname/bbrand, and optionally
     word (the closeness label the card already showed); returnEl gets focus back on close.
     The shortlist uses this to compare two saved colours. */
  function openPair(d, returnEl) {
    if (!ov) build();
    var aName = d.aname || 'Your colour', bName = d.bname || 'Match';
    ov.querySelector('.pd-cmp-a').style.background = d.ahex;
    ov.querySelector('.pd-cmp-b').style.background = d.bhex;
    fill('.pd-cmp-a', aName, d.abrand || d.ahex || '');
    fill('.pd-cmp-b', bName, d.bbrand || d.bhex || '');
    var w = (d.word || closeness(d.ahex, d.bhex) || '').trim();
    wordEl.textContent = w ? w.charAt(0).toUpperCase() + w.slice(1) : '';
    var src = [];
    [d.abrand, d.bbrand].forEach(function (b) {
      if (b && SOURCED.hasOwnProperty(b) && src.indexOf(b) < 0) src.push(b);
    });
    diffEl.textContent = diffSentence(d.ahex, d.bhex, aName, bName);
    noteEl.textContent = BASE_NOTE + src.map(function (b) {
      return ' ' + b + '’s values come from its stockist ' + SOURCED[b] + ', as ' + b + ' publishes none.';
    }).join('');
    ov.setAttribute('aria-label', 'Comparing ' + aName + ' with ' + bName + ' full screen');
    setPct(50);
    lastBtn = returnEl || null;
    ov.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    var xb = ov.querySelector('.pd-cmp-x');
    try { xb.focus({ preventScroll: true }); } catch (err) { xb.focus(); }
  }

  function close() {
    if (!ov || ov.hidden) return;
    ov.hidden = true;
    dragging = false;
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
    if (lastBtn && lastBtn.nodeType === 1 && document.contains(lastBtn)) {
      try { lastBtn.focus({ preventScroll: true }); } catch (err) {}
    }
    lastBtn = null;
  }

  // Event delegation: cards are rendered and re-rendered by other code, so the
  // trigger is found at click time rather than bound when it appears.
  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.pd-cmp-btn') : null;
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    open(b);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && ov && !ov.hidden) { e.preventDefault(); close(); }
  });

  window.PDCompare = { open: open, openPair: openPair, close: close, diffSentence: diffSentence };
})();
