# Google OAuth Setup (Gmail API)

One-time setup for the v0.2 ingestion pipeline. Produces an
`oauth_client.json` at `~/.config/politico-pipeline/` that the Gmail client
uses to authorize read-only inbox access.

## Prerequisites

- A Google account that can sign in to https://console.cloud.google.com/
- The Gmail account you want to **read from** — for this project,
  `politicollector@gmail.com` (the dedicated newsletter inbox)
- ~5–10 minutes

## Decision: which account owns the GCP project?

The **project owner** and the **OAuth subject** are independent decisions.
You will sign in as `politicollector@gmail.com` during the consent flow
regardless — that's the inbox being read, so only it can grant that
consent. The choice below only affects who owns/admins the GCP project
itself.

| Choice | Pros | Cons |
| --- | --- | --- |
| Project under `politicollector@gmail.com` (sock-puppet) | No cross-account test-user dance; owner = consenting user. Inbox + credentials + project live together. | If the account is dormant or weakly secured, losing it loses the credentials. Google may add verification friction on first Cloud-project creation. |
| Project under your primary account (e.g. `jacobbenkell@gmail.com`) | Admin lives with your most-secured identity. Survives rotation of the inbox account. | Must add `politicollector@gmail.com` to the consent screen's **Test Users** list, or OAuth fails with `access_denied`. |

**Heuristic**: if the inbox account has 2FA + recovery email set up and
you treat it as long-lived, own the project from it. Otherwise use your
primary.

## Step 1 — Pick or create the project

Open https://console.cloud.google.com/projectselector2 and sign in as
whichever account you chose above.

- **New project**: name it `politico-pipeline` (or anything). Click
  **Create**. Wait for the notification that the project is ready, then
  make sure it's selected in the top-of-page project dropdown.
- **Existing project**: just select it.

## Step 2 — Enable the Gmail API

Go to https://console.cloud.google.com/apis/library/gmail.googleapis.com
and click **ENABLE**. Wait for the page to flip to "API enabled."

## Step 3 — Configure the OAuth consent screen

> Must happen **before** creating the OAuth client.

Go to https://console.cloud.google.com/apis/credentials/consent

1. **User Type**:
   - **External** for personal Gmail accounts (the common case)
   - **Internal** only if both the project owner and the inbox are on
     the same Google Workspace organization
   - Click **Create**.
2. **App information**:
   - App name: `Politico Pipeline` (or anything user-facing)
   - User support email: your address
   - Developer contact information: your address
3. **Scopes screen**: skip — leave empty. The client requests
   `gmail.readonly` at runtime; you don't need to declare it here for an
   app in Testing status.
4. **Test users**: click **+ Add Users** and add
   `politicollector@gmail.com`. **This step is mandatory** — while the
   app is in Testing status (the default), only listed test users can
   complete the OAuth flow. Skipping this produces an opaque
   `access_denied` mid-flow.
5. **Save and continue** through the summary.

## Step 4 — Create the OAuth Client

Go to https://console.cloud.google.com/apis/credentials → click **+
CREATE CREDENTIALS** → **OAuth client ID**.

- **Application type**: **Desktop app** ← critical, see "Why Desktop
  app" below
- Name: `politico-pipeline desktop` (any label)
- Click **Create**.

A modal pops up showing the client ID and secret. Click **DOWNLOAD
JSON**. The file lands in your Downloads folder with a name like
`client_secret_<long-id>.apps.googleusercontent.com.json`.

### Why Desktop app, not Web application?

The pipeline uses
[`InstalledAppFlow.run_local_server(port=0)`](../politico_playbook/ingestion/gmail_client.py)
which starts a temporary HTTP server on a random localhost port to catch
the OAuth redirect (`http://127.0.0.1:<random>/`). Google's "Web
application" client type requires every redirect URI to be
pre-registered, which is incompatible with random ports. The "Desktop
app" type implicitly trusts `http://127.0.0.1` and `http://localhost`
callbacks for any port. Picking "Web application" by mistake is the
single most common failure mode for CLI OAuth setup.

## Step 5 — Place the JSON

Move the downloaded file into the directory the pipeline expects:

```bash
mkdir -p ~/.config/politico-pipeline    # idempotent
mv ~/Downloads/client_secret_*.json ~/.config/politico-pipeline/oauth_client.json
```

Verify shape:

```bash
python3 -c "
import json
data = json.load(open('/Users/$USER/.config/politico-pipeline/oauth_client.json'))
key = next(iter(data))            # 'installed' or 'web'
print(f'Client type: {key} (must be \"installed\")')
print(f'client_id: {data[key][\"client_id\"][:30]}...')
print(f'redirect_uris: {data[key].get(\"redirect_uris\")}')"
```

Expected output:

```
Client type: installed (must be "installed")
client_id: 1234567890-xxxxxxxxxxxxxxxx...
redirect_uris: ['http://localhost']
```

If the top-level key is `web` instead of `installed`, you created the
wrong client type — go back to Step 4 and recreate as Desktop app.

## Step 6 — First run

```bash
python -m politico_playbook.ingestion.runner backfill \
    --newsletter politicoplaybook \
    --limit 25
```

The first run opens a browser tab. The flow:

1. **Choose account**: pick `politicollector@gmail.com` (NOT your
   primary). If it's not listed, click "Use another account" and sign in.
2. **"Google hasn't verified this app"**: click **Advanced** →
   **Go to Politico Pipeline (unsafe)**. This warning is normal for any
   app in Testing status; it goes away once you publish to Production
   (which you don't need to do for personal use).
3. **Grant**: review the `gmail.readonly` scope and click **Continue**.
4. The browser shows "The authentication flow has completed" and you can
   close the tab.

A token is cached at `~/.config/politico-pipeline/token.json`.
Subsequent runs auto-refresh it; no browser needed.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `access_denied` on consent screen | Account not on Test Users list | Step 3.4 — add the inbox address |
| `redirect_uri_mismatch` | Created Web client instead of Desktop | Step 4 — recreate as Desktop app |
| `invalid_client` | `oauth_client.json` malformed or wrong path | Step 5 — verify shape and `GOOGLE_OAUTH_CLIENT_SECRETS` env var |
| Token works once, fails later | `token.json` cached but scopes changed | `rm ~/.config/politico-pipeline/token.json` and re-run |
| `403 insufficientPermissions` | Gmail API not enabled in this project | Step 2 — enable Gmail API for the *currently selected* project |

## Recovery / rotation

- **Revoke access**: https://myaccount.google.com/permissions → find
  "Politico Pipeline" → Remove access. The next CLI run will re-prompt
  for consent.
- **Rotate the OAuth client**: delete the client at
  https://console.cloud.google.com/apis/credentials and re-do Step 4.
  Replace `~/.config/politico-pipeline/oauth_client.json` and delete
  `token.json`.
- **Lose access to the project owner account**: if the project is owned
  by a sock-puppet you've lost, recreate the project under a different
  account and re-do Steps 1–5. The Gmail data itself is unaffected — the
  inbox is read via OAuth consent, not project ownership.
