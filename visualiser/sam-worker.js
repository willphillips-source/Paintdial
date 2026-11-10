/* PaintDial visualiser: the wall finder.
   Runs SlimSAM (a 100x-compressed Segment Anything) in a worker so the page stays
   responsive. The photo never leaves the device: the model files download once from
   Hugging Face and the browser keeps them; the photo is only ever processed here.

   Messages in:  {type:'load'} | {type:'embed', id, rgb, width, height} | {type:'decode', id, points:[{x,y,l}]}
   Messages out: {type:'progress', loaded, total} | {type:'ready', device, dtype}
                 {type:'embedded', id, ms} | {type:'mask', id, logits, lw, lh, iou, ms} | {type:'error', where, message} */
import { SamModel, AutoProcessor, RawImage, Tensor, env } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.1';

env.allowLocalModels = false;
const MODEL = 'Xenova/slimsam-77-uniform';

let model = null, processor = null, inputs = null, emb = null, embId = null;
let config = null, configs = [], loading = null;
const files = {};

function progress(info) {
  if (info.status !== 'progress' || !info.file) return;
  files[info.file] = { loaded: info.loaded || 0, total: info.total || 0 };
  let loaded = 0, total = 0;
  for (const k in files) { loaded += files[k].loaded; total += files[k].total; }
  postMessage({ type: 'progress', loaded, total });
}

async function candidates() {
  const list = [];
  try {
    if (self.navigator && navigator.gpu) {
      const ad = await navigator.gpu.requestAdapter();
      if (ad) list.push({ device: 'webgpu', dtype: ad.features.has('shader-f16') ? 'fp16' : 'fp32' });
    }
  } catch (e) { /* no WebGPU here */ }
  list.push({ device: 'wasm', dtype: 'q8' });
  return list;
}

async function loadWith(cfg) {
  if (model) { try { await model.dispose(); } catch (e) {} }
  model = await SamModel.from_pretrained(MODEL, { device: cfg.device, dtype: cfg.dtype, progress_callback: progress });
  if (!processor) processor = await AutoProcessor.from_pretrained(MODEL, { progress_callback: progress });
  config = cfg;
}

async function load() {
  if (loading) return loading;
  loading = (async () => {
    configs = await candidates();
    let lastErr = null;
    while (configs.length) {
      const cfg = configs.shift();
      try { await loadWith(cfg); postMessage({ type: 'ready', device: cfg.device, dtype: cfg.dtype }); return; }
      catch (e) { lastErr = e; }
    }
    throw lastErr || new Error('No way to run the model on this device');
  })();
  return loading;
}

// If the GPU path loads but fails when it runs, drop to the next option and retry once.
async function withFallback(fn) {
  try { return await fn(); }
  catch (e) {
    if (!configs.length) throw e;
    const cfg = configs.shift();
    await loadWith(cfg);
    postMessage({ type: 'ready', device: cfg.device, dtype: cfg.dtype, fellBack: true });
    return await fn();
  }
}

async function embed(msg) {
  await load();
  const t0 = performance.now();
  const image = new RawImage(new Uint8ClampedArray(msg.rgb), msg.width, msg.height, 3);
  await withFallback(async () => {
    inputs = await processor(image);
    emb = await model.get_image_embeddings(inputs);
  });
  embId = msg.id;
  postMessage({ type: 'embedded', id: msg.id, ms: Math.round(performance.now() - t0) });
}

async function decode(msg) {
  if (!emb || embId !== msg.id) { postMessage({ type: 'stale', id: msg.id, rk: msg.rk }); return; } // the photo changed
  const t0 = performance.now();
  const [rh, rw] = inputs.reshaped_input_sizes[0];
  const pts = msg.points;
  const input_points = new Tensor('float32', Float32Array.from(pts.flatMap(p => [p.x * rw, p.y * rh])), [1, 1, pts.length, 2]);
  const input_labels = new Tensor('int64', BigInt64Array.from(pts.map(p => BigInt(p.l))), [1, 1, pts.length]);
  let out = await model({ ...emb, input_points, input_labels });
  let masks = out.pred_masks, scores = out.iou_scores;
  if (masks.type !== 'float32') masks = masks.to('float32');
  if (scores.type !== 'float32') scores = scores.to('float32');
  const iou = Array.from(scores.data);
  // SAM gives three candidate masks. Among those scoring within 0.03 of the best, take
  // the largest: on a wall the smaller candidates are usually a patch of it.
  const n = 256 * 256, top = Math.max(...iou);
  let best = iou.indexOf(top), bestArea = -1;
  for (let k = 0; k < iou.length; k++) {
    if (iou[k] < top - 0.03) continue;
    let area = 0;
    for (let i = k * n, end = i + n; i < end; i++) if (masks.data[i] > 0) area++;
    if (area > bestArea) { bestArea = area; best = k; }
  }
  const logits = masks.data.slice(best * n, best * n + n);
  postMessage({ type: 'mask', id: msg.id, rk: msg.rk, logits, lw: rw / 4, lh: rh / 4, iou: iou[best], ms: Math.round(performance.now() - t0) }, [logits.buffer]);
}

// One message at a time, so a decode never runs against a half-built photo.
let chain = Promise.resolve();
self.onmessage = (e) => { chain = chain.then(() => handle(e.data)); };
async function handle(msg) {
  try {
    if (msg.type === 'load') await load();
    else if (msg.type === 'embed') await embed(msg);
    else if (msg.type === 'decode') await decode(msg);
  } catch (err) {
    postMessage({ type: 'error', where: msg.type, message: String(err && err.message || err) });
  }
}
