# Sentinel Security Assistant

A browser-based IT security portfolio prototype by Asrith. Analyze text logs, review investigation playbooks and export incident report drafts.

**Status:** rules-based prototype. No AI model, backend database, live monitoring or automated response is connected. No API key is required. Logs are processed in the current browser tab and are lost on refresh.

## Run on Windows 11

1. Install Python 3 if needed. Verify in a terminal with `py --version`.
2. Extract this project ZIP, or clone your GitHub repository.
3. Open the project folder in VS Code.
4. In the VS Code terminal run:

```powershell
py -3 -m http.server 8000 --bind 127.0.0.1
```

5. Open http://127.0.0.1:8000 in your browser.
6. Stop the server with Ctrl+C.

Alternatively, double-click `start-windows.bat` and open the same URL. If port 8000 is busy, replace it with 8001. If `py` is unavailable but Python is installed, try `python` in its place.

## macOS / Linux

```bash
sh start-local.sh
```

Open http://127.0.0.1:8000. Python 3 is required.

## Example investigations

Open **Log analysis**, choose **Upload file**, select an example, then click **Analyze logs**.

| Example | Expected result |
| --- | --- |
| `examples/suspicious-login.log` | 8 lines, 4 findings, Needs investigation |
| `examples/firewall.log` | 2 lines, 1 denied/blocked traffic finding |
| `examples/normal-activity.log` | 2 lines, no supported patterns matched |

The built-in **Load sample** button provides the suspicious-login example. Open **Investigation guide** for login, phishing, firewall and malware playbooks. Open **Incident report**, edit the title and download a text report.

No matched patterns does not mean a system is safe. Findings require analyst validation. Authentication success and failure are detected across the submitted text, without account/IP correlation. Sample addresses are reserved documentation addresses.

## Project structure

- `index.html`: complete interface, styles and browser JavaScript
- `examples/`: synthetic log files
- `start-windows.bat`: Windows localhost launcher
- `start-local.sh`: macOS/Linux localhost launcher

No npm install, React, MySQL, Laravel or AI subscription is required for this version. This is the same static prototype as the hosted Site.

## GitHub contribution setup

Create an empty repository called `sentinel-security-assistant` on your GitHub account. Leave README, license and .gitignore initialization unchecked when following these commands. Install Git if needed, then run these from the extracted project folder:

```bash
git init
git add .
git commit -m "Add Sentinel security assistant prototype"
git branch -M main
git remote add origin https://github.com/asrith1999/sentinel-security-assistant.git
git push -u origin main
```

Use the actual URL of your repository if you choose another name. GitHub may ask you to sign in. Never put a password or access token in source files. For an existing nonempty repository, clone it first and copy this project into it before committing; do not force push.

## Future AI integration

A real AI version needs a server endpoint and a server-side API secret. Never embed an API key in this HTML or browser JavaScript. It also needs explicit controls for sending log data to a model provider, error handling, and evidence-based output validation.
