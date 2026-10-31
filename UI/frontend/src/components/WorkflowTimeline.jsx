import WorkflowStage from "./WorkflowStage.jsx";
export default function WorkflowTimeline({ workflow }) {
  return (
    <div className="workflow-timeline">
      {workflow.stages.map((stage, index) => (
        <WorkflowStage
          key={stage.name}
          {...{ stage, index }}
          active={workflow.currentStage === stage.name}
        />
      ))}
    </div>
  );
}
