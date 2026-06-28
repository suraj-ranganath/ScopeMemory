import { Effect } from "effect";
import {
  AlertTriangle,
  Check,
  CircleDot,
  ClipboardList,
  Fingerprint,
  GitBranch,
  KeyRound,
  LockKeyhole,
  MessageSquare,
  Play,
  Moon,
  RefreshCw,
  Route,
  Sparkles,
  Sun,
  X
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  AccessRequest,
  AppModel,
  AuthorizationLedgerEntry,
  ContextGraph,
  CredentialLease,
  DemoLinearComment,
  DemoLinearIssue,
  DemoSlackMessage,
  DepartmentTrace,
  PolicyDecision,
  RecipeHit,
  TimelineEvent,
  TraceEvent,
  approveRequest,
  attemptSlackPost,
  loadAppModel,
  proposeRecipe,
  resetDemo,
  resumeSlackRead,
  runLinearIssue,
  runPreflight,
  syncRecipes
} from "./api";
import "./styles.css";

type AsyncState = {
  loading: boolean;
  error: string | null;
};

type ActionState = {
  preflight: Record<string, unknown> | null;
  linear: Record<string, unknown> | null;
  slack: Record<string, unknown> | null;
  rejectedSlack: Record<string, unknown> | null;
  reset: Record<string, unknown> | null;
  proposal: Record<string, unknown> | null;
  sync: Record<string, unknown> | null;
};

type Theme = "dark" | "light";

const money = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

function runEffect<A>(
  effect: Effect.Effect<A, unknown>,
  onSuccess: (value: A) => void,
  onError: (message: string) => void
) {
  Effect.runPromise(effect).then(onSuccess).catch((error) => {
    onError(error instanceof Error ? error.message : JSON.stringify(error));
  });
}

function statusTone(value?: string) {
  const text = (value || "").toLowerCase();
  if (text.includes("allow") || text.includes("approved") || text.includes("ready")) return "good";
  if (text.includes("deny") || text.includes("blocked") || text.includes("reject")) return "danger";
  if (text.includes("pending") || text.includes("wait") || text.includes("escalate")) return "warn";
  return "quiet";
}

function decisionIcon(decision?: string) {
  const tone = statusTone(decision);
  if (tone === "good") return <Check size={16} />;
  if (tone === "danger") return <X size={16} />;
  if (tone === "warn") return <AlertTriangle size={16} />;
  return <CircleDot size={16} />;
}

function compactJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function initialTheme(): Theme {
  const saved = window.localStorage.getItem("scopememory-theme");
  return saved === "light" ? "light" : "dark";
}

function useAppModel() {
  const [model, setModel] = useState<AppModel | null>(null);
  const [state, setState] = useState<AsyncState>({ loading: true, error: null });

  const refresh = () => {
    setState({ loading: true, error: null });
    runEffect(
      loadAppModel,
      (next) => {
        setModel(next);
        setState({ loading: false, error: null });
      },
      (message) => setState({ loading: false, error: message })
    );
  };

  useEffect(() => refresh(), []);

  return { model, state, refresh };
}

