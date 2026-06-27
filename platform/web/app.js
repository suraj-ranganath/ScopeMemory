const SESSION = "sess_demo_001";
const BASE = "";

async function api(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function el(id) {
  return document.getElementById(id);
}

function renderSession(s) {
  el("session").innerHTML = `
    <div class="card">
      <div><strong>${s.session_id}</strong></div>
      <div class="muted">${s.goal}</div>
      <div>Agent: ${s.agent_id} · Class: ${s.goal_class}</div>
      <div>Status: <span class="status-${s.status}">${s.status || s.ui_status}</span></div>
    </div>`;
}

function renderRecipes(hits) {
  el("recipes").innerHTML = hits.map(h => `
    <div class="card">
      <div>${h.title || h.recipe_id}</div>
      <div>score: ${h.score ?? "—"}</div>
    </div>`).join("") || "<p>No recipe hits</p>";
}

function renderRequests(reqs) {
  el("requests").innerHTML = reqs.map(r => `
    <div class="card">
      <div><strong>${r.requested_tool_id}</strong> → ${r.requested_resource}</div>
      <div>Scope: ${r.requested_scope}</div>
      <div class="status-${r.status}">${r.status}</div>
      ${r.status === "pending" ? `<button data-req="${r.request_id}">Approve (Bob)</button>` : ""}
    </div>`).join("") || "<p>No pending requests</p>";

  el("requests").querySelectorAll("button[data-req]").forEach(btn => {
    btn.onclick = async () => {
      await api(`/demo/access-requests/${btn.dataset.req}/approve`, {
        method: "POST",
        body: JSON.stringify({ approver_id: "user_bob" }),
      });
      await refresh();
    };
  });
}

function renderProof(decisions) {
  el("proof").innerHTML = decisions.map(d => `
    <div class="card decision-${d.decision}">
      <div><strong>${d.tool_id}</strong> @ ${d.resource_id}</div>
      <div>${d.decision}</div>
      <pre>${JSON.stringify(d.proof || d.proof_json, null, 2)}</pre>
    </div>`).join("") || "<p>No decisions yet</p>";
}

function renderTimeline(events) {
  el("timeline").innerHTML = events.map(e => `
    <div class="timeline-item">
      <div><strong>${e.event_type}</strong></div>
      <pre>${JSON.stringify(e.payload || e.event_json, null, 2)}</pre>
    </div>`).join("") || "<p>No events</p>";
}

async function refresh() {
  const state = await api(`/demo/ui-state/${SESSION}`);
  renderSession(state.session);
  renderRecipes(state.recipe_hits || []);
  renderRequests(state.access_requests || []);
  renderProof(state.policy_decisions || []);
  renderTimeline(state.timeline || []);
  if (state.index_status) {
    el("index-status").textContent = JSON.stringify(state.index_status, null, 2);
  }
}

async function loadHealth() {
  const h = await api("/health");
  el("health").textContent = `${h.status} · ${h.stack} · graph: ${h.graph_backend} · recipes: ${h.recipe_retrieval || h.graph_backend}`;
}

el("btn-index").onclick = async () => {
  const r = await api("/index/recipes", { method: "POST" });
  el("index-status").textContent = JSON.stringify(r, null, 2);
  await refresh();
};

el("btn-slack").onclick = async () => {
  const r = await api("/demo/slack/search?channel=slack_channel:sales-acme");
  const inj = r.prompt_injection ? `\n\n⚠ INJECTION: ${r.prompt_injection}` : "";
  el("slack").innerHTML = `<pre>${JSON.stringify(r.messages, null, 2)}</pre>` +
    (r.prompt_injection ? `<p class="injection">${r.prompt_injection}</p>` : "");
};

el("btn-learn").onclick = async () => {
  const r = await api(`/demo/recipes/propose?session_id=${SESSION}`, { method: "POST" });
  el("proposal").textContent = JSON.stringify(r, null, 2);
  await refresh();
};

loadHealth().then(refresh).catch(err => {
  el("health").textContent = "offline";
  console.error(err);
});
