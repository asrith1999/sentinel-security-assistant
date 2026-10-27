# API reference

Base URL: `http://127.0.0.1:8000/api`. Interactive schema: `/docs`.

Except for health/register/login, supply `Authorization: Bearer <session token>`.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | /health | Backend, database and local model readiness |
| POST | /auth/register | Create account: name, email, password |
| POST | /auth/login | Obtain session: email, password |
| GET | /auth/me | Current account |
| POST | /auth/logout | Revoke this session |
| POST | /investigations | Save and analyze: title, source, logs |
| GET | /investigations | Latest 200 owned cases |
| GET | /investigations/{id} | Owned case with evidence/findings/AI summary |
| PATCH | /investigations/{id} | Change status: open, investigating, resolved |
| POST | /investigations/{id}/explain | Generate/persist local AI commentary: language en or ta |
| GET | /investigations/{id}/report?language=ta | Download text report |
| POST | /chat | question, conversation_id UUID, language, optional investigation_id UUID |
| GET | /chat/{conversation_id} | First 100 turns owned by current account |

Errors include 401 (sign-in/expiry), 404 (missing or not owned), 409 (duplicate email), 413 (body limit), 422 (invalid input), 429 (auth throttle), 503 (database/model unavailable), 504 (AI timeout). Never send a session token to an external host. All service addresses are configured on the server, not accepted from log input or chat requests.
