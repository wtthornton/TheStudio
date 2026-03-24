# Analytics

The Analytics tab provides operational metrics to help you understand pipeline health, throughput, and agent performance over time.

## Key metrics

### Throughput
Tasks completed per day/week. A healthy pipeline processes issues within 2–4 hours from triage to published PR.

### Cycle time
Time from issue import to PR publication. Broken down by stage so you can identify bottlenecks.

### Gate pass rate
Percentage of tasks that pass each stage gate on the first attempt. Low pass rates indicate a stage needs tuning.

### Loopback rate
Percentage of tasks that loop back from QA to Implement. Target < 15%. High loopback rates usually mean the intent spec quality is low.

### Cost per task
Average LLM spend per completed task. Trends upward indicate increasingly complex issues or degrading agent efficiency.

## Charts available

- **Throughput over time** — bar chart by day
- **Stage bottleneck heatmap** — where tasks spend the most time
- **Expert performance table** — pass rate and average cost by expert agent

## Using analytics to improve quality

1. Find the stage with the lowest gate pass rate
2. Open the Activity Log filtered to that stage
3. Read the rejection reasons to identify patterns
4. Adjust routing rules or intent prompts accordingly
