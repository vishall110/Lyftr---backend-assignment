
# Lyftr AI – Backend Assignment

**Containerized Webhook API (FastAPI)**

---

## 📌 Overview

This project is a simple backend service built using **Python + FastAPI**.
It receives WhatsApp-like messages via a secure webhook, stores them in **SQLite**, and exposes APIs for listing messages, analytics, health checks, and metrics.

The service is designed to be:

* Secure (HMAC signature verification)
* Idempotent (same message is stored only once)
* Observable (logs + metrics)
* Easy to run locally

---

## ⚙️ Tech Stack

* **Python**
* **FastAPI**
* **SQLite**
* **Uvicorn**
* **Pydantic**
* **Prometheus-style metrics**

---

## 📁 Project Structure

```
lyftr-backend/
│
├── main.py        # Complete FastAPI application
├── README.md      # Project documentation
```

> Note: For simplicity, the entire solution is implemented in a single file (`main.py`).

---

## 🚀 How to Run (Local Setup)

### 1️⃣ Prerequisites

* Python 3.10+
* VS Code (or any editor)

---

### 2️⃣ Install Dependencies

Open terminal in the project folder and run:

```bash
pip install fastapi uvicorn
```

---

### 3️⃣ Set Environment Variable (IMPORTANT)

#### Windows (PowerShell)

```powershell
$env:WEBHOOK_SECRET="testsecret"
```

#### Mac / Linux

```bash
export WEBHOOK_SECRET="testsecret"
```

---

### 4️⃣ Start the Server

```bash
uvicorn main:app --reload
```

Server will start at:

```
http://127.0.0.1:8000
```

---

## 🔗 API Endpoints

### ✅ Health Checks

| Endpoint            | Description                       |
| ------------------- | --------------------------------- |
| `GET /health/live`  | App is running                    |
| `GET /health/ready` | App ready (DB + secret available) |

---

### 🔐 Webhook Ingestion

**POST `/webhook`**

* Verifies HMAC-SHA256 signature
* Stores message only once (idempotent)

**Headers**

```
Content-Type: application/json
X-Signature: <HMAC_SHA256>
```

**Request Body**

```json
{
  "message_id": "m1",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Hello"
}
```

**Success Response**

```json
{"status":"ok"}
```

---

### 📬 List Messages

**GET `/messages`**

Supports:

* Pagination (`limit`, `offset`)
* Filtering (`from`, `since`, `q`)

Example:

```
/messages?limit=2&offset=0
```

---

### 📊 Stats

**GET `/stats`**

Returns:

* Total messages
* Unique senders
* Messages per sender
* First & last message timestamps

---

### 📈 Metrics

**GET `/metrics`**

Prometheus-style metrics:

* HTTP request counts
* Webhook result counters

---

## 📝 Logging

* Structured **JSON logs**
* One log per request
* Includes:

  * timestamp
  * request_id
  * path
  * status
  * latency
  * webhook result & duplication flag

---

## 🧠 Design Decisions

### HMAC Verification

* Raw request body is used to compute signature
* Compared against `X-Signature` header
* Invalid signature → `401 Unauthorized`

---

### Idempotency

* `message_id` is primary key in SQLite
* Duplicate inserts are ignored gracefully
* Response remains `200 OK`

---

### Pagination

* `limit` and `offset` supported
* `total` count always reflects full dataset (ignoring pagination)

---

### Stats

* Aggregated using SQL queries
* Efficient for thousands of rows

---

## 🧪 Testing

Manual testing can be done using:

* Browser
* `curl`
* Postman

---

## 🔐 Environment Variables

| Variable         | Description                         |
| ---------------- | ----------------------------------- |
| `WEBHOOK_SECRET` | Secret key for HMAC validation      |
| `DATABASE_URL`   | SQLite database path (default used) |

---

## 🧰 Setup Used

* VS Code
* Python
* Occasional ChatGPT assistance

---

## ✅ Status

✔ All assignment requirements implemented
✔ Ready for evaluation & submission

---

### 📤 Submission

This project can be uploaded to GitHub and shared as required.

---
