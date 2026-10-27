# Windows 11 setup — Sentinel v2

This guide uses your installed XAMPP/MySQL and a free local Ollama model. The earlier `python -m http.server` command is for legacy v1 only.

## 1. Install/check prerequisites

Use vendor installers for Git, Node.js 22 LTS, Python 3.11–3.13 and Ollama. Restart VS Code after installation so its terminal sees new PATH entries.

```powershell
git --version
node --version
npm --version
py --version
ollama --version
```

If PowerShell blocks `npm.ps1`, use `npm.cmd` in the same commands, or choose **Command Prompt** in VS Code. You do not need to change system execution policy. All backend commands below call the virtual environment's Python directly, so activation is unnecessary.

## 2. Get the project

```powershell
git clone https://github.com/asrith1999/sentinel-security-assistant.git
cd sentinel-security-assistant
code .
```

If you already cloned the repository, save/commit your edits and use `git pull --ff-only` inside it. Do not clone into an existing project folder.

## 3. Create the MySQL database

1. Open XAMPP Control Panel.
2. Start **MySQL**. Start Apache only if you want to use phpMyAdmin.
3. Click MySQL **Admin**, or open http://localhost/phpmyadmin.
4. Open `database/setup.sql` in VS Code.
5. Replace `CHANGE_ME` with a strong local password. Avoid quotes/backslashes when first configuring, or escape them correctly in SQL.
6. Paste the SQL into phpMyAdmin's **SQL** tab and run it as the database administrator.

The script creates:

- Database: `sentinel_security`
- Account: `sentinel_user` with host `127.0.0.1`
- Permissions limited to this project's database

Do not change XAMPP's root password or use the root account for the app. If the dedicated account already exists, CREATE USER IF NOT EXISTS does not change its password. Use the account's existing credentials or change that dedicated account through phpMyAdmin.

## 4. Configure and start the backend

In VS Code terminal 1, from the project root:

```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and edit this line to match your dedicated user's password:

```dotenv
DATABASE_URL=mysql+pymysql://sentinel_user:YOUR_PASSWORD@127.0.0.1:3306/sentinel_security?charset=utf8mb4
```

Replace YOUR_PASSWORD; do not include angle brackets. If the password contains URL characters such as `@`, `:`, `/`, `#`, `%` or `?`, URL-encode the **password part only**. For example, `@` becomes `%40`. You can obtain the encoded value locally without echoing the original password:

```powershell
.venv\Scripts\python -c "from getpass import getpass; from urllib.parse import quote; print(quote(getpass('Database password: '), safe=''))"
```

Keep the same host (`127.0.0.1`) and match your MySQL port (normally 3306). Never commit or share `.env`.

Start FastAPI:

```powershell
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs to see the actual backend API. The backend creates its tables automatically if database credentials and privileges are correct. If initial setup fails, correct `.env`, ensure MySQL is running, then restart this terminal's server.

## 5. Start the frontend

Open a **new terminal** at the project root:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Keep both terminals running. Vite proxies `/api` requests to FastAPI on port 8000.

## 6. Start free AI

Install and open Ollama from https://ollama.com/download. Then run:

```powershell
ollama pull qwen2.5:3b
ollama list
```

The 3B model is the initial, modest-size choice. First inference may be slow while the model loads. Your 16 GB RAM laptop can try it; GPU offload depends on drivers/VRAM, and CPU fallback is possible. Tamil output may need correction. You can choose another model by pulling it and changing `OLLAMA_MODEL` in `.env`, then restarting FastAPI. Model licenses apply separately.

Ollama's installed Windows app normally runs a local API on port 11434. If it is not running, use `ollama serve`. If that command says the address is already in use, Ollama may already be running; check rather than starting a second copy:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Do not set Ollama to a public address. No API key is needed.

## 7. Use the app

1. Choose **Create account** and enter your name, email identifier and a password of 10–128 characters. No email is sent.
2. Click **தமிழ்** for Tamil. Choose **English** to switch back.
3. In **Setup & health**, check backend, database and local model readiness.
4. Go to **Log analysis**, load the sample and analyze/save it.
5. Expect 8 lines and 4 findings. These are hypotheses, not confirmation of compromise.
6. Generate a local AI explanation. AI being offline does not prevent rule analysis or saved cases.
7. In **AI assistant**, attach the selected case if you want it included in the question.
8. Export a report. For PDF, open a selected case and use **Print / Save PDF**.
9. Open **Investigations** to view previous work. Accounts only see their own cases.

## Example files

| File | Expected result |
| --- | --- |
| examples/suspicious-login.log | 8 lines / 4 findings / high |
| examples/firewall.log | 2 lines / 1 finding / medium |
| examples/normal-activity.log | 2 lines / 0 findings / unclassified |
| examples/auth-events.json | 6 events / 2 findings / high |

Use **Upload text logs** to load a file. Uploads are UTF-8 and at most 200 KB. The pasted text field permits 200,000 characters. The file is read in the browser, then its text is sent to your local backend when you choose Analyze & save.

## Common problems

| Problem | Fix |
| --- | --- |
| `py` not recognized | Install Python and reopen VS Code; if `python --version` works, use `python` instead of `py -3`. |
| `npm` not recognized | Install Node.js and restart VS Code. |
| PowerShell blocks `npm.ps1` | Use `npm.cmd ci` and `npm.cmd run dev`, or a Command Prompt terminal. |
| Database unavailable / Access denied | Start MySQL, check the dedicated account/host, password encoding, port and `.env`; restart FastAPI. |
| Unknown database | Run database/setup.sql as a database administrator. |
| Backend unavailable | Keep FastAPI running on 127.0.0.1:8000; check its terminal. |
| Port 8000 is occupied | Stop the other service, or change FastAPI's port AND both proxy targets in frontend/vite.config.js. |
| Port 5173 is occupied | Stop the other service; if deliberately changing it, update frontend origins in backend/.env too. |
| Model unavailable | Start Ollama, run `ollama list`, and confirm its exact model name matches `.env`. |
| AI timeout | Wait for model loading, shorten the question, or try a smaller model. Increase OLLAMA_TIMEOUT if appropriate, then restart FastAPI. |
| No patterns matched | The rules did not recognize the text. This does not prove safety. Use supported sample logs first. |
| Session expired | Sign in again; sessions last 12 hours by default. |
| Too many login attempts | Wait one minute before retrying. |

## Restart next time

1. Start MySQL in XAMPP.
2. Start Ollama.
3. Double-click `start-windows.bat`, or use the two server commands manually.
4. Open http://127.0.0.1:5173 once Vite reports ready.

For a clean stop, press Ctrl+C in each server terminal. MySQL stores the investigations across restarts. The browser tab's session token is removed when that tab closes; sign in again if needed.
