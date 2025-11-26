# Training Call Tree: Start Training Button to Completion

**Created:** 2025-11-25  
**Purpose:** Detailed call tree tracing the flow from clicking "Start Training" button until training is finished

---

## Overview

This document traces the complete execution flow from when a user clicks the "🚀 Start Training" button in the Admin UI (`localhost:3001/admin`) until the training job completes. The flow spans frontend React components, API calls, backend FastAPI endpoints, database operations, and a subprocess training script.

---

## Call Tree Structure

```
FRONTEND (React/TypeScript)
    ↓
API CLIENT (HTTP)
    ↓
BACKEND (FastAPI/Python)
    ↓
DATABASE (SQLite via SQLAlchemy)
    ↓
TRAINING SCRIPT (Subprocess)
    ↓
COMPLETION & STATUS UPDATES
```

---

## Detailed Call Tree

### 1. FRONTEND - User Interaction

**File:** `services/ai-automation-ui/src/pages/Admin.tsx`

```
Admin Component
└── Line 349-363: "Start Training" Button
    └── onClick Handler
        └── trainingMutation.mutate()
            └── Line 85-96: useMutation Hook Configuration
                ├── mutationFn: triggerTrainingRun (imported from '../api/admin')
                ├── onSuccess: 
                │   ├── toast.success('✅ Training job started')
                │   ├── queryClient.invalidateQueries(['training-runs'])
                │   └── queryClient.invalidateQueries(['admin-overview'])
                └── onError:
                    └── toast.error('❌ {error message}')
```

**Key State:**
- `trainingMutation.isPending` - Controls button disabled state and "🚧 Starting…" text
- `hasActiveTrainingRun` - Disables button if training already running (computed from `trainingRuns` query)

---

### 2. FRONTEND - API Client Call

**File:** `services/ai-automation-ui/src/api/admin.ts`

```
triggerTrainingRun()
├── Line 132-144: Function Definition
├── Line 133-135: Build Auth Headers
│   └── withAuthHeaders()
│       ├── Authorization: Bearer {API_KEY}
│       └── X-HomeIQ-API-Key: {API_KEY}
├── Line 137-141: HTTP POST Request
│   └── fetch(`${ADMIN_BASE}/training/trigger`, {
│       method: 'POST',
│       headers: withAuthHeaders(),
│       credentials: 'include'
│   })
└── Line 143: Handle Response
    └── handleResponse<TrainingRunRecord>(response)
        ├── If response.ok: return response.json()
        └── Else: throw Error(message)
```

**Network Request:**
- **URL:** `/api/v1/admin/training/trigger`
- **Method:** POST
- **Headers:** Authorization + X-HomeIQ-API-Key
- **Response:** `TrainingRunRecord` JSON

---

### 3. BACKEND - API Route Handler

**File:** `services/ai-automation-service/src/api/admin_router.py`

#### 3.1 Route Definition & Authentication

```
POST /api/v1/admin/training/trigger
├── Line 308-312: Route Decorator
│   ├── @router.post("/training/trigger")
│   ├── response_model=TrainingRunResponse
│   └── status_code=status.HTTP_202_ACCEPTED (202 Accepted)
└── Line 313: Handler Function
    └── trigger_training_run(db: AsyncSession = Depends(get_db))
```

**Dependencies:**
- `require_admin_user` - Middleware check (via router dependency at line 41)
- `get_db` - Database session dependency

---

#### 3.2 Training Job Initiation

