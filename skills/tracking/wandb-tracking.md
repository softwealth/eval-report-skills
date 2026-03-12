---
name: wandb
version: 0.19.x
category: tracking
trigger: 'when the user needs to track ML experiments, log metrics, manage model artifacts, run hyperparameter sweeps, or trace LLM calls'
updated: 2026-03-11
confidence: tested
eval_issue: 1
---

# Weights & Biases (wandb) v0.19.x

## When to Use

- You need to track training metrics (loss, accuracy, learning rate) across experiments
- You want to compare multiple experiment runs side-by-side
- You need to version datasets and model artifacts
- You want hyperparameter sweeps with Bayesian optimization
- You need to trace and evaluate LLM application calls (via Weave)
- You're using HuggingFace Transformers and want automatic logging
- You need collaborative experiment tracking across a team

## When NOT to Use

- You want fully local-only tracking with no cloud option -> use MLflow instead
- You need only simple CSV logging -> just use a CSV/JSON file
- You're in an air-gapped environment permanently -> use MLflow or TensorBoard
- You want free unlimited private projects for large teams -> use MLflow (self-hosted)
- You only need training visualization -> TensorBoard is simpler and free

## Quick Start

```bash
pip install wandb==0.19.*

# Login (one-time)
wandb login  # pastes API key from wandb.ai/authorize
```

```python
import wandb

# Initialize a run
run = wandb.init(
    project="my-project",
    config={
        "learning_rate": 3e-4,
        "batch_size": 32,
        "epochs": 10,
        "model": "resnet50",
    },
)

# Training loop
for epoch in range(10):
    train_loss = train_one_epoch()
    val_loss = evaluate()

    wandb.log({
        "epoch": epoch,
        "train/loss": train_loss,
        "val/loss": val_loss,
        "learning_rate": scheduler.get_last_lr()[0],
    })

# Always finish the run
wandb.finish()
```

## Common Patterns

### Basic experiment tracking with context manager

```python
import wandb

config = {
    "model": "llama-3.1-8b",
    "learning_rate": 2e-5,
    "lora_r": 16,
    "lora_alpha": 32,
    "epochs": 3,
    "batch_size": 4,
    "dataset": "my-instruct-v2",
}

with wandb.init(project="fine-tuning", config=config) as run:
    for step in range(1000):
        loss = train_step()
        wandb.log({"train/loss": loss, "step": step})

    # Log final metrics
    eval_results = evaluate()
    wandb.log({
        "eval/accuracy": eval_results["accuracy"],
        "eval/loss": eval_results["loss"],
    })

    # wandb.finish() called automatically by context manager
```

### HuggingFace Transformers integration

```python
from transformers import TrainingArguments, Trainer
import wandb

wandb.init(project="hf-training")

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    eval_strategy="steps",
    eval_steps=500,
    logging_steps=100,
    report_to="wandb",            # <-- This is the key line
    run_name="llama-lora-exp-1",  # Optional: name the run
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

trainer.train()
wandb.finish()
```

### Logging artifacts (models, datasets)

```python
import wandb

with wandb.init(project="my-project") as run:
    # Log a model artifact
    model_artifact = wandb.Artifact(
        name="fine-tuned-llama",
        type="model",
        description="LoRA fine-tuned Llama 3.1 8B on instruct data",
        metadata={"base_model": "meta-llama/Llama-3.1-8B", "lora_r": 16},
    )
    model_artifact.add_dir("./output/checkpoint-final")
    run.log_artifact(model_artifact)

    # Log a dataset artifact
    data_artifact = wandb.Artifact(
        name="instruct-dataset-v2",
        type="dataset",
        description="Curated instruction dataset, 50K examples",
    )
    data_artifact.add_file("./data/train.jsonl")
    data_artifact.add_file("./data/eval.jsonl")
    run.log_artifact(data_artifact)
```

### Downloading artifacts

```python
import wandb

run = wandb.init(project="my-project")

# Download latest version
artifact = run.use_artifact("fine-tuned-llama:latest")
artifact_dir = artifact.download()

# Download specific version
artifact = run.use_artifact("fine-tuned-llama:v3")
artifact_dir = artifact.download(root="./models/v3")
```

### Hyperparameter sweeps

```python
# sweep_config.yaml (or define as dict)
sweep_config = {
    "method": "bayes",  # bayes, grid, random
    "metric": {
        "name": "val/loss",
        "goal": "minimize",
    },
    "parameters": {
        "learning_rate": {
            "distribution": "log_uniform_values",
            "min": 1e-5,
            "max": 1e-3,
        },
        "batch_size": {"values": [4, 8, 16, 32]},
        "lora_r": {"values": [8, 16, 32, 64]},
        "warmup_ratio": {
            "distribution": "uniform",
            "min": 0.0,
            "max": 0.2,
        },
    },
}

def train():
    with wandb.init() as run:
        config = wandb.config
        # Use config.learning_rate, config.batch_size, etc.
        model = build_model(lr=config.learning_rate, lora_r=config.lora_r)
        for epoch in range(3):
            loss = train_epoch(model, batch_size=config.batch_size)
            val_loss = evaluate(model)
            wandb.log({"train/loss": loss, "val/loss": val_loss})

# Create and run sweep
sweep_id = wandb.sweep(sweep_config, project="sweep-example")
wandb.agent(sweep_id, function=train, count=20)  # Run 20 trials
```

