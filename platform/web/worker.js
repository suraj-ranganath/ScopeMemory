const API_ROUTE_PREFIXES = [
  "/auth/",
  "/admin/",
  "/demo/",
  "/fixtures/",
  "/iam/",
  "/index/",
  "/mcp/",
  "/mock-iam/",
  "/codex/"
];

const API_ROUTE_EXACT = new Set(["/health", "/mcp"]);

function shouldProxy(pathname) {
  return API_ROUTE_EXACT.has(pathname) || API_ROUTE_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

function responseWithProxyHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set("x-scopememory-proxy", "cloudflare-worker");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

export default {
  async fetch(request, env) {
    const source = new URL(request.url);
    if (!shouldProxy(source.pathname)) {
      return new Response("Not found", { status: 404 });
    }

    const apiOrigin = env.SCOPEMEMORY_API_ORIGIN;
    if (!apiOrigin || apiOrigin.includes("replace-with")) {
      return Response.json({ error: "SCOPEMEMORY_API_ORIGIN is not configured" }, { status: 502 });
    }

    const target = new URL(source.pathname + source.search, apiOrigin);
    const headers = new Headers(request.headers);
    headers.delete("host");

    try {
      const upstream = await fetch(target, {
        method: request.method,
        headers,
        body: request.body,
        redirect: "manual"
      });
      return responseWithProxyHeaders(upstream);
    } catch (error) {
      return Response.json(
        {
          error: "ScopeMemory backend tunnel is unreachable",
          detail: error instanceof Error ? error.message : String(error)
        },
        { status: 502 }
      );
    }
  }
};
