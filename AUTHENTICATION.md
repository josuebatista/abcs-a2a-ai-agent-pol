# Authentication Setup Guide

## Overview

The A2A Agent now requires **Bearer Token authentication** for all API requests. This protects your agent from unauthorized access and controls costs.

## Key Features

- **Multi-Key Support**: Grant access to multiple users/agents with unique keys
- **User Tracking**: Each request is logged with the key owner's name
- **Expiry Dates**: Optional key expiration for temporary access
- **Metadata**: Track when keys were created and add notes
- **Secure Storage**: Keys stored in Google Cloud Secret Manager

## API Key Format

API keys are stored as a JSON object where each key is a token string, and the value contains metadata:

```json
{
  "your-secret-token-here": {
    "name": "User Display Name",
    "created": "2025-10-11",
    "expires": null,
    "notes": "Optional description"
  }
}
```

### Field Descriptions

- **Key (token)**: The actual API key used in Bearer token - should be long, random, and unique
- **name**: Human-readable identifier (shows in logs)
- **created**: ISO date when key was created
- **expires**: ISO date when key expires, or `null` for no expiration
- **notes**: Optional description for your reference

## Generating Secure API Keys

Use one of these methods to generate cryptographically secure keys:

### Option 1: OpenSSL (Recommended)
```bash
# Generate a 32-byte random key (44 characters base64)
openssl rand -base64 32
```

### Option 2: Python
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Option 3: Node.js
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

## Setup Instructions

### Step 1: Create Your API Keys JSON

1. Copy `api-keys-example.json` as a template
2. Replace the example keys with secure random keys (see generation methods above)
3. Update the metadata (name, created, expires, notes)
4. Minify to single line (optional but recommended):

```bash
# Minify JSON
jq -c . api-keys-example.json
```

Example output:
```json
{"key1":{"name":"User1","created":"2025-10-11","expires":null,"notes":"Main"},"key2":{"name":"User2","created":"2025-10-11","expires":"2026-10-11","notes":"Temp"}}
```

### Step 2: Store in Google Cloud Secret Manager

```bash
# Create the secret (first time)
echo -n '{"your-key-here":{"name":"User1","created":"2025-10-11","expires":null}}' | \
  gcloud secrets create api-keys --data-file=-

# Update the secret (if already exists)
echo -n '{"your-key-here":{"name":"User1","created":"2025-10-11","expires":null}}' | \
  gcloud secrets versions add api-keys --data-file=-
```

**CRITICAL**: Use `echo -n` to prevent newline characters!

### Step 3: Grant Service Account Access

```bash
# Get your Cloud Run service account
# Cloud Run uses the default Compute Engine service account with format:
# PROJECT_NUMBER-compute@developer.gserviceaccount.com

# Option 1: Get it directly from your Cloud Run service
SERVICE_ACCOUNT=$(gcloud run services describe a2a-agent \
  --region us-central1 \
  --format="value(spec.template.spec.serviceAccountName)")

# Option 2: If service doesn't exist yet, construct it from project number
# PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
# SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant access to the secret
gcloud secrets add-iam-policy-binding api-keys \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

**Important**: Do NOT use `PROJECT_ID@appspot.gserviceaccount.com` - this is a common mistake. Cloud Run uses the Compute Engine default service account with the format `PROJECT_NUMBER-compute@developer.gserviceaccount.com`.

### Step 4: Deploy with Secret

```bash
gcloud run deploy a2a-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --update-secrets API_KEYS=api-keys:latest,GEMINI_API_KEY=gemini-api-key:latest \
  --memory 512Mi \
  --timeout 300
```

**Note**: Keep `--allow-unauthenticated` flag - authentication is handled by the application code, not Cloud Run.

## Using the API

### Making Authenticated Requests

Include the Bearer token in the `Authorization` header:

```bash
# Get your service URL
SERVICE_URL="https://a2a-agent-298609520814.us-central1.run.app"
API_KEY="your-secret-token-here"

# Test authentication
curl -X POST ${SERVICE_URL}/rpc \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "text.summarize",
    "params": {
      "text": "This is a test message for summarization.",
      "max_length": 20
    },
    "id": "test-001"
  }'
```

### Response Examples

**Success (200)**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "task_id": "test-001",
    "status": "pending"
  },
  "id": "test-001"
}
```

**Invalid Token (401)**:
```json
{
  "detail": "Invalid authentication token"
}
```

**Expired Token (401)**:
```json
{
  "detail": "Token has expired"
}
```

## Managing API Keys

### Adding a New Key

1. Get current secret value:
```bash
gcloud secrets versions access latest --secret=api-keys > current-keys.json
```

2. Edit `current-keys.json` to add new key

3. Update secret:
```bash
cat current-keys.json | gcloud secrets versions add api-keys --data-file=-
```

4. Redeploy (Cloud Run automatically picks up new version):
```bash
gcloud run services update a2a-agent --region us-central1
```

### Revoking a Key

Simply remove it from the JSON and update the secret following the same steps above.

### Rotating Keys

1. Generate new keys
2. Add them to the secret alongside old keys
3. Update clients to use new keys
4. Remove old keys from secret after transition period

## Monitoring

### View Authentication Logs

```bash
# See all authentication events
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 50 | grep "Authenticated request"

# See failed authentication attempts
gcloud run services logs read a2a-agent \
  --region us-central1 \
  --limit 50 | grep "Authentication failed"
```

### Track Usage by Key

Logs show which key (by name) created each task:
```
INFO: ✓ Authenticated request from: Primary User
INFO: Task abc-123 created by 'Primary User' - Method: text.summarize
```

## Security Best Practices

1. **Use Strong Keys**: Generate keys with 32+ bytes of entropy
2. **Rotate Regularly**: Change keys every 90-180 days
3. **Set Expiry Dates**: Use temporary keys for testing/development
4. **Monitor Logs**: Review authentication logs for suspicious activity
5. **Limit Key Distribution**: Only share keys with authorized users/agents
6. **Use HTTPS Only**: Never send keys over unencrypted connections
7. **Store Securely**: Keep key JSON files out of version control

## Troubleshooting

### Issue: "Authentication required" error

**Cause**: API_KEYS not loaded in Cloud Run

**Solution**:
```bash
# Check if secret is mounted
gcloud run services describe a2a-agent --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"

# Verify secret exists
gcloud secrets versions access latest --secret=api-keys
```

### Issue: Keys not working after update

**Cause**: Cloud Run cached old secret version

**Solution**:
```bash
# Force redeploy
gcloud run services update a2a-agent --region us-central1
```

### Issue: "Token has expired" error

**Cause**: Key's expiry date has passed

**Solution**: Remove the expired key and generate a new one, or update the `expires` field to `null` or a future date.

## Migration Guide

If you have an existing deployment without authentication:

1. **Deploy with authentication disabled** (test first):
   - Don't set `API_KEYS` environment variable
   - App will log warnings but remain functional

2. **Test locally** with authentication:
   ```bash
   export API_KEYS='{"test-key":{"name":"Test","created":"2025-10-11","expires":null}}'
   python main.py
   ```

3. **Deploy to production** with API_KEYS secret configured

4. **Update all clients** to include Bearer tokens

5. **Monitor logs** for authentication issues

## Support

For issues or questions:
- GitHub Issues: https://github.com/josuebatista/abcs-a2a-ai-agent-pol/issues
- Documentation: See CLAUDE.md for deployment details
