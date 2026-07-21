/* PaintDial — 301 the legacy .html URLs to their canonical extensionless twins.
 *
 * WHY THIS EXISTS
 * Netlify serves `colours/foo.html` at BOTH /colours/foo and /colours/foo.html, so every
 * page has a duplicate. Netlify's "Pretty URLs" post-processing does NOT fix this: it
 * rewrites hrefs inside HTML at build time, and PaintDial's HTML already links cleanly,
 * so it is a no-op here (verified live: both forms return 200).
 *
 * WHY NOT _redirects
 * Explicit rules work (all 6,442 verified against netlify-redirector, Netlify's real
 * engine) but the engine scans rules top-to-bottom and a CLEAN url matches nothing —
 * so it scans all 6,442. Measured linear: 0.075ms @5 rules -> 28ms @6,442. That taxes
 * every human visitor to fix crawling by bots. An edge function scoped by `pattern` to
 * .html only is O(1) and never runs for clean URLs.
 *
 * SAFETY
 * - The endsWith('.html') guard means even a too-broad pattern cannot cause a loop.
 * - Never redirects to a path that still ends in .html.
 * - onError:"bypass" — if this throws, Netlify skips it and serves as it does today.
 */
export default (request, context) => {
  const url = new URL(request.url);
  const p = url.pathname;

  // Guard: only ever touch .html. Anything else passes straight through untouched.
  if (!p.endsWith(".html")) return context.next();

  let next;
  if (p === "/index.html") {
    next = "/";                                        // NOT "/index" (would 404)
  } else if (p.endsWith("/index.html")) {
    next = p.slice(0, -"index.html".length);           // /colours/index.html -> /colours/
  } else {
    next = p.slice(0, -".html".length);                // /colours/foo.html  -> /colours/foo
  }

  // Belt and braces: never loop, never emit another .html
  if (next === p || next.endsWith(".html")) return context.next();

  url.pathname = next;                                 // query string is preserved by URL
  return Response.redirect(url.toString(), 301);
};

export const config = {
  pattern: "^/.+\\.html$",
  excludedPattern: [
    "^/impact-site-verification\\.html$",   // affiliate verification fetches this exact URL
    "^/404\\.html$",
  ],
  onError: "bypass",
};
