# 🤖 HR GPT Local Chatbot

Local chatbot project built with Python, MySQL, and Ollama.

It supports two different chat modes in one UI:

- 🏢 `HR Database` mode for local employee database search
- 💬 `Regular Chat` mode for normal chatbot-style questions

---

## ✨ Features

- 🔍 Ask HR-related questions and fetch data from local MySQL
- 💬 Switch to regular chatbot mode for non-database questions
- 🧠 Uses local Ollama model: `phi3:latest`
- 🛡️ Only safe `SELECT` queries are allowed in HR mode
- ❓ If the HR query is unclear, chatbot asks a related follow-up question
- 📜 Separate chat history view for `HR Database` and `Regular Chat`
- 🔐 Password-protected log viewer inside the frontend
- 🗂️ Separate log files for HR and Regular chat
- 📅 Handles `date` and `datetime` values safely in API responses
- 📱 Auto-scrolls to the latest message

---

## 📷 Screenshots

### HR Database

![HR Database](assets/Screenshot%20-%20HR%20Database.png)

### Regular Chat

![Regular Chat](assets/Screenshot%20-%20Regular%20Chat.png)

### Logs Viewer

![Logs Viewer](assets/Screenshot%20-%20Logs.png)

---

## 🧰 Tech Stack

- `Python`
- `MySQL`
- `Ollama`
- `HTML + Bootstrap`
- Built-in Python server using `ThreadingHTTPServer`

---

## 📁 Project Files

- `app.py` : backend server and chatbot logic
- `templates/index.html` : frontend UI
- `hr-chat.jsonl` : HR chat logs
- `regular-chat.jsonl` : Regular chat logs
- `log.txt` : combined JSON line log
- `requirements.txt` : Python dependencies

---

## ⚙️ Requirements

Before running the project, make sure you have:

- ✅ Python installed
- ✅ MySQL running locally
- ✅ Ollama installed and running
- ✅ Ollama model pulled locally:

```powershell
ollama pull phi3:latest
```

---

## 🗄️ Database Setup

The app connects to this MySQL database config from `app.py`:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "hr_management",
}
```

Make sure:

- the database `hr_management` exists
- the required HR tables exist
- MySQL username/password match your local setup

---

## 📦 Installation

Install Python packages:

```powershell
pip install -r requirements.txt
```

If `pip` is not available directly, use:

```powershell
python -m pip install -r requirements.txt
```

---

## ▶️ Run The App

Run the backend:

```powershell
python app.py
```

If your machine uses a specific Python path, run it like this:

```powershell
& "C:\Users\mahes\AppData\Local\Programs\Python\Python314\python.exe" app.py
```

Open in browser:

```text
http://127.0.0.1:8000
```

---

## 🧭 How To Use

### 🏢 HR Database Mode

Use this tab for employee/database-related questions.

Examples:

- `total employees`
- `inactive employee`
- `show employee name and email`
- `employees in IT`
- `active employees`

What it does:

- tries smart query handling first
- if needed, sends schema + question to Ollama to generate SQL
- allows only safe `SELECT` queries
- shows results in table format

### 💬 Regular Chat Mode

Use this tab for general questions that are not related to the HR database.

Examples:

- `Explain leave policy draft`
- `Write a short mail to HR`
- `Summarize this message`
- `Give me interview questions for Python`

What it does:

- sends the prompt directly to Ollama
- does not show SQL/debug output in the UI
- keeps chat history separate from HR mode

---

## 🔁 Chat Mode Switching

The frontend has two buttons:

- `HR Database`
- `Regular Chat`

Behavior:

- switching tabs changes the active mode
- each mode keeps its own visible conversation
- HR chats do not appear inside Regular Chat view
- Regular Chat messages do not appear inside HR view

---

## 📜 Logs

The app stores logs in JSON Lines format.

### Log Files

- `hr-chat.jsonl` : only HR database conversations
- `regular-chat.jsonl` : only regular chatbot conversations
- `log.txt` : combined log entries in JSON line format

### Log Entry Format

Example:

```json
{"timestamp":"2026-04-10T12:07:37","mode":"hr","question":"total employee","answer":"Total employees: 11","debug":{"query":"total employee","sql":"SELECT COUNT(*) AS total_employees FROM employees"}}
```

Each entry may contain:

- `timestamp`
- `mode`
- `question`
- `answer`
- `debug`

---

## 🔐 Logs Viewer

The UI includes a `View Logs` button.

Features:

- asks for password before showing logs
- reads logs from:
  - `hr-chat.jsonl`
  - `regular-chat.jsonl`
- merges and shows them in one list
- labels each entry as `HR Database` or `Regular Chat`
- shows HR table responses in a readable preview format

### Default Password

```text
1234
```

Password is currently hardcoded in `app.py`:

```python
LOG_VIEW_PASSWORD = "1234"
```

---

## 🛡️ Safety Rules In HR Mode

- only `SELECT` queries are allowed
- dangerous SQL like `DELETE`, `DROP`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE` is blocked
- multi-statement SQL is rejected
- query limit is enforced with `LIMIT 50`

---

## 🧠 Ollama Behavior

### In HR Mode

- Ollama is used to help generate SQL when rule-based matching is not enough
- if the request is unclear or Ollama is unavailable, the bot asks a related clarification question

### In Regular Chat Mode

- Ollama is used like a normal local chatbot
- no SQL is generated or shown in the UI

---

## 🎨 Frontend Behavior

- separate mode buttons for HR and Regular chat
- auto-scroll to newest response
- table output stays inside chat width
- debug panel shown only for HR mode
- logs panel with password protection

---

## 🚨 Troubleshooting

### `Ollama request failed` or chat service unavailable

Check:

- Ollama is installed
- Ollama app/service is running
- model `phi3:latest` is available
- Ollama is reachable at:

```text
http://localhost:11434
```

### `Database connection failed`

Check:

- MySQL server is running
- database name is correct
- username/password in `DB_CONFIG` are correct

### `Object of type date is not JSON serializable`

This issue has already been handled in the backend by converting date values to ISO strings.

### UI changes not visible

If you updated code but do not see changes:

- stop the running server
- start `app.py` again
- refresh the browser

---

## 🔮 Possible Improvements

- move passwords and config to `.env`
- add login/logout for logs view
- add export logs to CSV/JSON
- add filters in logs view by mode/date
- improve regular chat prompts
- add database schema docs

---

## ✅ Summary

This project is a local dual-mode chatbot:

- 🏢 HR mode for MySQL database search
- 💬 Regular mode for chatbot questions
- 📜 JSON-based logging
- 🔐 protected logs viewer
- 🤖 powered by local Ollama