### Logging tables, images, and media

```python
import wandb

with wandb.init(project="eval") as run:
    # Log a table of predictions
    table = wandb.Table(columns=["input", "prediction", "ground_truth", "correct"])
    for sample in eval_samples:
        pred = model.predict(sample["input"])
        table.add_data(
            sample["input"],
            pred,
            sample["label"],
            pred == sample["label"],
        )
    wandb.log({"predictions": table})

    # Log images
    images = [wandb.Image(img, caption=f"Sample {i}") for i, img in enumerate(batch)]
    wandb.log({"examples": images})
```

### Offline mode

```bash
# Set environment variable before running
export WANDB_MODE=offline

# Or in Python
import os
os.environ["WANDB_MODE"] = "offline"

import wandb
wandb.init(project="my-project")  # Logs locally only

# Sync later when you have internet
wandb sync ./wandb/offline-run-*
```

### Weave for LLM tracing

```python
import weave

# Initialize Weave tracing
weave.init("my-llm-app")

@weave.op()
def generate_response(prompt: str) -> str:
    """Traced function — inputs, outputs, and latency are logged."""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# Every call to generate_response is now traced in Weave
result = generate_response("Explain LCEL in one sentence")
```

## Configuration Reference

### wandb.init() parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| project | None | Project name (required) |
| name | auto-generated | Run display name |
| config | {} | Hyperparameters dict |
| tags | [] | List of tags for filtering |
| group | None | Group related runs |
| job_type | None | Type: "train", "eval", "sweep" |
| notes | None | Free-text description |
| mode | "online" | "online", "offline", "disabled" |
| resume | None | "allow", "must", "never", or run ID |
| dir | "./wandb" | Local log directory |

### Environment variables

| Variable | Description |
|----------|-------------|
| WANDB_API_KEY | API key (alternative to wandb login) |
| WANDB_PROJECT | Default project name |
| WANDB_MODE | online, offline, disabled |
| WANDB_DIR | Local log directory |
| WANDB_ENTITY | Team/user name |
| WANDB_RUN_GROUP | Group name |
| WANDB_DISABLED | Set to "true" to disable |

### wandb.log() tips

| Pattern | Description |
|---------|-------------|
| wandb.log({"loss": 0.5}) | Log a scalar |
| wandb.log({"loss": 0.5}, step=100) | Log with explicit step |
| wandb.log({"train/loss": 0.5, "train/acc": 0.9}) | Grouped metrics (slash = section) |
| wandb.log({"table": wandb.Table(...)}) | Log a table |
| wandb.log({"img": wandb.Image(array)}) | Log an image |

## Pitfalls & Gotchas

- **Forgetting wandb.finish()**: If you don't call `wandb.finish()` (or use a context manager), the run may not sync properly. Data can be lost. Always finish your runs.
- **Multiple wandb.init() calls**: Calling `wandb.init()` twice without `wandb.finish()` in between creates problems. Each script should have one active run at a time.
- **Config immutability**: `wandb.config` is meant to be set once at init. You can update it with `wandb.config.update({"key": val})`, but don't treat it like a log — use `wandb.log()` for time-series data.
- **Slow logging**: Don't call `wandb.log()` on every single training sample. Log every N steps (e.g., every 10-100 steps). Frequent logging slows training.
- **Large artifacts**: Artifacts upload can be slow for large model checkpoints. Consider logging only the best checkpoint, not every one.
- **HuggingFace integration gotcha**: Must set `report_to="wandb"` in TrainingArguments. If both `report_to="wandb"` and `report_to="tensorboard"` are set, both run (more overhead).
- **Offline sync**: Offline runs accumulate in ./wandb/. You must manually `wandb sync` them. They can grow large.
- **API key in CI/CD**: Use `WANDB_API_KEY` env var in CI, not interactive login. Add `WANDB_MODE=disabled` for test runs that shouldn't be tracked.

## Compared To

| Feature | wandb | MLflow | TensorBoard | Neptune | CometML |
|---------|-------|--------|-------------|---------|---------|
| Cloud hosted | Yes (free tier) | Self-host | No | Yes | Yes |
| Self-hosted | Yes (enterprise) | Yes (free) | Local only | No | No |
| Experiment tracking | Excellent | Good | Basic | Good | Good |
| Artifact versioning | Yes | Yes | No | Yes | Yes |
| Hyperparameter sweeps | Built-in | Limited | No | Built-in | Built-in |
| LLM tracing | Weave | MLflow Tracing | No | No | No |
| HF Transformers | One-line | Plugin | Callback | Plugin | Plugin |
| Collaboration | Excellent | Good | Limited | Good | Good |
| Free tier | 100GB storage | Unlimited (self) | Free | Limited | Limited |
