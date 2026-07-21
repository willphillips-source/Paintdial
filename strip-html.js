export default (request, context) => {
  const url = new URL(request.url);
  const p = url.pathname;
  if (!p.endsWith(".html")) return context.next();
  let next;
  if (p === "/index.html") {
    next = "/";
  } else if (p.endsWith("/index.html")) {
    next = p.slice(0, -"index.html".length);
  } else {
    next = p.slice(0, -".html".length);
  }
  if (next === p || next.endsWith(".html")) return context.next();
  url.pathname = next;
  return Response.redirect(url.toString(), 301);
};

export const config = {
  pattern: "^/.+\\.html$",
  excludedPattern: ["^/impact-site-verification\\.html$", "^/404\\.html$"],
  onError: "bypass",
};