export default function App() {
  const { model, state, refresh } = useAppModel();
  const [actions, setActions] = useState<ActionState>({
    preflight: null,
    linear: null,
    slack: null,
    rejectedSlack: null,
    reset: null,
    proposal: null,
    sync: null
  });
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [liveMode, setLiveMode] = useState(true);

  const session = model?.state.session;
  const decisions = model?.state.policy_decisions || [];
  const accessRequests = model?.state.access_requests || [];
  const anticipatedRequests = model?.state.anticipated_requests || accessRequests.filter((request) => request.created_before_tool_call);
  const credentialLeases = model?.state.credential_leases || [];
  const traceEvents = model?.state.trace_events || [];
  const departmentTraces = model?.state.department_traces || [];
  const contextGraph = model?.state.context_graph || { nodes: [], edges: [] };
  const demoApps = model?.state.demo_apps || {};
  const authorizationLedger = model?.state.authorization_ledger || [];
  const agentRun = model?.state.agent_run;
  const visibleTools = model?.state.predicted_tools || [];
  const pendingCount = accessRequests.filter((request) => request.status === "pending").length;
  const mode = model?.state.mode || "offline";
  const currentPath = window.location.pathname;

  useEffect(() => {
    window.localStorage.setItem("scopememory-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!liveMode) return;
    const timer = window.setInterval(refresh, 2000);
    return () => window.clearInterval(timer);
  }, [liveMode, refresh]);

  const execute = <A,>(label: string, effect: Effect.Effect<A, unknown>, onSuccess: (value: A) => void) => {
    setBusyAction(label);
    runEffect(
      effect,
      (value) => {
        onSuccess(value);
        setBusyAction(null);
      },
      (message) => {
        setActions((current) => ({ ...current, [label]: { error: message } }));
        setBusyAction(null);
      }
    );
  };

  const approve = (request: AccessRequest) => {
    execute("approve", approveRequest(request.request_id), () => refresh());
  };

  const executeAndRefresh = <A,>(label: keyof ActionState, effect: Effect.Effect<A, unknown>) => {
    execute(label, effect, (value) => {
      setActions((current) => ({ ...current, [label]: value as Record<string, unknown> }));
      refresh();
    });
  };

  const latestDecision = decisions[decisions.length - 1];
  const proofRules = useMemo(() => {
    const proof = latestDecision?.proof;
    if (proof && Array.isArray(proof.rules)) return proof.rules as string[];
    return ["session", "recipe", "scope", "decision"];
  }, [latestDecision]);

  if (currentPath.startsWith("/linear")) {
    return (
      <main className={`app-shell app-page-shell theme-${theme}`}>
        <AppPageHeader
          title="Demo Linear"
          subtitle="Policy-gated MCP issue activity"
          theme={theme}
          setTheme={setTheme}
        />
        <LinearDemoPage
          issues={demoApps.linear?.issues || []}
          comments={demoApps.linear?.comments || []}
          decisions={decisions}
        />
      </main>
    );
  }

  if (currentPath.startsWith("/slack")) {
    return (
      <main className={`app-shell app-page-shell theme-${theme}`}>
        <AppPageHeader
          title="Demo Slack"
          subtitle="Policy-gated MCP channel history"
          theme={theme}
          setTheme={setTheme}
        />
        <SlackDemoPage
          messages={demoApps.slack?.messages || []}
          decisions={decisions}
        />
      </main>
    );
  }

  return (
    <main className={`app-shell theme-${theme}`}>
      <aside className="rail" aria-label="ScopeMemory sections">
        <div className="brand-mark">
          <span>SM</span>
        </div>
        <nav>
          <a href="#session" aria-label="Session"><Route size={18} /></a>
          <a href="#requests" aria-label="Requests"><LockKeyhole size={18} /></a>
          <a href="#proof" aria-label="Proof"><GitBranch size={18} /></a>
          <a href="#memory" aria-label="Memory"><Sparkles size={18} /></a>
        </nav>
        <button
          className="theme-toggle"
          onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </aside>

      <section className="hero-pane" id="session">
        <div className="hero-copy">
          <p className="eyebrow">ScopeMemory control room</p>
          <h1>{session?.goal || "Memory-informed authorization for MCP agents"}</h1>
          <p className="session-summary">
            ScopeMemory sits between an AI agent and the tools it wants to use. It compares
            the session goal against accepted workflow memory, decides each tool call, and
            keeps credentials out of the agent context.
          </p>
          <div className="session-strip">
            <Pill tone={statusTone(session?.status || model?.state.ui_status)}>{session?.status || model?.state.ui_status || "offline"}</Pill>
            <Pill>{session?.session_id || "sess_demo_001"}</Pill>
            <Pill>{session?.agent_id || "agent_renewal_01"}</Pill>
            <Pill tone={mode === "live" ? "good" : "warn"}>{mode}</Pill>
          </div>
          <div className="app-link-row">
            <a className="app-link" href="/linear"><ClipboardList size={15} /> Demo Linear</a>
            <a className="app-link" href="/slack"><MessageSquare size={15} /> Demo Slack</a>
          </div>
        </div>

        <ProofSpine
          rules={proofRules}
          decision={latestDecision?.decision || (pendingCount ? "ESCALATE_HUMAN" : "ALLOW")}
        />
      </section>

      <section className="topology">
        <Metric label="Mode" value={mode} tone={mode === "live" ? "good" : "warn"} />
        <Metric label="Graph" value={model?.health?.graph_backend || "fixture"} />
        <Metric label="Policy" value={model?.health?.policy_engine || "cozo"} tone={(model?.health?.policy_engine || "").includes("cozo") ? "good" : "danger"} />
        <Metric label="Visible tools" value={visibleTools.length.toString()} />
        <Metric label="Open requests" value={pendingCount.toString()} tone={pendingCount ? "warn" : "good"} />
      </section>

      <section className="presenter-controls" aria-label="Hackathon presenter controls">
        <button className="secondary-button" disabled={busyAction === "reset"} onClick={() => executeAndRefresh("reset", resetDemo())}>
          <RefreshCw size={15} /> Reset demo
        </button>
        <button className="primary-button" disabled={busyAction === "preflight"} onClick={() => executeAndRefresh("preflight", runPreflight(session?.session_id, session?.agent_id))}>
          <Route size={15} /> Run preflight
        </button>
        <button className="secondary-button" disabled={!anticipatedRequests.some((request) => request.status === "pending") || busyAction === "approve"} onClick={() => {
          const pending = anticipatedRequests.find((request) => request.status === "pending");
          if (pending) approve(pending);
        }}>
          <Check size={15} /> Approve as Bob
        </button>
        <button className="secondary-button" disabled={busyAction === "linear"} onClick={() => executeAndRefresh("linear", runLinearIssue(session?.session_id, session?.agent_id))}>
          <KeyRound size={15} /> Run Linear with 1P lease
        </button>
        <button className="secondary-button" disabled={busyAction === "slack"} onClick={() => executeAndRefresh("slack", resumeSlackRead(session?.session_id, session?.agent_id))}>
          <Play size={15} /> Resume Slack read
        </button>
        <button className="secondary-button danger-action" disabled={busyAction === "rejectedSlack"} onClick={() => executeAndRefresh("rejectedSlack", attemptSlackPost(session?.session_id, session?.agent_id))}>
          <X size={15} /> Attempt rejected Slack post
        </button>
        <button className={`live-toggle ${liveMode ? "good" : ""}`} onClick={() => setLiveMode((current) => !current)}>
          <CircleDot size={13} /> {liveMode ? "Live polling" : "Polling paused"}
        </button>
      </section>

      {state.error ? <div className="notice danger">{state.error}</div> : null}
      {state.loading ? <div className="notice">Loading governed session...</div> : null}

      <section className="work-grid">
        <Panel
          title="Agent identity"
          eyebrow="Delegation"
          icon={<Fingerprint size={18} />}
          action={<button className="icon-button" onClick={refresh} aria-label="Refresh"><RefreshCw size={16} /></button>}
        >
          <div className="identity-lockup">
            <div>
              <strong>{model?.identity?.agent_id || session?.agent_id || "agent_renewal_01"}</strong>
              <span>{model?.identity?.identity_ref || "agentic-iam://agents/renewal-bot"}</span>
            </div>
            <TrustDial value={model?.identity?.trust_score ?? 0.91} />
          </div>
          <TupleList tuples={model?.identity?.rebac_tuples || []} />
        </Panel>

        <Panel title="Recipe memory" eyebrow="Predicted path" icon={<Sparkles size={18} />}>
          <RecipeList hits={model?.state.recipe_hits || []} />
          <DepartmentTraceList traces={departmentTraces} />
          <div className="command-row">
            <button
              className="secondary-button"
              disabled={busyAction === "sync"}
              onClick={() => execute("sync", syncRecipes(), (sync) => setActions((current) => ({ ...current, sync })))}
            >
              <RefreshCw size={15} /> Refresh index
            </button>
          </div>
          {actions.sync ? <CodePlate value={actions.sync} /> : null}
        </Panel>

        <Panel title="Anticipated access" eyebrow="Asked before tool call" icon={<LockKeyhole size={18} />} id="requests">
          <AnticipatedRequestList requests={anticipatedRequests} onApprove={approve} busy={busyAction === "approve"} />
        </Panel>

        <Panel title="Credential lease" eyebrow="1Password broker" icon={<KeyRound size={18} />}>
          <CredentialLeasePanel leases={credentialLeases} grants={model?.state.grants || []} />
        </Panel>
      </section>

      <section className="decision-band access-ledger-band">
        <div>
          <p className="eyebrow">Access ledger</p>
          <h2>Requests, approvals, rejections, and policy reasons in one place.</h2>
        </div>
        <AuthorizationLedger rows={authorizationLedger} />
      </section>

      <section className="live-trace-band">
        <div>
          <p className="eyebrow">Running trace</p>
          <h2>Prediction, approval, policy, credential injection, and execution in one timeline.</h2>
        </div>
        <TraceLanes events={traceEvents} />
      </section>

      <section className="decision-band" id="proof">
        <div>
          <p className="eyebrow">Policy proof</p>
          <h2>Every tool call leaves a redacted decision trail.</h2>
        </div>
        <DecisionList decisions={decisions} />
      </section>

      <section className="two-column" id="memory">
        <Panel title="Context graph" eyebrow="Governed memory" icon={<GitBranch size={18} />}>
          <ContextGraphPanel graph={contextGraph} />
        </Panel>
        <Panel title="Agent run" eyebrow="Long-horizon session" icon={<Play size={18} />}>
          <AgentRunPanel run={agentRun} lastActions={actions} />
        </Panel>
      </section>

      <section className="two-column">
        <Panel title="Demo Linear" eyebrow="Local MCP app" icon={<ClipboardList size={18} />}>
          <LinearMini issues={demoApps.linear?.issues || []} />
        </Panel>
        <Panel title="Demo Slack" eyebrow="Local MCP app" icon={<MessageSquare size={18} />}>
          <SlackMini messages={demoApps.slack?.messages || []} />
        </Panel>
      </section>

      <section className="decision-band compact-audit">
        <div>
          <p className="eyebrow">Audit</p>
          <h2>Hash-chained events remain available below the live trace.</h2>
        </div>
        <Timeline events={model?.state.timeline || []} />
      </section>

      <section className="learning-panel">
        <div>
          <p className="eyebrow">Learning worker</p>
          <h2>Recipe diffs stay reviewable before they become memory.</h2>
        </div>
        <button
          className="primary-button"
          disabled={busyAction === "proposal"}
          onClick={() => execute("proposal", proposeRecipe(session?.session_id), (proposal) => setActions((current) => ({ ...current, proposal: proposal as Record<string, unknown> })))}
        >
          Propose recipe diff <Sparkles size={15} />
        </button>
        {actions.proposal ? <CodePlate value={actions.proposal} /> : null}
      </section>
    </main>
  );
}

function Panel(props: {
  title: string;
  eyebrow: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
  id?: string;
}) {
  return (
    <section className="panel" id={props.id}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{props.eyebrow}</p>
          <h2>{props.icon}{props.title}</h2>
        </div>
        {props.action}
      </div>
      {props.children}
    </section>
  );
}

function Pill({ children, tone = "quiet" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

function Metric({ label, value, tone = "quiet" }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AppPageHeader({ title, subtitle, theme, setTheme }: {
  title: string;
  subtitle: string;
  theme: Theme;
  setTheme: React.Dispatch<React.SetStateAction<Theme>>;
}) {
  return (
    <header className="app-page-header">
      <a className="app-link" href="/"><Route size={15} /> ScopeMemory</a>
      <div>
        <p className="eyebrow">Local demo app</p>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <button
        className="theme-toggle page-theme-toggle"
        onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}
        aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      >
        {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
      </button>
    </header>
  );
}

function ProofSpine({ rules, decision }: { rules: string[]; decision: string }) {
  const decisionName = decision.toLowerCase();
  const decisionLabel = decisionName.includes("escalate")
    ? "escalate"
    : decisionName.includes("deny")
      ? "deny"
      : decisionName.includes("allow")
        ? "allow"
        : "decide";
  const nodes = ["goal", "recipe", "grant", "lease", decisionLabel];
  return (
    <div className="proof-spine" aria-label="Proof path">
      <svg viewBox="0 0 660 260" role="img" aria-labelledby="proof-title">
        <title id="proof-title">Authorization proof path</title>
        <path className="spine-track" d="M52 134 C150 26 224 232 330 128 S522 36 606 134" />
        <path className="spine-glow" d="M52 134 C150 26 224 232 330 128 S522 36 606 134" />
        {nodes.map((node, index) => {
          const points = [
            [52, 134],
            [188, 108],
            [330, 128],
            [472, 104],
            [606, 134]
          ];
          const [x, y] = points[index];
          return (
            <g key={node} className="spine-node">
              <circle cx={x} cy={y} r="18" />
              <text x={x} y={y + 43} textAnchor="middle">{node}</text>
            </g>
          );
        })}
      </svg>
      <div className="spine-rules">
        {rules.slice(0, 5).map((rule) => <span key={rule}>{rule}</span>)}
      </div>
    </div>
  );
}

function AuthorizationLedger({ rows }: { rows: AuthorizationLedgerEntry[] }) {
  if (!rows.length) return <EmptyLine text="Run preflight and tool calls to populate the ledger." />;
  return (
    <div className="authorization-ledger">
      {rows.map((row, index) => (
        <article className={`ledger-row ${statusTone(row.status || row.decision)}`} key={`${row.kind}-${row.request_id || row.decision_id || index}`}>
          <div className="ledger-main">
            <Pill tone={statusTone(row.status || row.decision)}>{row.status || row.decision}</Pill>
            <strong>{row.tool_id || "authorization"}</strong>
            <span>{row.scope || "scope"} {"->"} {row.resource_id || "resource"}</span>
            <p>{row.reason || "No policy reason recorded."}</p>
          </div>
          <div className="ledger-proof">
            {row.policy_engine ? <Pill tone={row.policy_engine.includes("cozo") ? "good" : "danger"}>{row.policy_engine}</Pill> : null}
            {(row.rules || []).slice(0, 4).map((rule) => <span key={`${row.decision_id}-${rule}`}>{rule}</span>)}
            {row.proof_hash ? <small>{row.proof_hash}</small> : null}
          </div>
        </article>
      ))}
    </div>
  );
}

function TrustDial({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="trust-dial" style={{ "--trust": `${pct}%` } as React.CSSProperties}>
      <span>{money.format(value)}</span>
      <small>trust</small>
    </div>
  );
}

function LinearMini({ issues }: { issues: DemoLinearIssue[] }) {
  if (!issues.length) return <EmptyLine text="No demo Linear issues yet." />;
  return (
    <div className="app-mini-list">
      {issues.slice(0, 4).map((issue) => (
        <a className="app-mini-row" href={`/linear/issues/${issue.issue_id}`} key={issue.issue_id}>
          <strong>{issue.issue_id}</strong>
          <span>{issue.title}</span>
          <Pill tone={issue.state === "open" ? "good" : "quiet"}>{issue.state || "open"}</Pill>
        </a>
      ))}
    </div>
  );
}

function SlackMini({ messages }: { messages: DemoSlackMessage[] }) {
  if (!messages.length) return <EmptyLine text="No demo Slack messages yet." />;
  return (
    <div className="app-mini-list">
      {messages.slice(-4).map((message) => (
        <a className="app-mini-row" href={`/slack/channels/${message.channel_id}`} key={message.message_id}>
          <strong>{message.user_name}</strong>
          <span>{message.text}</span>
          <Pill tone={message.is_untrusted ? "warn" : "quiet"}>{message.message_kind || "message"}</Pill>
        </a>
      ))}
    </div>
  );
}

function TupleList({ tuples }: { tuples: string[] }) {
  if (!tuples.length) return <EmptyLine text="No delegation tuples." />;
  return (
    <ul className="tuple-list">
      {tuples.slice(0, 4).map((tuple) => <li key={tuple}>{tuple}</li>)}
    </ul>
  );
}

function RecipeList({ hits }: { hits: RecipeHit[] }) {
  if (!hits.length) return <EmptyLine text="No recipe hits." />;
  return (
    <div className="recipe-list">
      {hits.map((hit) => (
        <article className="recipe-row" key={hit.recipe_id}>
          <div>
            <strong>{hit.title || hit.recipe_id}</strong>
            <span>{hit.recipe_id}</span>
          </div>
          <Pill tone="good">{hit.score ? `${Math.round(hit.score * 100)}%` : "match"}</Pill>
        </article>
      ))}
    </div>
  );
}

function DepartmentTraceList({ traces }: { traces: DepartmentTrace[] }) {
  if (!traces.length) return null;
  return (
    <div className="department-traces">
      <p className="micro-label">Reusable traces</p>
      {traces.slice(0, 5).map((trace) => (
        <div className="department-row" key={trace.recipe_id}>
          <span>{trace.team_name}</span>
          <strong>{trace.title}</strong>
          <Pill tone={trace.has_human_gate ? "warn" : "quiet"}>
            {trace.tool_count || 0} tools
          </Pill>
        </div>
      ))}
    </div>
  );
}

function LinearDemoPage({ issues, comments, decisions }: {
  issues: DemoLinearIssue[];
  comments: DemoLinearComment[];
  decisions: PolicyDecision[];
}) {
  const issueId = window.location.pathname.split("/").filter(Boolean)[2];
  const selected = issues.find((issue) => issue.issue_id === issueId) || issues[0];
  const selectedComments = comments.filter((comment) => comment.issue_id === selected?.issue_id);
  return (
    <section className="demo-app-layout linear-app">
      <aside className="demo-app-sidebar">
        <p className="eyebrow">Issues</p>
        {issues.map((issue) => (
          <a className={`demo-app-list-row ${selected?.issue_id === issue.issue_id ? "active" : ""}`} href={`/linear/issues/${issue.issue_id}`} key={issue.issue_id}>
            <strong>{issue.issue_id}</strong>
            <span>{issue.title}</span>
          </a>
        ))}
      </aside>
      <article className="demo-app-detail">
        {selected ? (
          <>
            <div className="demo-app-title">
              <div>
                <p className="eyebrow">{selected.issue_id}</p>
                <h2>{selected.title}</h2>
              </div>
              <Pill tone="good">{selected.state || "open"}</Pill>
            </div>
            <p>{selected.description}</p>
            <div className="demo-app-evidence">
              <Pill>{selected.team_id}</Pill>
              <Pill>session: {selected.source_session_id || "seed"}</Pill>
              {selected.policy_decision_id ? <Pill tone="good">policy: {selected.policy_decision_id}</Pill> : null}
              {selected.credential_lease_id ? <Pill tone="good">lease: {selected.credential_lease_id}</Pill> : null}
            </div>
            <h3>Comments</h3>
            {selectedComments.length ? selectedComments.map((comment) => (
              <div className="demo-comment" key={comment.comment_id}>
                <strong>{comment.created_by_agent_id || "agent"}</strong>
                <p>{comment.body}</p>
              </div>
            )) : <EmptyLine text="No comments on this issue." />}
          </>
        ) : <EmptyLine text="No Linear issue selected." />}
      </article>
      <aside className="demo-app-policy">
        <p className="eyebrow">Policy evidence</p>
        <DecisionList decisions={decisions.filter((decision) => (decision.tool_id || "").startsWith("linear."))} />
      </aside>
    </section>
  );
}

function SlackDemoPage({ messages, decisions }: {
  messages: DemoSlackMessage[];
  decisions: PolicyDecision[];
}) {
  const channelId = decodeURIComponent(window.location.pathname.split("/").filter(Boolean)[2] || "slack_channel:sales-acme");
  const channelMessages = messages.filter((message) => message.channel_id === channelId);
  return (
    <section className="demo-app-layout slack-app">
      <aside className="demo-app-sidebar">
        <p className="eyebrow">Channels</p>
        {Array.from(new Set(messages.map((message) => message.channel_id))).map((channel) => (
          <a className={`demo-app-list-row ${channel === channelId ? "active" : ""}`} href={`/slack/channels/${channel}`} key={channel}>
            <strong>{channel.replace("slack_channel:", "#")}</strong>
            <span>{messages.filter((message) => message.channel_id === channel).length} messages</span>
          </a>
        ))}
      </aside>
      <article className="demo-app-detail">
        <div className="demo-app-title">
          <div>
            <p className="eyebrow">Channel</p>
            <h2>{channelId.replace("slack_channel:", "#")}</h2>
          </div>
          <Pill tone="warn">human-gated read</Pill>
        </div>
        <div className="slack-message-list">
          {channelMessages.map((message) => (
            <div className={`slack-message ${message.is_untrusted ? "untrusted" : ""}`} key={message.message_id}>
              <strong>{message.user_name}</strong>
              <p>{message.text}</p>
              <div>
                <Pill tone={message.is_untrusted ? "warn" : "quiet"}>{message.message_kind || "message"}</Pill>
                {message.policy_decision_id ? <Pill tone="good">policy: {message.policy_decision_id}</Pill> : null}
              </div>
            </div>
          ))}
        </div>
      </article>
      <aside className="demo-app-policy">
        <p className="eyebrow">Policy evidence</p>
        <DecisionList decisions={decisions.filter((decision) => (decision.tool_id || "").startsWith("slack."))} />
      </aside>
    </section>
  );
}

function RequestList({ requests, onApprove, busy }: {
  requests: AccessRequest[];
  onApprove: (request: AccessRequest) => void;
  busy: boolean;
}) {
  if (!requests.length) return <EmptyLine text="No open access requests." />;
  return (
    <div className="request-list">
      {requests.map((request) => (
        <article className="request-row" key={request.request_id}>
          <div>
            <strong>{request.requested_tool_id}</strong>
            <span>{request.requested_scope}</span>
            <small>{request.reason}</small>
          </div>
          {request.status === "pending" ? (
            <button className="primary-button" disabled={busy} onClick={() => onApprove(request)}>
              Approve <Check size={15} />
            </button>
          ) : (
            <Pill tone={statusTone(request.status)}>{request.status}</Pill>
          )}
        </article>
      ))}
    </div>
  );
}

function AnticipatedRequestList({ requests, onApprove, busy }: {
  requests: AccessRequest[];
  onApprove: (request: AccessRequest) => void;
  busy: boolean;
}) {
  if (!requests.length) return <EmptyLine text="Run preflight to send predicted approval requests before tool calls." />;
  return (
    <div className="request-list">
      {requests.map((request) => (
        <article className="request-row anticipated" key={request.request_id}>
          <div>
            <strong>{request.requested_tool_id}</strong>
            <span>{request.requested_scope} {"->"} {request.requested_resource}</span>
            <small>{request.reason}</small>
            <div className="evidence-line">
              <Pill tone="good">origin: {request.request_origin || "prediction"}</Pill>
              <Pill tone="warn">{request.created_before_tool_call ? "before tool call" : "at tool call"}</Pill>
              {request.prediction_confidence ? <Pill>{Math.round(request.prediction_confidence * 100)}% confidence</Pill> : null}
            </div>
          </div>
          {request.status === "pending" ? (
            <button className="primary-button" disabled={busy} onClick={() => onApprove(request)}>
              Approve <Check size={15} />
            </button>
          ) : (
            <Pill tone={statusTone(request.status)}>{request.status}</Pill>
          )}
        </article>
      ))}
    </div>
  );
}

function LeasePath({ grants }: { grants: Array<Record<string, unknown>> }) {
  return (
    <div className="lease-path">
      {["policy", "lease", "resolve", "execute"].map((step, index) => (
        <div className="lease-step" key={step}>
          <span>{index + 1}</span>
          <strong>{step}</strong>
        </div>
      ))}
      <p>{grants.length ? `${grants.length} grant record${grants.length === 1 ? "" : "s"} ready` : "No credential material is exposed to the agent."}</p>
    </div>
  );
}

function CredentialLeasePanel({ leases, grants }: { leases: CredentialLease[]; grants: Array<Record<string, unknown>> }) {
  if (!leases.length) {
    return (
      <div className="lease-path">
        {["policy", "lease", "resolve", "execute"].map((step, index) => (
          <div className="lease-step" key={step}>
            <span>{index + 1}</span>
            <strong>{step}</strong>
          </div>
        ))}
        <p>{grants.length ? `${grants.length} grant record${grants.length === 1 ? "" : "s"} ready. Run Linear to mint a 1Password lease.` : "No credential material is exposed to the agent."}</p>
      </div>
    );
  }
  return (
    <div className="lease-inspector">
      {leases.map((lease) => (
        <article className="lease-record" key={lease.lease_id}>
          <div className="lease-record-head">
            <strong>{lease.lease_id}</strong>
            <Pill tone={lease.status === "used" ? "good" : "warn"}>{lease.status || "minted"}</Pill>
          </div>
          <dl>
            <dt>provider</dt><dd>{lease.provider || "1password"}</dd>
            <dt>mode</dt><dd>{lease.provider_mode || "broker"}</dd>
            <dt>injection</dt><dd>{lease.injection_mode || "gateway_header"}</dd>
            <dt>secret exposed</dt><dd>{String(Boolean(lease.secret_exposed_to_agent))}</dd>
            <dt>credential hash</dt><dd>{lease.credential_ref_hash || "sha256:..."}</dd>
          </dl>
        </article>
      ))}
    </div>
  );
}

function DecisionList({ decisions }: { decisions: PolicyDecision[] }) {
  if (!decisions.length) return <EmptyLine text="No policy decisions yet." />;
  return (
    <div className="decision-list">
      {decisions.map((decision, index) => (
        <article className={`decision-row ${statusTone(decision.decision)}`} key={decision.decision_id || `${decision.tool_id}-${index}`}>
          <div className="decision-mark">{decisionIcon(decision.decision)}</div>
          <div>
            <strong>{decision.tool_id || "tool.call"}</strong>
            <span>{decision.resource_id || "resource"}</span>
            <p>{decision.reason || String(decision.proof?.reason || "No reason recorded.")}</p>
          </div>
          <CodePlate value={decision.proof || decision.proof_json || {}} />
        </article>
      ))}
    </div>
  );
}

function TraceLanes({ events }: { events: TraceEvent[] }) {
  const lanes = ["Context", "Approval", "Policy", "Credential", "Execution", "Learning"];
  if (!events.length) return <EmptyLine text="Run preflight to start the live trace." />;
  return (
    <div className="trace-lanes">
      {lanes.map((lane) => {
        const laneEvents = events.filter((event) => event.lane === lane).slice(-4);
        return (
          <div className="trace-lane" key={lane}>
            <h3>{lane}</h3>
            {laneEvents.length ? laneEvents.map((event, index) => (
              <article className="trace-event" key={`${event.event_type}-${index}`}>
                <strong>{event.event_type}</strong>
                <span>{event.created_at || "demo time"}</span>
                <small>{event.event_hash ? event.event_hash.slice(0, 18) : ""}</small>
              </article>
            )) : <p>No events yet.</p>}
          </div>
        );
      })}
    </div>
  );
}

function ContextGraphPanel({ graph }: { graph: ContextGraph }) {
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  if (!nodes.length) return <EmptyLine text="Run preflight to project the context graph." />;
  return (
    <div className="context-graph-panel">
      <div className="graph-stats">
        <Metric label="Nodes" value={nodes.length.toString()} />
        <Metric label="Edges" value={edges.length.toString()} />
      </div>
      <div className="graph-node-list">
        {nodes.slice(0, 10).map((node) => (
          <div className="graph-node-row" key={String(node.node_id)}>
            <span>{String(node.node_kind || "Node")}</span>
            <strong>{String(node.label || node.source_id || node.node_id)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentRunPanel({ run, lastActions }: { run?: { status: string; current_step: string; pending_approvals: number; approved_requests: number; policy_decisions: number; credential_leases: number; last_event_hash?: string }; lastActions: ActionState }) {
  if (!run) return <EmptyLine text="No agent run loaded." />;
  return (
    <div className="agent-run-panel">
      <div className="agent-status">
        <Pill tone={statusTone(run.status)}>{run.status}</Pill>
        <strong>{run.current_step}</strong>
      </div>
      <div className="agent-run-metrics">
        <Metric label="Pending" value={run.pending_approvals.toString()} tone={run.pending_approvals ? "warn" : "good"} />
        <Metric label="Approved" value={run.approved_requests.toString()} />
        <Metric label="Policy" value={run.policy_decisions.toString()} />
        <Metric label="Leases" value={run.credential_leases.toString()} />
      </div>
      {run.last_event_hash ? <p className="hash-line">Last event {run.last_event_hash}</p> : null}
      {lastActions.linear ? <CodePlate value={lastActions.linear} /> : null}
      {lastActions.slack ? <CodePlate value={lastActions.slack} /> : null}
      {lastActions.rejectedSlack ? <CodePlate value={lastActions.rejectedSlack} /> : null}
    </div>
  );
}

function Timeline({ events }: { events: TimelineEvent[] }) {
  if (!events.length) return <EmptyLine text="No audit events yet." />;
  return (
    <ol className="timeline">
      {events.map((event, index) => (
        <li key={`${event.event_type}-${index}`}>
          <strong>{event.event_type || "event"}</strong>
          <span>{event.created_at || "demo time"}</span>
          <CodePlate value={event.payload || event.event_json || {}} />
        </li>
      ))}
    </ol>
  );
}

function CodePlate({ value }: { value: unknown }) {
  return <pre className="code-plate">{compactJson(value)}</pre>;
}

function EmptyLine({ text }: { text: string }) {
  return <p className="empty-line">{text}</p>;
}
