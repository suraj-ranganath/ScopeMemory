import { STATIC_DEMO_SNAPSHOT } from "./static-demo-snapshot.js";

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

function snapshotJson(value, status = 200) {
  return Response.json(value, {
    status,
    headers: {
      "cache-control": "public, max-age=30",
      "x-scopememory-mode": "static-snapshot",
      "x-scopememory-snapshot-captured-at": STATIC_DEMO_SNAPSHOT.captured_at
    }
  });
}

async function requestBody(request) {
  try {
    return await request.json();
  } catch {
    return {};
  }
}

function staticToolResult(toolName) {
  const state = STATIC_DEMO_SNAPSHOT.uiState;
  if (toolName === "linear.create_issue") {
    return {
      status: "simulated",
      tool: toolName,
      issue: {
        issue_id: "SM-STATIC-ACME",
        team_id: "linear_team:SALES",
        title: "Acme renewal follow-up",
        state: "open",
        source: "static_demo_snapshot"
      },
      note: "Static snapshot mode: no external Linear write was performed."
    };
  }
  if (toolName === "slack.search_messages") {
    return {
      status: "simulated",
      tool: toolName,
      messages: state.demo_apps?.slack?.messages || [],
      note: "Static snapshot mode: no live Slack read was performed."
    };
  }
  if (toolName === "slack.post_message") {
    return {
      status: "denied",
      tool: toolName,
      decision: "DENY",
      reason: "External Slack writes remain blocked in the static demo snapshot.",
      note: "Static snapshot mode: no external Slack write was performed."
    };
  }
  return {
    status: "simulated",
    tool: toolName || "unknown",
    note: "Static snapshot mode: no live MCP tool call was performed."
  };
}

async function staticMcpResponse(request) {
  const body = await requestBody(request);
  const toolName = body?.params?.name;
  return snapshotJson({
    jsonrpc: "2.0",
    id: body?.id ?? "static-demo",
    result: {
      content: [
        {
          type: "text",
          text: JSON.stringify(staticToolResult(toolName))
        }
      ],
      structuredContent: staticToolResult(toolName)
    }
  });
}

async function staticApiResponse(request, pathname) {
  if (pathname === "/health") {
    return snapshotJson({
      ...STATIC_DEMO_SNAPSHOT.health,
      mode: "static-snapshot",
      backend: "baked-cloudflare-worker",
      source: STATIC_DEMO_SNAPSHOT.source
    });
  }
  if (pathname.startsWith("/demo/ui-state/")) {
    return snapshotJson(STATIC_DEMO_SNAPSHOT.uiState);
  }
  if (pathname.startsWith("/iam/sessions/") && pathname.endsWith("/identity-proof")) {
    return snapshotJson(STATIC_DEMO_SNAPSHOT.identity);
  }
  if (pathname === "/iam/delegation-token") {
    return snapshotJson(STATIC_DEMO_SNAPSHOT.actionResponses.delegation_token);
  }
  if (pathname === "/auth/preflight") {
    return snapshotJson({
      ...STATIC_DEMO_SNAPSHOT.actionResponses.preflight,
      static_snapshot: true,
      note: "Preflight already ran before this snapshot was baked."
    });
  }
  if (pathname === "/mcp" || pathname.startsWith("/mcp/")) {
    return staticMcpResponse(request);
  }
  if (pathname.startsWith("/demo/access-requests/") && pathname.endsWith("/approve")) {
    return snapshotJson({
      status: "simulated",
      approved: true,
      static_snapshot: true,
      note: "Approval is acknowledged in static mode; the baked snapshot itself is immutable."
    });
  }
  if (pathname === "/demo/scenarios/hackathon/reseed") {
    return snapshotJson({
      ...STATIC_DEMO_SNAPSHOT.actionResponses.reseed,
      static_snapshot: true,
      note: "Static snapshot mode already contains the seeded demo state."
    });
  }
  if (pathname === "/index/recipes") {
    return snapshotJson({
      status: "ok",
      static_snapshot: true,
      indexed_recipes: STATIC_DEMO_SNAPSHOT.uiState.index_status?.indexed_recipes || 0,
      recipes: STATIC_DEMO_SNAPSHOT.uiState.index_status?.recipes || []
    });
  }
  if (pathname === "/demo/recipes/propose") {
    return snapshotJson({
      status: "simulated",
      static_snapshot: true,
      proposal: {
        recipe_id: "recipe_sales_renewal_v3",
        change: "No live learning worker ran; this is the baked demo snapshot."
      }
    });
  }
  if (pathname.startsWith("/demo/slack/search")) {
    return snapshotJson({
      channel: "slack_channel:sales-acme",
      messages: STATIC_DEMO_SNAPSHOT.uiState.demo_apps?.slack?.messages || []
    });
  }
  return snapshotJson({
    error: "This API path is not available in the static demo snapshot.",
    path: pathname
  }, 404);
}

export default {
  async fetch(request) {
    const source = new URL(request.url);
    if (!shouldProxy(source.pathname)) {
      return new Response("Not found", { status: 404 });
    }

    return staticApiResponse(request, source.pathname);
  }
};
