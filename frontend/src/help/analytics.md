# Analytics

The Analytics tab provides operational metrics to help you understand pipeline health, throughput, and agent performance over time. Use it to identify bottlenecks, track quality trends, and make data-driven decisions about pipeline configuration.

## Key metrics

### Throughput
Tasks completed per day or week. A healthy pipeline processes issues within 2–4 hours from triage to published PR. Sudden drops in throughput usually indicate a stage is backing up or an agent is being quarantined.

### Cycle time
Total time from issue import to PR publication, broken down by stage. The per-stage breakdown makes it easy to see where time is being spent — a high Intent stage time, for example, suggests intent specs are being heavily edited.

### Gate pass rate
Percentage of tasks that pass each stage gate on the first attempt. A low pass rate at the Verify stage indicates the Primary Agent is producing code that fails tests or lint. A low pass rate at QA indicates intent quality issues.

### Loopback rate
Percentage of tasks that loop back from QA to Implement. Target under 15%. Rates above 20% consistently indicate a systemic issue — usually vague intent specifications or a mismatch between the selected expert and the task domain.

### Cost per task
Average LLM spend per completed task. An upward trend indicates increasingly complex issues, more loopbacks, or degrading agent efficiency. Compare cost per task against cycle time to understand the quality-cost trade-off.

## Charts available

- **Throughput over time** — daily bar chart showing tasks completed; compare against imported to see if the queue is growing
- **Stage bottleneck heatmap** — colour-coded by average dwell time, so the most congested stage stands out immediately
- **Expert performance table** — pass rate, loopback rate, average cost, and trend for each expert agent

## Using analytics to improve quality

A systematic improvement loop:

1. Find the stage with the **lowest gate pass rate** in the heatmap
2. Open the **Activity Log** filtered to that stage and set the time range to the last 7 days
3. Read the gate rejection reasons — look for repeating patterns
4. Adjust routing rules (if wrong experts are being selected) or intent prompt guidelines (if intent quality is low)
5. Check the next week's metrics to confirm the pass rate improved

## Period selector

Use the period selector (top right) to switch between last 7 days, 30 days, 90 days, or a custom range. Longer ranges reveal seasonality and long-term trends that are invisible in short windows.