```
trigger_training_run()
├── Line 316: Acquire Training Lock
│   └── async with _training_job_lock:
│       └── Prevents concurrent training jobs
│
├── Line 317: Validate Training Script
│   └── script_path = _validate_training_script_path()
│       ├── Line 55-83: _validate_training_script_path()
│       ├── Resolve path from settings.training_script_path
│       ├── Check file exists
│       ├── Verify script is within PROJECT_ROOT (security)
│       └── Optional: Verify SHA256 hash if configured
│
├── Line 318: Check for Active Training
│   └── active = await get_active_training_run(db)
│       └── Line 139-153 (database/crud.py): get_active_training_run()
│           ├── SELECT * FROM training_runs
│           ├── WHERE status = 'running'
│           ├── AND training_type = 'soft_prompt' (default)
│           └── LIMIT 1
│       └── If active exists:
│           └── Raise HTTPException(409, "A training job is already running")
│
├── Line 325: Generate Run Identifier
│   └── run_identifier = datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
│       └── Example: "run_20251125_195644"
│
├── Line 326-327: Setup Output Directories
│   ├── base_output_dir = _resolve_path(settings.soft_prompt_model_dir)
│   └── run_directory = base_output_dir / run_identifier
│       └── Example: data/ask_ai_soft_prompt/run_20251125_195644
│
├── Line 329-339: Create Training Run Record
│   └── run_record = await create_training_run(db, {
│       "training_type": "soft_prompt",
│       "status": "queued",
│       "started_at": datetime.utcnow(),
│       "output_dir": str(run_directory),
│       "run_identifier": run_identifier,
│       "triggered_by": "admin"
│   })
│       └── Line 156-163 (database/crud.py): create_training_run()
│           ├── Create TrainingRun model instance
│           ├── db.add(run)
│           ├── await db.commit()
│           └── await db.refresh(run)
│
├── Line 341-349: Launch Background Task
│   └── asyncio.create_task(
│       _execute_training_run(
│           run_record.id,
│           run_identifier,
│           base_output_dir,
│           run_directory,
│           script_path
│       )
│   )
│   └── Returns immediately (non-blocking)
│
└── Line 351: Return Response
    └── return TrainingRunResponse.model_validate(run_record, from_attributes=True)
        └── Returns 202 Accepted with run record JSON
```

**Database Operations:**
- **INSERT** into `training_runs` table with status='queued'
- **SELECT** to check for active runs

---

### 4. BACKEND - Background Training Execution

**File:** `services/ai-automation-service/src/api/admin_router.py`

```
_execute_training_run(
    run_id: int,
    run_identifier: str,
    base_output_dir: Path,
    run_directory: Path,
    script_path: Path
)
├── Line 151-153: Setup Paths & Directories
│   ├── db_path = _resolve_path(settings.database_path)
│   ├── base_output_dir.mkdir(parents=True, exist_ok=True)
│   └── run_directory.mkdir(parents=True, exist_ok=True)
│
├── Line 155-162: Build Command
│   └── command = [
│       sys.executable,                      # Python interpreter
│       str(script_path),                    # scripts/train_soft_prompt.py
│       "--db-path", str(db_path),
│       "--output-dir", str(base_output_dir),
│       "--run-directory", str(run_directory),
│       "--run-id", run_identifier
│   ]
│
├── Line 164: Update Status to "running"
│   └── await _update_training_status(run_id, {"status": "running"})
│       └── Line 137-139: _update_training_status()
│           └── await update_training_run(db, run_id, updates)
│               └── Line 166-180 (database/crud.py): update_training_run()
│                   ├── SELECT * FROM training_runs WHERE id = run_id
│                   ├── Update fields from updates dict
│                   ├── await db.commit()
│                   └── await db.refresh(run)
│
├── Line 166-178: Configure Environment
│   └── env = os.environ.copy()
│       ├── env['HF_HOME'] = models directory
│       └── env['TRANSFORMERS_CACHE'] = models directory
│
├── Line 172-178: Launch Subprocess
│   └── process = await asyncio.create_subprocess_exec(
│       *command,
│       stdout=asyncio.subprocess.PIPE,
│       stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
│       cwd=str(PROJECT_ROOT),
│       env=env
│   )
│
├── Line 179: Wait for Process Completion
│   └── stdout, _ = await process.communicate()
│       └── BLOCKS until training script finishes
│
├── Line 182-188: Read Training Metadata
│   └── metadata_path = run_directory / "training_run.json"
│       └── If exists:
│           └── metadata = json.loads(metadata_path.read_text())
│               └── Contains: samples_used, base_model, final_loss, etc.
│
├── Line 190-198: Prepare Status Updates
│   └── updates = {
│       "status": "completed" if success else "failed",
│       "finished_at": datetime.utcnow(),
│       "metadata_path": str(metadata_path) if exists else None,
│       "dataset_size": metadata.get("samples_used"),
│       "base_model": metadata.get("base_model"),
│       "final_loss": metadata.get("final_loss")
│   }
│
├── Line 200-206: Handle Failure Case
│   └── If not success:
│       ├── error_output = stdout.decode(errors="ignore")
│       ├── logger.error("Training script failed...")
│       └── updates["error_message"] = error_output[-5000:]  # Limit length
│
├── Line 208: Update Database with Results
│   └── await _update_training_status(run_id, updates)
│
└── Line 209-218: Exception Handler
    └── If exception occurs:
        └── await _update_training_status(run_id, {
            "status": "failed",
            "finished_at": datetime.utcnow(),
            "error_message": str(exc)
        })
```

