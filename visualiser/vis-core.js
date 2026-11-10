/* PaintDial visualiser: colour maths and matte handling, no DOM.
   Loaded by the page as a plain script (window.VisCore) and by the Node tests.

   The regrade is an albedo swap done in linear light. Each wall pixel keeps its
   brightness relative to the wall's average (that is the room's light and shade), and
   takes its colour from the paint. By default the wall then averages out at the paint's
   published colour. If the person says what the wall is painted now, the photo's light
   (exposure and colour cast) is measured against that colour and the new paint is lit
   the same way instead. */
(function (root) {
  'use strict';

  // ---------- colour basics ----------
  const S2L = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const v = i / 255; S2L[i] = v > 0.04045 ? Math.pow((v + 0.055) / 1.055, 2.4) : v / 12.92; }
  const L2S = new Uint8ClampedArray(4097);
  for (let i = 0; i <= 4096; i++) { const v = i / 4096; L2S[i] = Math.round(255 * (v > 0.0031308 ? 1.055 * Math.pow(v, 1 / 2.4) - 0.055 : 12.92 * v)); }
  function l2s(v) { return L2S[v <= 0 ? 0 : v >= 1 ? 4096 : (v * 4096 + 0.5) | 0]; }

  function rgb(h) { h = String(h || '').replace('#', ''); return [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16)); }
  function hexLin(h) { return rgb(h).map(c => S2L[c]); }
  function oklabLin(r, g, b) {
    const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b),
          m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b),
          s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function oklab(h) { const c = hexLin(h); return oklabLin(c[0], c[1], c[2]); }
  function lrv(h) { const c = hexLin(h); return 100 * (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]); }

  // ---------- the site's wording (mirrors pd-compare.js and diff_bits() in gen_pages.py) ----------
  function dist(a, b) {
    const p = oklab(a), q = oklab(b), cp = Math.hypot(p[1], p[2]), cq = Math.hypot(q[1], q[2]);
    let dh = Math.abs(Math.atan2(p[2], p[1]) - Math.atan2(q[2], q[1])); if (dh > Math.PI) dh = 2 * Math.PI - dh;
    const hh = 2 * Math.sqrt(Math.max(cp * cq, 0)) * Math.sin(dh / 2);
    return 190 * Math.sqrt(Math.pow((p[0] - q[0]) / 1.3, 2) + Math.pow(cp - cq, 2) + 4 * hh * hh);
  }
  function closenessWord(d) { return d < 2 ? 'near-identical' : d < 5 ? 'very close' : d < 10 ? 'close' : ''; }
  function diffBits(a, b) {
    const bits = [], dl = lrv(b) - lrv(a), pa = oklab(a), pb = oklab(b);
    if (Math.abs(dl) >= 1.5) {
      const pts = Math.round(Math.abs(dl));
      bits.push((Math.abs(dl) >= 4 ? 'noticeably ' : '') + (dl > 0 ? 'lighter' : 'darker') + ' (about ' + pts + ' LRV point' + (pts !== 1 ? 's' : '') + ')');
    }
    const db = pb[2] - pa[2];
    if (Math.abs(db) >= 0.010) bits.push((Math.abs(db) >= 0.020 ? 'noticeably ' : 'slightly ') + (db > 0 ? 'warmer' : 'cooler'));
    const dc = Math.hypot(pb[1], pb[2]) - Math.hypot(pa[1], pa[2]);
    if (Math.abs(dc) >= 0.010) bits.push((Math.abs(dc) >= 0.020 ? 'noticeably ' : 'slightly ') + (dc > 0 ? 'more saturated' : 'softer'));
    return bits;
  }
  function joinBits(b) { return b.length < 2 ? (b[0] || '') : b.slice(0, -1).join(', ') + ' and ' + b[b.length - 1]; }
  function diffSentence(a, b, aName, bName) {
    const bits = diffBits(a, b);
    if (!bits.length) return 'No real difference in lightness, warmth or saturation.';
    return bName + ' is ' + joinBits(bits) + ' than ' + aName + '.';
  }

  // ---------- the library ----------
  function baseSlug(n) {
    return n.normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase()
      .replace(/&/g, 'and').replace(/'/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  }
  /* data: {brands, sourced, c:[[bi,name,hex6,code],...]} in the master file's order, so the
     slugs (and their duplicate suffixes) come out the same as gen_pages.py's. */
  function buildLibrary(data) {
    const n = data.c.length, L = new Float32Array(n), C = new Float32Array(n), Hh = new Float32Array(n);
    const list = new Array(n), used = new Set();
    for (let i = 0; i < n; i++) {
      const [bi, name, h6, code] = data.c[i], hex = '#' + h6, brand = data.brands[bi];
      let slug = baseSlug(brand) + '-' + baseSlug(name);
      if (used.has(slug)) slug += '-' + h6.toLowerCase();
      used.add(slug);
      const o = oklab(hex);
      L[i] = o[0]; C[i] = Math.hypot(o[1], o[2]); Hh[i] = Math.atan2(o[2], o[1]);
      list[i] = { i, brand, bi, name, hex, code, slug, key: (name + ' ' + brand + ' ' + code).toLowerCase() };
    }
    return { list, L, C, H: Hh, brands: data.brands, sourced: data.sourced || {} };
  }
  /* The closest colour from each other brand, nearest first (the same distance the site ranks by). */
  function bestPerBrand(lib, i, limit) {
    const { L, C, H, list } = lib, n = list.length, li = L[i], ci = C[i], hi = H[i];
    const best = new Map();
    for (let j = 0; j < n; j++) {
      const bj = list[j].bi;
      if (bj === list[i].bi) continue;
      let dh = Math.abs(H[j] - hi); if (dh > Math.PI) dh = 2 * Math.PI - dh;
      const hh = 2 * Math.sqrt(Math.max(C[j] * ci, 0)) * Math.sin(dh / 2);
      const dl = (L[j] - li) / 1.3, dc = C[j] - ci;
      const d = 190 * Math.sqrt(dl * dl + dc * dc + 4 * hh * hh);
      const cur = best.get(bj);
      if (!cur || d < cur.d) best.set(bj, { j, d });
    }
    return [...best.values()].sort((a, b) => a.d - b.d).slice(0, limit || 99);
  }
  /* The n nearest paints to any colour (the site's match distance), optionally from one
     brand (bi) only. The wheel uses this so the wall only ever shows a real paint. */
  function nearestN(lib, hex, n, bi) {
    const { L, C, H, list } = lib, o = oklab(hex), li = o[0], ci = Math.hypot(o[1], o[2]), hi = Math.atan2(o[2], o[1]);
    const out = [];
    for (let j = 0; j < list.length; j++) {
      if (bi != null && bi >= 0 && list[j].bi !== bi) continue;
      let dh = Math.abs(H[j] - hi); if (dh > Math.PI) dh = 2 * Math.PI - dh;
      const hh = 2 * Math.sqrt(Math.max(C[j] * ci, 0)) * Math.sin(dh / 2);
      const dl = (L[j] - li) / 1.3, dc = C[j] - ci;
      const d = 190 * Math.sqrt(dl * dl + dc * dc + 4 * hh * hh);
      if (out.length < n || d < out[out.length - 1].d) {
        out.push({ j, d }); out.sort((a, b) => a.d - b.d); if (out.length > n) out.pop();
      }
    }
    return out;
  }
  function search(lib, q, limit) {
    q = q.trim().toLowerCase().replace(/’/g, "'");
    if (!q) return [];
    const words = q.split(/\s+/), out = [];
    for (const c of lib.list) {
      const k = c.key.replace(/’/g, "'");
      if (words.every(w => k.includes(w))) {
        // names that start with the query come first
        const score = (c.name.toLowerCase().startsWith(q) ? 0 : 1) + c.name.length / 1000;
        out.push([score, c]);
      }
    }
    out.sort((a, b) => a[0] - b[0]);
    return out.slice(0, limit || 30).map(x => x[1]);
  }

  // ---------- photo preparation ----------
  function boxMean(src, w, h, r, out) {
    // Separable box mean with the window clipped at the edges (prefix sums in float64).
    const tmp = new Float32Array(w * h), row = new Float64Array(w + 1), col = new Float64Array(h + 1);
    for (let y = 0; y < h; y++) {
      const o = y * w; row[0] = 0;
      for (let x = 0; x < w; x++) row[x + 1] = row[x] + src[o + x];
      for (let x = 0; x < w; x++) {
        const a = x - r < 0 ? 0 : x - r, b = x + r + 1 > w ? w : x + r + 1;
        tmp[o + x] = (row[b] - row[a]) / (b - a);
      }
    }
    for (let x = 0; x < w; x++) {
      col[0] = 0;
      for (let y = 0; y < h; y++) col[y + 1] = col[y] + tmp[y * w + x];
      for (let y = 0; y < h; y++) {
        const a = y - r < 0 ? 0 : y - r, b = y + r + 1 > h ? h : y + r + 1;
        out[y * w + x] = (col[b] - col[a]) / (b - a);
      }
    }
    return out;
  }

  function prepare(rgba, w, h) {
    const N = w * h, lin = new Float32Array(N * 3), Y = new Float32Array(N), I = new Float32Array(N);
    for (let i = 0, k = 0; i < N; i++, k += 4) {
      const r = S2L[rgba[k]], g = S2L[rgba[k + 1]], b = S2L[rgba[k + 2]];
      lin[i * 3] = r; lin[i * 3 + 1] = g; lin[i * 3 + 2] = b;
      const y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      Y[i] = y; I[i] = Math.cbrt(y); // guide: perceptual lightness
    }
    const r = Math.max(2, Math.round(Math.max(w, h) / 360));
    const meanI = boxMean(I, w, h, r, new Float32Array(N));
    const II = new Float32Array(N); for (let i = 0; i < N; i++) II[i] = I[i] * I[i];
    const varI = boxMean(II, w, h, r, new Float32Array(N));
    for (let i = 0; i < N; i++) varI[i] -= meanI[i] * meanI[i];
    return { w, h, N, src: rgba, lin, Y, I, meanI, varI, r, eps: 0.0012 };
  }

  // ---------- matte ----------
  /* SAM returns 256x256 logits covering the photo scaled to fit 1024 (lw x lh of them are
     the photo, the rest padding). Several selections are combined by taking the highest
     logit, then sampled up to the photo and turned into a soft matte. */
  function softFromLogits(prep, regions) {
    const { w, h, N } = prep, p = new Float32Array(N);
    const live = regions.filter(r => r.logits);
    if (!live.length) return p;
    const lw = live[0].lw, lh = live[0].lh;
    const comb = new Float32Array(256 * 256).fill(-30);
    for (const r of live) for (let i = 0; i < comb.length; i++) if (r.logits[i] > comb[i]) comb[i] = r.logits[i];
    const sx = lw / w, sy = lh / h;
    for (let y = 0; y < h; y++) {
      let v = (y + 0.5) * sy - 0.5; if (v < 0) v = 0; if (v > 255) v = 255;
      const y0 = v | 0, y1 = y0 < 255 ? y0 + 1 : 255, fy = v - y0;
      for (let x = 0; x < w; x++) {
        let u = (x + 0.5) * sx - 0.5; if (u < 0) u = 0; if (u > 255) u = 255;
        const x0 = u | 0, x1 = x0 < 255 ? x0 + 1 : 255, fx = u - x0;
        const a = comb[y0 * 256 + x0] * (1 - fx) + comb[y0 * 256 + x1] * fx;
        const b = comb[y1 * 256 + x0] * (1 - fx) + comb[y1 * 256 + x1] * fx;
        const l = a * (1 - fy) + b * fy;
        p[y * w + x] = 1 / (1 + Math.exp(-l));
      }
    }
    return p;
  }
  function logitAt(region, nx, ny) {
    if (!region.logits) return -30;
    const u = Math.min(255, Math.max(0, nx * region.lw - 0.5)), v = Math.min(255, Math.max(0, ny * region.lh - 0.5));
    return region.logits[Math.round(v) * 256 + Math.round(u)];
  }

  /* Guided filter (He et al.) with the photo's lightness as the guide: the model's edge,
     which is soft at 1/4 resolution, is pulled onto the real edges in the photo. Then the
     result is tightened back into a clean matte. */
  function refine(prep, p) {
    const { w, h, N, I, meanI, varI, r, eps } = prep;
    const meanP = boxMean(p, w, h, r, new Float32Array(N));
    const Ip = new Float32Array(N); for (let i = 0; i < N; i++) Ip[i] = I[i] * p[i];
    const corrIp = boxMean(Ip, w, h, r, Ip);
    const a = new Float32Array(N), b = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      const ai = (corrIp[i] - meanI[i] * meanP[i]) / (varI[i] + eps);
      a[i] = ai; b[i] = meanP[i] - ai * meanI[i];
    }
    const ma = boxMean(a, w, h, r, a), mb = boxMean(b, w, h, r, b);
    const out = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      let q = ma[i] * I[i] + mb[i];
      q = (q - 0.25) / 0.5; q = q < 0 ? 0 : q > 1 ? 1 : q;
      out[i] = q * q * (3 - 2 * q);
    }
    return out;
  }

  // ---------- regrade ----------
  /* The wall's reference brightness (a trimmed mean, so a lamp's hotspot or a missed
     socket doesn't skew it) and its average linear colour. */
  function wallStats(prep, alpha) {
    const { N, Y, lin } = prep;
    let maxY = 0, cnt = 0;
    for (let i = 0; i < N; i++) if (alpha[i] > 0.5) { cnt++; if (Y[i] > maxY) maxY = Y[i]; }
    if (!cnt || maxY <= 0) return null;
    const bins = 1024, hist = new Uint32Array(bins), k = (bins - 1) / maxY;
    for (let i = 0; i < N; i++) if (alpha[i] > 0.5) hist[(Y[i] * k) | 0]++;
    let lo = 0, hi = bins - 1, acc = 0;
    const cut = cnt * 0.03;
    for (acc = 0; lo < bins && acc + hist[lo] < cut; lo++) acc += hist[lo];
    for (acc = 0; hi > 0 && acc + hist[hi] < cut; hi--) acc += hist[hi];
    const yLo = lo / k, yHi = (hi + 1) / k;
    let sy = 0, sr = 0, sg = 0, sb = 0, n = 0;
    for (let i = 0; i < N; i++) {
      if (alpha[i] <= 0.5 || Y[i] < yLo || Y[i] > yHi) continue;
      sy += Y[i]; sr += lin[i * 3]; sg += lin[i * 3 + 1]; sb += lin[i * 3 + 2]; n++;
    }
    if (!n) return null;
    const Yref = sy / n;
    // How the wall's brightness spreads around its reference, for the exposure solve below.
    const sCnt = new Float64Array(256), sSum = new Float64Array(256);
    for (let i = 0; i < N; i++) {
      if (alpha[i] <= 0.5) continue;
      const s = Y[i] / Yref, b = s >= 4 ? 255 : (s * 64) | 0;
      sCnt[b]++; sSum[b] += s;
    }
    const sb_ = [], sc_ = [];
    for (let b = 0; b < 256; b++) if (sCnt[b]) { sb_.push(sSum[b] / sCnt[b]); sc_.push(sCnt[b]); }
    return { Yref, mean: [sr / n, sg / n, sb / n], count: cnt, sVal: sb_, sCnt: sc_ };
  }

  function shoulder(v) { return v <= 0.82 ? v : 0.82 + 0.18 * (1 - Math.exp(-(v - 0.82) / 0.18)); }

  /* The highlight roll-off pulls the average of a light colour down, so solve for the
     exposure that brings the wall's average back to the target exactly (bisection over
     the brightness spread). */
  function solveExposure(T, stats) {
    if (T <= 0) return 1;
    const v = stats.sVal, c = stats.sCnt;
    let tot = 0; for (let i = 0; i < c.length; i++) tot += c[i];
    const f = (k) => { let m = 0; for (let i = 0; i < v.length; i++) m += c[i] * shoulder(T * k * v[i]); return m / tot; };
    let lo = 0.25, hi = 6;
    if (f(hi) < T) return hi;
    for (let it = 0; it < 32; it++) { const mid = (lo + hi) / 2; if (f(mid) < T) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }

  /* paintHex: the new colour. currentHex: what the wall is painted now, or null. */
  function regrade(prep, alpha, stats, paintHex, currentHex, out) {
    const { N, Y, lin, src } = prep;
    const P = hexLin(paintHex);
    let gain = [1, 1, 1];
    if (currentHex) {
      const cur = hexLin(currentHex);
      // The photo's light on the wall, per channel: what the camera recorded over what the paint is.
      gain = [0, 1, 2].map(c => stats.mean[c] / Math.max(cur[c], 1e-4));
    }
    const T = [0, 1, 2].map(c => { const t = P[c] * gain[c]; return t * solveExposure(t, stats); });
    const inv = 1 / stats.Yref;
    for (let i = 0, k = 0; i < N; i++, k += 4) {
      const a = alpha[i];
      if (a < 0.003) { out[k] = src[k]; out[k + 1] = src[k + 1]; out[k + 2] = src[k + 2]; out[k + 3] = 255; continue; }
      const s = Y[i] * inv, j = i * 3;
      const r = shoulder(T[0] * s), g = shoulder(T[1] * s), b = shoulder(T[2] * s);
      out[k] = l2s(lin[j] + (r - lin[j]) * a);
      out[k + 1] = l2s(lin[j + 1] + (g - lin[j + 1]) * a);
      out[k + 2] = l2s(lin[j + 2] + (b - lin[j + 2]) * a);
      out[k + 3] = 255;
    }
    return out;
  }

  const api = { hexLin, oklab, lrv, dist, closenessWord, diffSentence, baseSlug, buildLibrary, bestPerBrand, nearestN, search,
                boxMean, prepare, softFromLogits, logitAt, refine, wallStats, regrade, l2s };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.VisCore = api;
})(typeof self !== 'undefined' ? self : this);
