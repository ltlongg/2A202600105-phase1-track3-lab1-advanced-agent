from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Literal
from .llm_client import call_llm
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord, JudgeResult

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1

    def _get_actor_prompt(self, example: QAExample, reflection_memory: list[str]) -> str:
        ctx_text = "\n\n".join([f"Source: {c.title}\nContent: {c.text}" for c in example.context])
        prompt = f"Context:\n{ctx_text}\n\nQuestion: {example.question}"
        if reflection_memory:
            history = "\n".join([f"- {r}" for r in reflection_memory])
            prompt += f"\n\nReflections from previous failed attempts:\n{history}\n\nPlease learn from these and try again."
        return prompt

    async def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        
        for attempt_id in range(1, self.max_attempts + 1):
            # 1. Actor step
            actor_input = self._get_actor_prompt(example, reflection_memory)
            actor_res = await call_llm(ACTOR_SYSTEM, actor_input)
            answer = actor_res["content"].strip()
            print(f"Predicted Answer: {answer}")
            # 2. Evaluator step
            eval_input = f"Question: {example.question}\nGold Answer: {example.gold_answer}\nPredicted Answer: {answer}"
            eval_res = await call_llm(EVALUATOR_SYSTEM, eval_input, response_format="json")
            print(f"Evaluator Response: {eval_res['content']}")
            try:
                judge_data = json.loads(eval_res["content"])
                judge = JudgeResult(**judge_data)
            except Exception:
                # Fallback nếu JSON parse lỗi
                judge = JudgeResult(score=0, reason="Failed to parse evaluator response")

            total_step_tokens = actor_res["tokens"] + eval_res["tokens"]
            total_step_latency = actor_res["latency_ms"] + eval_res["latency_ms"]
            
            final_answer = answer
            final_score = judge.score

            reflection_entry = None
            
            # 3. Reflexion step (nếu sai và là mode reflexion)
            if self.agent_type == "reflexion" and judge.score == 0 and attempt_id < self.max_attempts:
                reflect_input = f"Question: {example.question}\nPredicted Answer: {answer}\nFailure Reason: {judge.reason}\nPrevious Reflections: {reflection_memory}"
                reflect_res = await call_llm(REFLECTOR_SYSTEM, reflect_input, response_format="json")
                print(f"Reflector Response: {reflect_res['content']}")

                try:
                    reflect_data = json.loads(reflect_res["content"])
                    reflection_entry = ReflectionEntry(**reflect_data)
                    reflections.append(reflection_entry)
                    
                    # Cập nhật memory từ bài học mới nhất
                    if reflection_entry.reflection_memory:
                        reflection_memory.extend(reflection_entry.reflection_memory)
                    
                    total_step_tokens += reflect_res["tokens"]
                    total_step_latency += reflect_res["latency_ms"]
                except Exception:
                    pass

            trace = AttemptTrace(
                attempt_id=attempt_id, 
                answer=answer, 
                score=judge.score, 
                reason=judge.reason, 
                reflection=reflection_entry,
                token_estimate=total_step_tokens, 
                latency_ms=total_step_latency
            )
            traces.append(trace)

            if judge.score == 1:
                break
            
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        
        failure_mode = "none" if final_score == 1 else "wrong_final_answer"
        if final_score == 0 and self.agent_type == "reflexion":
            # Có thể làm logic phân loại failure mode sâu hơn ở đây
            pass

        return RunRecord(
            qid=example.qid, 
            question=example.question, 
            gold_answer=example.gold_answer, 
            agent_type=self.agent_type, 
            predicted_answer=final_answer, 
            is_correct=bool(final_score), 
            attempts=len(traces), 
            token_estimate=total_tokens, 
            latency_ms=total_latency, 
            failure_mode=failure_mode, 
            reflections=reflections, 
            traces=traces
        )

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