**Database Operations:**
- **UPDATE** training_runs SET status='running' WHERE id=run_id
- **UPDATE** training_runs SET status='completed'/'failed', finished_at, metadata WHERE id=run_id

---

### 5. TRAINING SCRIPT - Subprocess Execution

**File:** `services/ai-automation-service/scripts/train_soft_prompt.py`

#### 5.1 Script Entry Point

```
main()
├── Line 222-223: Initialize Logging & Parse Args
│   ├── logging.basicConfig(level=logging.INFO)
│   └── args = parse_args()
│       └── Line 21-114: parse_args()
│           └── Parses command-line arguments:
│               ├── --db-path
│               ├── --output-dir
│               ├── --run-directory
│               ├── --run-id
│               ├── --base-model (default: "google/flan-t5-small")
│               ├── --max-samples (default: 2000)
│               ├── --epochs (default: 3)
│               └── ... other training hyperparameters
│
├── Line 225: Check Dependencies
│   └── ensure_dependencies()
│       └── Line 167-175: ensure_dependencies()
│           ├── import torch
│           ├── from transformers import AutoTokenizer
│           └── from peft import LoraConfig
│           └── Raises RuntimeError if missing
│
├── Line 227: Generate/Use Run ID
│   └── run_identifier = args.run_id or datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
│
└── Line 229-234: Load Training Data
    └── examples = load_training_examples(args.db_path, args.max_samples)
        └── Line 117-164: load_training_examples()
            ├── Connect to SQLite database
            ├── Query: SELECT original_query, suggestions
            │   FROM ask_ai_queries
            │   WHERE suggestions IS NOT NULL
            │   ORDER BY created_at DESC
            │   LIMIT ?
            ├── For each row:
            │   ├── Parse suggestions JSON
            │   ├── Sort by confidence (descending)
            │   ├── Take top suggestion
            │   └── Create {instruction, response} pair
            └── Return List[Dict[str, str]]
        └── If no examples:
            └── logger.error("No Ask AI labelled data available.")
            └── return (script exits)
```

---

#### 5.2 Model & Dataset Preparation

```
main() (continued)
├── Line 234: Log Examples Count
│   └── logger.info("Loaded %s training examples", len(examples))
│
├── Line 236-237: Import ML Libraries
│   ├── from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, Trainer, TrainingArguments
│   └── from peft import LoraConfig, get_peft_model
│
├── Line 239: Load Tokenizer
│   └── tokenizer = AutoTokenizer.from_pretrained(args.base_model)
│       └── Downloads/caches from HuggingFace Hub if needed
│
├── Line 241-246: Prepare Dataset
│   └── dataset = prepare_dataset(
│       tokenizer,
│       examples,
│       max_source_tokens=args.source_max_tokens,
│       max_target_tokens=args.target_max_tokens
│   )
│       └── Line 178-218: prepare_dataset()
│           ├── Defines PromptDataset class (torch.utils.data.Dataset)
│           ├── __getitem__ method:
│           │   ├── Tokenize instruction → source input_ids, attention_mask
│           │   ├── Tokenize response → target input_ids
│           │   ├── Create labels (mask padding tokens with -100)
│           │   └── Return {input_ids, attention_mask, labels}
│           └── Returns dataset instance
│
├── Line 248: Load Base Model
│   └── model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model)
│       └── Downloads/caches from HuggingFace Hub if needed
│
└── Line 250-258: Configure LoRA Adapters
    └── lora_config = LoraConfig(
        r=args.lora_r,                    # Rank (default: 16)
        lora_alpha=args.lora_alpha,       # Scaling (default: 16.0)
        target_modules=["q", "v"],        # Attention modules
        lora_dropout=args.lora_dropout,   # Dropout (default: 0.05)
        bias="none",
        task_type="SEQ_2_SEQ_LM"
    )
    └── model = get_peft_model(model, lora_config)
        └── Wraps model with LoRA adapters for efficient fine-tuning
```

