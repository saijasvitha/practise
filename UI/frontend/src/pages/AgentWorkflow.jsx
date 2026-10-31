import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock3,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import Header from "../components/Header.jsx";
import WorkflowTimeline from "../components/WorkflowTimeline.jsx";
import useAgentWorkflow from "../hooks/useAgentWorkflow.js";
import { workflows } from "../mock/workflows.js";
export default function AgentWorkflow() {
  const { executionId } = useParams(),
    stored = sessionStorage.getItem(executionId),
    { workflow: mock } = useAgentWorkflow(executionId),
    workflow = stored ? JSON.parse(stored) : mock;
  if (!workflow)
    return (
      <div className="app-shell">
        <Header backLink />
        <main className="workflow-main">
          <div className="not-found">
            <AlertTriangle />
            <h1>Execution not found</h1>
            <p>This ID is not in local demo data.</p>
            <Link className="button button-primary" to="/issues">
              Back to dashboard
            </Link>
            <div className="demo-links">
              Examples:{" "}
              {Object.keys(workflows).map((id) => (
                <Link key={id} to={"/agent/" + id}>
                  {id}
                </Link>
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  const failed = workflow.status === "FAILED",
    complete = workflow.status === "COMPLETED";
  return (
    <div className="app-shell">
      <Header
        agentStatus={workflow.status === "IN_PROGRESS" ? "Working" : "Idle"}
        backLink
      />
      <main className="workflow-main">
        <Link className="back-mobile" to="/issues">
          <ArrowLeft size={15} /> Back to dashboard
        </Link>
        <div className="workflow-heading">
          <div>
            <div className="eyebrow">Agent execution · {executionId}</div>
            <h1>
              {workflow.issueId} <span>·</span> {workflow.title}
            </h1>
            <p>
              Incident Response Agent <span>·</span> AI-Assisted
            </p>
          </div>
          <span
            className={
              "execution-status " +
              (failed ? "failed" : complete ? "completed" : "running")
            }
          >
            {failed ? (
              <AlertTriangle size={15} />
            ) : complete ? (
              <CheckCircle2 size={15} />
            ) : (
              <Clock3 size={15} />
            )}{" "}
            {workflow.status.replace("_", " ")}
          </span>
        </div>
        <div className="workflow-layout">
          <section className="workflow-panel">
            <div className="panel-heading">
              <div>
                <h2>Execution timeline</h2>
                <p>Seven stages from assignment through verification.</p>
              </div>
              <span className="stage-count">
                {workflow.stages.filter((s) => s.state === "COMPLETED").length}{" "}
                / 7 complete
              </span>
            </div>
            <WorkflowTimeline workflow={workflow} />
          </section>
          <aside className="workflow-aside">
            <div
              className={
                "activity-card " +
                (failed ? "failure" : complete ? "success" : "")
              }
            >
              <div className="aside-icon">
                <Bot size={19} />
              </div>
              <div className="eyebrow">Current activity</div>
              <h2>{workflow.currentStage}</h2>
              <p>{workflow.activity}</p>
              <div className="activity-rule" />
              <small>Execution status</small>
              <strong>{workflow.status.replace("_", " ")}</strong>
            </div>
            <div className="result-card">
              <div className="result-heading">
                <CheckCircle2 size={17} />
                <h3>Execution summary</h3>
              </div>
              <p>{workflow.result}</p>
              <div className="mock-banner">
                Mock workflow · no services were changed
              </div>
            </div>
            <div className="workflow-meta">
              <span>
                Issue <strong>{workflow.issueId}</strong>
              </span>
              <span>
                Agent <strong>Incident Response Agent</strong>
              </span>
              <span>
                Mode <strong>AI-Assisted</strong>
              </span>
            </div>
          </aside>
        </div>
        <div className="workflow-bottom">
          <span>Workflow state comes from local mock data.</span>
          <Link to="/issues">Return to issues →</Link>
        </div>
      </main>
    </div>
  );
}
