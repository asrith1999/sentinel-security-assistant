# Validation and acceptance checks

## Completed during implementation

- Vite production build succeeds.
- 11 backend tests pass with an isolated SQLite database.
- Authentication: salted password hashes, hashed session tokens, valid/invalid login, duplicate account validation, logout and expiry.
- Authorization: another user cannot list/read/edit/explain/export a case or access its chat context.
- Input boundaries: authentication required, blank/oversized input rejected, 1 MB request limit, Host/Origin checks, auth throttling.
- Detection: same-account/source timed correlation; unrelated-account and stale success guards; unclassified result; structured JSON and Tamil findings.
- Local AI HTTP integration: mocked successful response and Tamil system prompt, saved commentary/chat, missing model, offline server and timeout behavior.
- Sample fixtures match documented counts.

## Not verified in the implementation environment

MySQL/MariaDB and Ollama were not installed. Automated tests used SQLite and mocked model responses, not a real database server or generated AI answer. A browser preview was blocked by the environment's port routing, so desktop/mobile visual and interaction acceptance remains to be checked locally. Vite compilation and API tests do not replace these checks.

## Live laptop smoke check

After configuring and starting FastAPI against your actual MySQL/MariaDB database, from the backend folder:

```powershell
.venv\Scripts\python scripts\smoke.py
```

This creates a synthetic local test account/case and verifies the actual database, login session, sample analysis, Tamil export and logout. It leaves those test records in your local database. To also request a real Ollama answer:

```powershell
.venv\Scripts\python scripts\smoke.py --ai
```

Read the AI answer in the app to judge accuracy; a nonempty response alone is not proof of correctness.

## UI acceptance

1. Register and sign in with a local account.
2. Switch English/Tamil on desktop and a narrow browser window.
3. Upload every sample and compare its counts to docs/WINDOWS_SETUP.md.
4. Refresh the page and confirm the case persists; update its status.
5. Ask a question with and without a selected investigation attached.
6. Start a new chat and refresh to check history restoration.
7. Stop Ollama: analysis/save should continue, AI should report an error.
8. Restart Ollama: AI should recover when the model is ready.
9. Download a Tamil report and print a selected case to PDF.
10. Sign out and sign in as another user to confirm case isolation.

## Automated tests

From backend: `python -m pip install -r requirements-dev.txt`, then `python -m pytest tests -q`. Test configuration is temporary and does not read or overwrite your production MySQL data. From frontend: `npm ci`, then `npm run build`.