---

#### 5.3 Training Loop

```
main() (continued)
├── Line 260-262: Optional Resume from Checkpoint
│   └── If args.resume_from:
│       └── model.load_adapter(str(args.resume_from))
│
├── Line 264-266: Ensure Output Directories Exist
│   ├── args.output_dir.mkdir(parents=True, exist_ok=True)
│   └── run_dir = args.run_directory or (args.output_dir / run_identifier)
│       └── run_dir.mkdir(parents=True, exist_ok=True)
│
├── Line 268-282: Configure Training Arguments
│   └── training_args = TrainingArguments(
│       output_dir=str(run_dir),
│       per_device_train_batch_size=args.batch_size,      # Default: 2
│       gradient_accumulation_steps=4,
│       num_train_epochs=args.epochs,                     # Default: 3
│       learning_rate=args.learning_rate,                 # Default: 5e-5
│       logging_dir=str(run_dir / "logs"),
│       logging_steps=10,
│       save_strategy="epoch",                            # Save after each epoch
│       evaluation_strategy="no",                         # No validation set
│       report_to=["none"],                               # No wandb/tensorboard
│       dataloader_drop_last=False,
│       bf16=False,                                       # CPU-friendly
│       fp16=False                                        # CPU-friendly
│   )
│
├── Line 284-289: Initialize Trainer
│   └── trainer = Trainer(
│       model=model,
│       args=training_args,
│       train_dataset=dataset,
│       tokenizer=tokenizer
│   )
│
└── Line 291: Execute Training
    └── train_result = trainer.train()
        └── HuggingFace Transformers Trainer.train()
            ├── Iterates over dataset for num_train_epochs epochs
            ├── Forward pass: model(input_ids, attention_mask, labels)
            ├── Compute loss (cross-entropy)
            ├── Backward pass: gradient computation
            ├── Optimizer step (Adam/AdamW)
            ├── Logging every 10 steps
            └── Saves checkpoint after each epoch
            └── Returns TrainingOutput with training_loss
```

---

#### 5.4 Save Artifacts & Metadata

```
main() (continued)
├── Line 292: Save Model
│   └── trainer.save_model(str(run_dir))
│       └── Saves LoRA adapter weights to run_dir/
│
├── Line 293: Save Tokenizer
│   └── tokenizer.save_pretrained(run_dir)
│       └── Saves tokenizer files (tokenizer_config.json, vocab, etc.)
│
├── Line 295-304: Create Metadata Dictionary
│   └── metadata = {
│       "base_model": args.base_model,
│       "samples_used": len(examples),
│       "epochs": args.epochs,
│       "learning_rate": args.learning_rate,
│       "run_directory": str(run_dir),
│       "trained_at": datetime.utcnow().isoformat(),
│       "final_loss": train_result.training_loss,
│       "run_id": run_identifier
│   }
│
├── Line 306-307: Write Metadata File
│   └── with open(run_dir / "training_run.json", "w") as fp:
│       └── json.dump(metadata, fp, indent=2)
│
└── Line 309-312: Create "latest" Symlink
    └── latest_symlink = args.output_dir / "latest"
        ├── If exists: latest_symlink.unlink()
        └── latest_symlink.symlink_to(run_dir, target_is_directory=True)
            └── Creates: data/ask_ai_soft_prompt/latest → data/ask_ai_soft_prompt/run_20251125_195644
```

**File System Operations:**
- Creates directory: `data/ask_ai_soft_prompt/run_YYYYMMDD_HHMMSS/`
- Saves model weights, tokenizer, and training metadata
- Creates symlink: `data/ask_ai_soft_prompt/latest` → run directory

---

#### 5.5 Script Completion

```
main() (continued)
└── Line 314: Log Completion
    └── logger.info("Training complete. Artifacts written to %s", run_dir)
        └── Script exits with return code 0 (success)
```

**Return to:** `_execute_training_run()` in `admin_router.py` (line 179)

---

