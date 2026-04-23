from __future__ import annotations
import json
import asyncio
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

async def run_agents_async(dataset: str, out_dir: str, reflexion_attempts: int):
    examples = load_dataset(dataset)
    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)
    
    print(f"[bold blue]Starting Concurrent Benchmark[/bold blue] on {len(examples)} examples...")
    
    batch_size = 10
    
    async def run_in_batches(agent, name):
        records = []
        for i in range(0, len(examples), batch_size):
            batch_num = (i // batch_size) + 1
            total_batches = (len(examples) + batch_size - 1) // batch_size
            print(f"\n[bold green]Running {name} Batch {batch_num}/{total_batches}[/bold green]")
            
            batch_examples = examples[i:i + batch_size]
            tasks = [agent.run(ex) for ex in batch_examples]
            batch_results = await asyncio.gather(*tasks)
            records.extend(batch_results)
            
            for j, res in enumerate(batch_results):
                status = "Correct" if res.is_correct else "Incorrect"
                print(f"  - Example {i+j+1}/{len(examples)}: {res.qid} [{status}]")
                
        return records

    # Chạy ReAct
    react_records = await run_in_batches(react, "ReAct")
        
    # Chạy Reflexion
    reflexion_records = await run_in_batches(reflexion, "Reflexion")
        
    all_records = list(react_records) + list(reflexion_records)
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    report = build_report(all_records, dataset_name=Path(dataset).name, mode="vllm_async")
    json_path, md_path = save_report(report, out_path)
    
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

@app.command()
def main(dataset: str = "data/hotpot_100.json", out_dir: str = "outputs/vllm_run", reflexion_attempts: int = 3) -> None:
    asyncio.run(run_agents_async(dataset, out_dir, reflexion_attempts))

if __name__ == "__main__":
    app()
