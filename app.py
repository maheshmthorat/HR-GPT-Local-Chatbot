from __future__ import annotations

import json
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import mysql.connector
import requests


HOST = "0.0.0.0"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "log.txt"
HR_LOG_FILE = BASE_DIR / "hr-chat.jsonl"
REGULAR_LOG_FILE = BASE_DIR / "regular-chat.jsonl"
INDEX_FILE = BASE_DIR / "templates" / "index.html"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "hr_management",
}

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:latest"
LOG_VIEW_PASSWORD = "1234"


def json_serializer(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def append_json_log(file_path: Path, payload: dict[str, Any]) -> None:
    with file_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload, default=json_serializer) + "\n")


def append_chat_log(mode: str, question: str, answer: Any, debug: dict[str, Any] | None = None) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "question": question,
        "answer": answer,
        "debug": debug or {},
    }
    append_json_log(LOG_FILE, entry)

    if mode == "hr":
        append_json_log(HR_LOG_FILE, entry)
    elif mode == "regular":
        append_json_log(REGULAR_LOG_FILE, entry)


def read_json_log(file_path: Path) -> list[dict[str, Any]]:
    if not file_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8") as log_file:
        for line in log_file:
            line = line.strip()
            if not line:
                continue

            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, dict):
                entries.append(parsed)

    return entries


def get_combined_logs() -> list[dict[str, Any]]:
    entries = read_json_log(HR_LOG_FILE) + read_json_log(REGULAR_LOG_FILE)
    entries.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return entries


def build_clarification_message(message: str) -> str:
    lowered = message.lower()

    if "employee" in lowered:
        return (
            "I didn't fully understand that employee request. "
            "Do you want employee count, employee list, or employee details like name, email, department, or status?"
        )

    if "department" in lowered:
        return (
            "I need a bit more detail about the department request. "
            "Do you want to see department names, employees in a department, or employee count by department?"
        )

    if any(keyword in lowered for keyword in ["status", "active", "inactive"]):
        return (
            "I need a little more detail for the status request. "
            "Do you want active employees, inactive employees, or status for a specific employee?"
        )

    if any(keyword in lowered for keyword in ["email", "phone", "contact"]):
        return (
            "I can help with employee contact details. "
            "Do you want name and email, phone numbers, or contact details for a specific department?"
        )

    return (
        "I didn't fully understand the request. "
        "Try asking about employee count, employee list, department-wise employees, active or inactive employees, or name and email."
    )


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_database_schema(connection) -> str:
    schema_parts: list[str] = []
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")

    for (table_name,) in cursor.fetchall():
        column_cursor = connection.cursor(dictionary=True)
        column_cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        column_names = [row["Field"] for row in column_cursor.fetchall()]
        column_cursor.close()
        schema_parts.append(
            f"Table: {table_name}\nColumns: {', '.join(column_names)}"
        )

    cursor.close()
    return "\n\n".join(schema_parts)


def extract_select_statement(raw_text: str) -> str:
    text = raw_text.replace("```sql", "").replace("```", "").strip()
    upper_text = text.upper()
    start = upper_text.find("SELECT")
    if start == -1:
        return ""

    end = text.find(";", start)
    if end == -1:
        statement = text[start:].strip()
    else:
        statement = text[start : end + 1].strip()

    return statement


