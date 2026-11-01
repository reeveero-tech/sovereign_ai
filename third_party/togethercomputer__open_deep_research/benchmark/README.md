### Running Benchmarks

```bash
# Set Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)/../src

# Run benchmarks
python scoring.py --datasets together-search-bench --agent-config ../configs/base_llm_config.yaml --max-workers 10

# Summarize results
python summary.py
```

#### Benchmark Options
- `--datasets`: Benchmark dataset to use (e.g., `together-search-bench`)
- `--limit`: Number of examples to process
- `--agent-config`: Path to LLM configuration file
- `--max-workers`: Number of parallel workers

> **Note:** For LangChain's Open-Deep-Research benchmarks, we replace instructions with "You must perform in-depth research to answer the question" instead of "Rules: The answer is usually very short. It might be a number or two words. It's definitely not a sentence." Otherwise, the planner will refuse to generate research reports.