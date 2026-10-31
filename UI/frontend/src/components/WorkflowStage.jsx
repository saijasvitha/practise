import { Check, Circle, CircleDashed, CircleX, Minus } from "lucide-react";
const icons = {
  COMPLETED: Check,
  IN_PROGRESS: CircleDashed,
  FAILED: CircleX,
  PENDING: Circle,
  SKIPPED: Minus,
};
export default function WorkflowStage({ stage, index, active }) {
  const Icon = icons[stage.state] || Circle;
  return (
    <article
      className={
        "workflow-stage " +
        stage.state.toLowerCase() +
        (active ? " active" : "")
      }
    >
      <div className="stage-marker">
        <Icon size={18} />
      </div>
      <div className="stage-copy">
        <div className="stage-title-line">
          <span className="stage-number">0{index + 1}</span>
          <h3>{stage.name}</h3>
          <span className={"state-label " + stage.state.toLowerCase()}>
            {stage.state.replace("_", " ")}
          </span>
        </div>
        <p>{stage.summary}</p>
      </div>
    </article>
  );
}