def ensure_limit(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    if " limit " not in stripped.lower():
        stripped = f"{stripped} LIMIT 50"
    return stripped


def generate_sql(message: str, schema: str) -> str:
    prompt = f"""
You are an expert SQL generator.

STRICT RULES:
- Output ONLY valid MySQL SELECT query
- No explanation
- No extra text
- Use schema only
- LIMIT 50

Schema:
{schema}

User Query: {message}

SQL:
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    sql = extract_select_statement(data.get("response", ""))
    return ensure_limit(sql) if sql else ""


def generate_regular_chat_response(message: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": message,
        "stream": False,
        "options": {"temperature": 0.7},
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return (data.get("response", "") or "").strip()


def is_safe_query(sql: str) -> bool:
    normalized = sql.strip().lower()
    banned_tokens = [" delete ", " drop ", " update ", " insert ", " alter ", " truncate "]

    if not normalized.startswith("select"):
        return False

    if ";" in normalized.rstrip(";"):
        return False

    return not any(token in f" {normalized} " for token in banned_tokens)


def build_smart_query(message: str) -> str | None:
    lowered = message.lower()

    if "employee" in lowered and ("count" in lowered or "total" in lowered):
        return "SELECT COUNT(*) AS total_employees FROM employees"

    columns: list[str] = []
    if "name" in lowered:
        columns.append("name")
    if "email" in lowered:
        columns.append("email")
    if "phone" in lowered:
        columns.append("phone")
    if "department" in lowered:
        columns.append("department")
    if "status" in lowered:
        columns.append("status")

    if not columns:
        columns = ["id", "name", "email", "department", "status"]

    sql = f"SELECT {', '.join(columns)} FROM employees"
    conditions: list[str] = []

    marker = "in "
    if marker in lowered:
        after_marker = lowered.split(marker, 1)[1].strip()
        department = after_marker.split()[0].strip(",.?!")
        if department.isalpha():
            conditions.append(f"department = '{department.title()}'")

    if "inactive" in lowered:
        conditions.append("status = 'inactive'")
    elif "active" in lowered:
        conditions.append("status = 'active'")

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " LIMIT 50"

    if "employee" in lowered and ("list" in lowered or "show" in lowered):
        return sql

    return None


def run_chat_query(user_message: str) -> dict[str, Any]:
    connection = get_connection()

    try:
        sql = build_smart_query(user_message)
        if not sql:
            schema = get_database_schema(connection)
            try:
                sql = generate_sql(user_message, schema)
            except requests.RequestException:
                return {
                    "type": "text",
                    "data": build_clarification_message(user_message),
                    "debug": {"query": user_message, "sql": "", "reason": "ollama_unavailable"},
                }

        debug = {"query": user_message, "sql": sql}

        if not sql or not is_safe_query(sql):
            return {
                "type": "text",
                "data": build_clarification_message(user_message),
                "debug": {**debug, "reason": "invalid_or_unsafe_query"},
            }

        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return {"type": "text", "data": "No data found", "debug": debug}

        if "count(" in sql.lower():
            first_key = next(iter(rows[0]))
            return {
                "type": "text",
                "data": f"Total employees: {rows[0][first_key]}",
                "debug": debug,
            }

        return {"type": "table", "data": rows, "debug": debug}
    finally:
        connection.close()


def run_regular_chat(user_message: str) -> dict[str, Any]:
    response_text = generate_regular_chat_response(user_message)
    if not response_text:
        response_text = "I couldn't generate a response right now. Please try again."

    return {
        "type": "text",
        "data": response_text,
        "debug": {"mode": "regular"},
    }


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        html = INDEX_FILE.read_text(encoding="utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self) -> None:
        if self.path not in {"/chat", "/logs"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(raw_body) if raw_body else {}
            if self.path == "/logs":
                password = str(payload.get("password", ""))
                if password != LOG_VIEW_PASSWORD:
                    self._send_json({"type": "text", "data": "Invalid password"}, HTTPStatus.UNAUTHORIZED)
                    return

                self._send_json({"type": "logs", "data": get_combined_logs()}, HTTPStatus.OK)
                return

            user_message = payload.get("message", "").strip()
            mode = payload.get("mode", "hr").strip().lower()
            if not user_message:
                self._send_json({"type": "text", "data": "Message is required"}, HTTPStatus.BAD_REQUEST)
                return

            if mode == "regular":
                result = run_regular_chat(user_message)
            else:
                mode = "hr"
                result = run_chat_query(user_message)

            append_chat_log(mode, user_message, result.get("data"), result.get("debug"))
            self._send_json(result, HTTPStatus.OK)
        except mysql.connector.Error:
            self._send_json({"type": "text", "data": "Database connection failed"}, HTTPStatus.INTERNAL_SERVER_ERROR)
        except requests.RequestException:
            self._send_json({"type": "text", "data": "Chat service is unavailable right now"}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._send_json({"type": "text", "data": f"Server error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus) -> None:
        response = json.dumps(payload, default=json_serializer).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
