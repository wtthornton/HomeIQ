# List Home Assistant Assist Agents

This script queries your Home Assistant instance to list all configured Assist agents and their pipeline IDs.

## Usage

### Option 1: Run with environment variables (PowerShell)

```powershell
cd services/ai-automation-service
$env:HA_URL='http://192.168.1.86:8123'
$env:HA_TOKEN='your_token_here'
python list_agents.py
```

### Option 2: Run with environment variables (Bash/Linux)

```bash
cd services/ai-automation-service
export HA_URL='http://192.168.1.86:8123'
export HA_TOKEN='your_token_here'
python list_agents.py
```

### Option 3: Create a local .env file

Create `services/ai-automation-service/.env`:

```bash
HA_URL=http://192.168.1.86:8123
HA_TOKEN=your_token_here
```

Then run:
```bash
python list_agents.py
```

## Getting Your HA Token

1. Open Home Assistant UI
2. Go to your profile (click your avatar in the bottom left)
3. Scroll down to **Long-Lived Access Tokens**
4. Click **Create Token**
5. Give it a name (e.g., "Agent Lister")
6. Copy the token

## Output

The script will show:
- List of all configured Assist agents
- Agent IDs
- Pipeline IDs (needed for API calls)
- JSON output for programmatic use
- Usage examples

## Example Output

```
✅ Found 2 agent(s):

1. HomeIQ
   ID: conversation.homeiq
   Type: conversation
   Pipeline ID: abc123...

2. Default Assistant
   ID: conversation.default
   Type: conversation
   Pipeline ID: xyz789...

================================================================================
SUMMARY
================================================================================
#   Agent Name                    Agent ID                            Pipeline ID
--------------------------------------------------------------------------------
1   HomeIQ                        conversation.homeiq                  abc123...
2   Default Assistant             conversation.default                 xyz789...
```

## Using the Pipeline ID in API Calls

Once you have the pipeline ID, use it in the `pipeline` parameter:

```python
import aiohttp

async def call_assistant(pipeline_id, text):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://192.168.1.86:8123/api/conversation/process",
            headers={"Authorization": "Bearer YOUR_TOKEN"},
            json={
                "text": text,
                "language": "en",
                "pipeline": pipeline_id
            }
        ) as response:
            return await response.json()
```

## Troubleshooting

### "API endpoint /api/conversation/agents not available (404)"
- Ensure your Home Assistant version is 2023.11 or later
- Verify the Assist integration is installed and configured
- Check that you have assistants created in Settings → Voice Assistants (Assist)

### "Error connecting to Home Assistant"
- Verify HA_URL is correct (use HTTP URL, not WebSocket)
- Verify HA_TOKEN is valid and not expired
- Check that Home Assistant is accessible from your machine
- Verify the token has proper permissions







