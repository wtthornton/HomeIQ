# Ollama Installation Guide for HomeIQ

**Target System:** Windows NUC with 16GB RAM  
**Model:** qwen2.5-coder:7b (~4.1 GB)

## Installation Methods

### Method 1: Direct Download (Recommended)

1. **Download Ollama:**
   - Visit: https://ollama.com/download/windows
   - Click "Download for Windows"
   - Save `OllamaSetup.exe` (~100 MB)

2. **Install:**
   - Run `OllamaSetup.exe`
   - Follow installation wizard
   - Ollama will auto-start as a service

3. **Verify Installation:**
   ```powershell
   ollama --version
   ```

### Method 2: Using winget (If Available)

```powershell
winget install Ollama.Ollama
```

### Method 3: Manual Download via PowerShell

```powershell
# Download installer
$url = "https://ollama.com/download/OllamaSetup.exe"
$output = "$env:USERPROFILE\Downloads\OllamaSetup.exe"
Invoke-WebRequest -Uri $url -OutFile $output

# Run installer
Start-Process $output -Wait
```

## Post-Installation Setup

### 1. Pull the Model

After Ollama is installed, pull the qwen2.5-coder:7b model:

```powershell
ollama pull qwen2.5-coder:7b
```

**Expected:**
- Download size: ~4.1 GB
- Time: 5-10 minutes (depending on internet speed)
- Disk space: ~4.2 GB total

### 2. Verify Installation

```powershell
# Check Ollama is running
ollama list

# Test the model
ollama run qwen2.5-coder:7b "Hello, can you code?"
```

### 3. Test TappsCodingAgents Connection

```powershell
# Test HTTP connection
python -c "import httpx; r = httpx.get('http://localhost:11434/api/tags', timeout=5.0); print('Ollama status:', r.status_code); print('Models:', [m['name'] for m in r.json().get('models', [])])"
```

### 4. Test Enhancer Agent

```powershell
# Now this should work with populated stages
python -m tapps_agents.cli enhancer enhance-quick "Add device health monitoring"
```

## System Requirements

- **RAM:** 16 GB ✅ (You have this)
- **Disk Space:** ~5 GB free (for Ollama + model)
- **CPU:** Any modern CPU (GPU optional but faster)
- **Network:** Internet connection for initial download

## Troubleshooting

### Ollama Not Starting

```powershell
# Check if service is running
Get-Service | Where-Object {$_.Name -like "*ollama*"}

# Start manually
ollama serve
```

### Port Already in Use

If port 11434 is in use:
```powershell
# Check what's using it
netstat -ano | findstr :11434

# Ollama uses port 11434 by default
```

### Model Download Fails

```powershell
# Retry download
ollama pull qwen2.5-coder:7b

# Check disk space
Get-PSDrive C | Select-Object Used,Free
```

## Verification Checklist

After installation, verify:

- [ ] `ollama --version` works
- [ ] `ollama list` shows qwen2.5-coder:7b
- [ ] HTTP connection to localhost:11434 works
- [ ] Enhancer Agent stages populate (not "unknown")
- [ ] Can run test enhancement command

## Next Steps

Once Ollama is installed and model is pulled:

1. **Test Enhancer Agent:**
   ```powershell
   python -m tapps_agents.cli enhancer enhance-quick "Add full end to end testing to Tapps CodingAgents prompt enhancements"
   ```

2. **Expected Output:**
   - ✅ Intent: [specific intent, not "unknown"]
   - ✅ Scope: [specific scope]
   - ✅ Requirements: [list of requirements]
   - ✅ Architecture: [guidance]
   - ✅ Expert consultations: [domain expert input]

3. **Create config.yaml** (optional but recommended):
   ```yaml
   # .tapps-agents/config.yaml
   mal:
     ollama_url: "http://localhost:11434"
     default_model: "qwen2.5-coder:7b"
   ```

## Quick Install Command (If You Have winget)

```powershell
# Install Ollama
winget install Ollama.Ollama

# Pull model
ollama pull qwen2.5-coder:7b

# Verify
ollama list
```

## Notes

- Ollama runs as a background service on Windows
- Models are stored in: `%USERPROFILE%\.ollama\models\`
- First model download takes longest
- Subsequent models download faster (shared layers)

---

**After installation, run the verification steps above to confirm everything works!**