### 6. BACKEND - Process Completion Handling

**File:** `services/ai-automation-service/src/api/admin_router.py`

```
_execute_training_run() (continued)
├── Line 179: Process Communication Completes
│   └── stdout, _ = await process.communicate()
│       └── Returns when subprocess exits
│
├── Line 182-188: Read Metadata (see section 4)
├── Line 190-198: Prepare Updates (see section 4)
├── Line 200-206: Handle Errors (see section 4)
│
└── Line 208: Final Database Update
    └── await _update_training_status(run_id, updates)
        └── UPDATE training_runs SET
            status = 'completed' | 'failed',
            finished_at = datetime.utcnow(),
            dataset_size = metadata.samples_used,
            base_model = metadata.base_model,
            final_loss = metadata.final_loss,
            metadata_path = 'path/to/training_run.json',
            error_message = NULL | 'error text'
            WHERE id = run_id
```

---

### 7. FRONTEND - Status Polling

**File:** `services/ai-automation-ui/src/pages/Admin.tsx`

#### 7.1 Automatic Refetch

```
useQuery Hook (Line 56-64)
├── queryKey: ['training-runs']
├── queryFn: () => getTrainingRuns(25)
└── refetchInterval: 60_000  # Poll every 60 seconds
    └── getTrainingRuns()
        └── services/ai-automation-ui/src/api/admin.ts:118-130
            └── GET /api/v1/admin/training/runs?limit=25
                └── Backend: list_training_runs_endpoint()
                    └── services/ai-automation-service/src/api/admin_router.py:289-305
                        ├── SELECT * FROM training_runs
                        ├── WHERE training_type = 'soft_prompt'
                        ├── ORDER BY started_at DESC
                        └── LIMIT 25
```

#### 7.2 UI Updates

```
Training Runs Table (Line 372-417)
├── Displays: Run, Status, Samples, Loss, Started, Finished, Notes
├── Status Badge Colors:
│   ├── completed: green
│   ├── running: blue
│   └── failed/queued: yellow
└── Button State Updates:
    ├── hasActiveTrainingRun (Line 157-160)
    │   └── Checks if any run.status === 'running'
    └── Button disabled if:
        ├── trainingMutation.isPending, OR
        └── hasActiveTrainingRun
```

---

## Complete Flow Sequence Diagram

```
User Click "Start Training"
    ↓
[Frontend] trainingMutation.mutate()
    ↓
[Frontend] triggerTrainingRun() API call
    ↓
[Network] POST /api/v1/admin/training/trigger
    ↓
[Backend] trigger_training_run()
    ├── Check active training (GET training_runs WHERE status='running')
    ├── Create run record (INSERT training_runs status='queued')
    └── Launch background task
        ↓
    [Backend] _execute_training_run()
        ├── Update status='running' (UPDATE training_runs)
        ├── Launch subprocess: python scripts/train_soft_prompt.py
        │   ↓
        │   [Script] main()
        │   ├── Load training examples (SELECT from ask_ai_queries)
        │   ├── Load base model & tokenizer (HuggingFace)
        │   ├── Prepare dataset
        │   ├── Configure LoRA adapters
        │   ├── trainer.train() (3 epochs by default)
        │   ├── Save model & tokenizer
        │   ├── Write training_run.json metadata
        │   └── Create latest symlink
        │       ↓
        │   Script exits (return code 0 or non-zero)
        │
        ├── Read training_run.json
        ├── Update status='completed'/'failed' (UPDATE training_runs)
        └── Log results
    ↓
[Frontend] Response 202 Accepted with run record
    ├── Show toast: "✅ Training job started"
    └── Invalidate queries (triggers refetch)
        ↓
[Frontend] Polling (every 60s)
    └── GET /api/v1/admin/training/runs
        └── Update table with latest status
```

---

## Key Files & Line References

### Frontend
- `services/ai-automation-ui/src/pages/Admin.tsx`
  - Line 349-363: Start Training button
  - Line 85-96: Training mutation configuration
  - Line 56-64: Training runs query with polling

- `services/ai-automation-ui/src/api/admin.ts`
  - Line 132-144: triggerTrainingRun() function
  - Line 118-130: getTrainingRuns() function

