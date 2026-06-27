import { Effect } from "effect";
import {
  AlertTriangle,
  ArrowUpRight,
  Check,
  CircleDot,
  Fingerprint,
  GitBranch,
  KeyRound,
  LockKeyhole,
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
  PolicyDecision,
  RecipeHit,
  TimelineEvent,
  approveRequest,
  loadAppModel,
  proposeRecipe,
  searchSlack,
  syncRecipes
} from "./api";
import "./styles.css";

type AsyncState = {
  loading: boolean;
  error: string | null;
};

type ActionState = {
  slack: Record<string, unknown> | null;
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
  if (text.includes("deny") || text.includes("blocked")) return "danger";
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
  const [actions, setActions] = useState<ActionState>({ slack: null, proposal: null, sync: null });
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>(initialTheme);

  const session = model?.state.session;
  const decisions = model?.state.policy_decisions || [];
  const accessRequests = model?.state.access_requests || [];
  const visibleTools = model?.state.predicted_tools || [];
  const pendingCount = accessRequests.filter((request) => request.status === "pending").length;
  const mode = model?.state.mode || "offline";

  useEffect(() => {
    window.localStorage.setItem("scopememory-theme", theme);
  }, [theme]);

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

  const latestDecision = decisions[decisions.length - 1];
  const proofRules = useMemo(() => {
    const proof = latestDecision?.proof;
    if (proof && Array.isArray(proof.rules)) return proof.rules as string[];
    return ["session", "recipe", "scope", "decision"];
  }, [latestDecision]);

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
        </div>

        <ProofSpine
          rules={proofRules}
          decision={latestDecision?.decision || (pendingCount ? "ESCALATE_HUMAN" : "ALLOW")}
        />
      </section>

      <section className="topology">
        <Metric label="Mode" value={mode} tone={mode === "live" ? "good" : "warn"} />
        <Metric label="Graph" value={model?.health?.graph_backend || "fixture"} />
        <Metric label="Visible tools" value={visibleTools.length.toString()} />
        <Metric label="Open requests" value={pendingCount.toString()} tone={pendingCount ? "warn" : "good"} />
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

        <Panel title="Access requests" eyebrow="Human gate" icon={<LockKeyhole size={18} />} id="requests">
          <RequestList requests={accessRequests} onApprove={approve} busy={busyAction === "approve"} />
        </Panel>

        <Panel title="Credential lease" eyebrow="1Password broker" icon={<KeyRound size={18} />}>
          <LeasePath grants={model?.state.grants || []} />
        </Panel>
      </section>

      <section className="decision-band" id="proof">
        <div>
          <p className="eyebrow">Policy proof</p>
          <h2>Every tool call leaves a redacted decision trail.</h2>
        </div>
        <DecisionList decisions={decisions} />
      </section>

      <section className="two-column" id="memory">
        <Panel title="Timeline" eyebrow="Audit" icon={<GitBranch size={18} />}>
          <Timeline events={model?.state.timeline || []} />
        </Panel>
        <Panel title="Adversarial context" eyebrow="Mock Slack" icon={<AlertTriangle size={18} />}>
          <button
            className="primary-button"
            disabled={busyAction === "slack"}
            onClick={() => execute("slack", searchSlack(), (slack) => setActions((current) => ({ ...current, slack: slack as Record<string, unknown> })))}
          >
            Inspect channel <ArrowUpRight size={15} />
          </button>
          {actions.slack ? <CodePlate value={actions.slack} /> : <EmptyLine text="No channel sample loaded." />}
        </Panel>
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

function TrustDial({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="trust-dial" style={{ "--trust": `${pct}%` } as React.CSSProperties}>
      <span>{money.format(value)}</span>
      <small>trust</small>
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

function DecisionList({ decisions }: { decisions: PolicyDecision[] }) {
  if (!decisions.length) return <EmptyLine text="No policy decisions yet." />;
  return (
    <div className="decision-list">
      {decisions.map((decision, index) => (
        <article className={`decision-row ${statusTone(decision.decision)}`} key={`${decision.tool_id}-${index}`}>
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
