# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_100.json
- Mode: vllm_async
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.97 | 0.97 | 0.0 |
| Avg attempts | 1 | 1.06 | 0.06 |
| Avg token estimate | 730.38 | 775.14 | 44.76 |
| Avg latency (ms) | 1817.86 | 1806.68 | -11.18 |

## Failure modes
```json
{
  "react": {
    "none": 97,
    "wrong_final_answer": 3
  },
  "reflexion": {
    "none": 97,
    "wrong_final_answer": 3
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