### Backend
- `services/ai-automation-service/src/api/admin_router.py`
  - Line 308-351: trigger_training_run() endpoint
  - Line 142-218: _execute_training_run() background task
  - Line 137-139: _update_training_status() helper
  - Line 55-83: _validate_training_script_path() security check

- `services/ai-automation-service/src/database/crud.py`
  - Line 139-153: get_active_training_run()
  - Line 156-163: create_training_run()
  - Line 166-180: update_training_run()
  - Line 183-204: list_training_runs()

- `services/ai-automation-service/src/database/models.py`
  - Line 946-975: TrainingRun model definition

### Training Script
- `services/ai-automation-service/scripts/train_soft_prompt.py`
  - Line 221-318: main() function
  - Line 117-164: load_training_examples()
  - Line 178-218: prepare_dataset()
  - Line 167-175: ensure_dependencies()

---

## Database Schema

**Table:** `training_runs`

```sql
CREATE TABLE training_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    training_type VARCHAR(20) NOT NULL DEFAULT 'soft_prompt',
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    dataset_size INTEGER,
    base_model VARCHAR,
    output_dir VARCHAR,
    run_identifier VARCHAR UNIQUE,
    final_loss FLOAT,
    error_message TEXT,
    metadata_path VARCHAR,
    triggered_by VARCHAR NOT NULL DEFAULT 'admin',
    iteration_history_json JSON
);

CREATE INDEX idx_training_runs_status ON training_runs(status);
CREATE INDEX idx_training_runs_started_at ON training_runs(started_at);
CREATE INDEX idx_training_runs_run_identifier ON training_runs(run_identifier);
```

**Status Flow:**
1. `queued` - Created when user clicks button
2. `running` - Updated when subprocess starts
3. `completed` - Updated when subprocess exits with code 0
4. `failed` - Updated when subprocess exits with non-zero code or exception

---

## Error Handling

### Frontend Errors
- **Network Error:** Toast error message, mutation error handler
- **409 Conflict:** "A training job is already running" - shown in toast
- **500 Server Error:** Generic error message from API

### Backend Errors
- **Active Training Exists:** HTTP 409 Conflict
- **Script Not Found:** HTTP 500 with detail message
- **Script Hash Mismatch:** HTTP 500 (security check)
- **Script Execution Failure:** Status updated to 'failed' with error_message

### Script Errors
- **No Training Data:** Script exits with error log, return code non-zero
- **Missing Dependencies:** RuntimeError raised, return code non-zero
- **Training Failure:** Exception logged, return code non-zero
- **All errors captured in stdout/stderr and stored in training_runs.error_message**

---

## Performance Characteristics

### Timing Estimates
- **API Response:** ~50-200ms (database queries + validation)
- **Subprocess Launch:** ~100-500ms (directory creation, env setup)
- **Training Duration:** Highly variable
  - Small dataset (<100 examples): 1-5 minutes
  - Medium dataset (100-1000 examples): 5-30 minutes
  - Large dataset (1000+ examples): 30+ minutes
- **Status Polling:** Every 60 seconds (configurable via refetchInterval)

### Resource Usage
- **CPU:** Training script uses CPU (no GPU by default)
- **Memory:** Base model + LoRA adapters + dataset in memory
- **Disk:** Model weights, tokenizer, metadata files (~50-200MB per run)
- **Network:** Initial model download from HuggingFace Hub (cached after first use)

---

## Security Considerations

1. **Authentication:** All endpoints require admin user (via `require_admin_user` dependency)
2. **Script Validation:** Script path must be within PROJECT_ROOT
3. **Hash Verification:** Optional SHA256 hash check (if configured)
4. **Concurrent Execution:** Lock prevents multiple training jobs
5. **Error Sanitization:** Error messages limited to 5000 chars for database storage

---

## Notes

- The training job runs **asynchronously** - the API returns 202 Accepted immediately
- The frontend **polls** for status updates every 60 seconds
- Training artifacts are saved to `data/ask_ai_soft_prompt/run_YYYYMMDD_HHMMSS/`
- A symlink `data/ask_ai_soft_prompt/latest` points to the most recent successful run
- The soft prompt adapter is **not automatically reloaded** after training completes - a service restart or manual reload via settings may be required

---

**End of Call Tree**

