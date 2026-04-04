# 🏥 NL2SQL Clinic Assistant

An AI-powered **Natural Language to SQL (NL2SQL)** system built using **Vanna AI 2.0**, **FastAPI**, **SQLite**, and **Streamlit**.

This application allows users to ask questions in plain English and retrieve structured data insights without writing SQL.

---

## 🚀 Live Capabilities

* Convert natural language → SQL queries
* Execute queries safely on a database
* Return structured results (table + JSON)
* Generate interactive charts automatically
* Provide SQL transparency for debugging

---

## 🧠 System Architecture

```text
User (Streamlit UI / API Client)
            ↓
        FastAPI Backend
            ↓
     Vanna AI 2.0 Agent
 (LLM + Tools + Memory)
            ↓
      SQL Validation Layer
            ↓
        SQLite Database
            ↓
   Results + Charts (Plotly)
```

---

## 🛠️ Tech Stack

| Technology   | Purpose            |
| ------------ | ------------------ |
| Python 3.10+ | Core language      |
| Vanna 2.0    | NL → SQL Agent     |
| FastAPI      | Backend API        |
| SQLite       | Database           |
| Groq (LLaMA) | LLM Provider       |
| Plotly       | Chart generation   |
| Streamlit    | Frontend dashboard |

---

## ✨ Features

### 🔹 Core Features

* Natural Language → SQL conversion
* Multi-table joins and aggregations
* Automatic SQL execution
* Structured API responses

### 🔹 AI Capabilities

* Vanna Agent with memory
* Few-shot learning using seeded SQL examples
* Deterministic fallback for known queries

### 🔹 Backend Features

* SQL validation (SELECT-only execution)
* Error handling (invalid SQL, empty results)
* Query caching (performance optimization)
* Rate limiting (basic protection)
* Input validation (security)

### 🔹 Visualization

* Automatic chart generation (Plotly)
* Smart visualization selection

### 🔹 UI (Streamlit)

* Clean interactive dashboard
* Query history tracking
* SQL preview panel
* Table + chart display

---

## 📁 Project Structure

```text
project/
│
├── setup_database.py       # Create DB + insert dummy data
├── seed_memory.py          # Seed agent memory
├── vanna_setup.py          # Initialize Vanna agent
├── main.py                 # FastAPI backend
├── app.py        # Streamlit UI
├── run_benchmark.py        # Benchmark runner
│
├── clinic.db               # SQLite database
├── seed_data.json          # Training examples
│
├── requirements.txt
├── README.md
├── RESULTS.md              # Benchmark results
└── benchmark_results.json
```

---

## ⚙️ Run Locally

### 1️⃣ Clone Repository

```bash
git clone https://github.com/<your-username>/nl2sql-clinic-assistant.git
cd nl2sql-clinic-assistant
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Add Environment Variable

Create `.env` file:

```env
GROQ_API_KEY=your_api_key_here
```

---

### 5️⃣ Setup Database

```bash
python setup_database.py
```

---

### 6️⃣ Seed Agent Memory

```bash
python seed_memory.py
```

---

## ▶️ Run Application

### 🔹 Start Backend (FastAPI)

```bash
uvicorn main:app --port 8000
```

Swagger UI:

```
http://127.0.0.1:8000/docs
```

---

### 🔹 Start Frontend (Streamlit)

```bash
streamlit run streamlit_app.py
```

---

## 📡 API Endpoints

### POST `/chat`

```json
{
  "question": "Which doctor earns the most revenue?"
}
```

Response:

```json
{
  "success": true,
  "sql_query": "...",
  "rows": [...],
  "chart": {...}
}
```

---

### GET `/health`

```json
{
  "status": "ok",
  "database": "connected"
}
```

---

## 📊 Benchmark Results

Run:

```bash
python run_benchmark.py
```

### ✅ Result

**20 / 20 Queries Passed**

* All assignment queries handled correctly
* Deterministic responses via seed matching

---

## 🔐 Security

* Only `SELECT` queries allowed
* Dangerous SQL blocked:

  * DROP, DELETE, UPDATE, ALTER
* Input validation enforced
* Basic rate limiting enabled

---

## 🚀 Deployment

### Recommended Setup

| Component       | Platform         |
| --------------- | ---------------- |
| FastAPI Backend | Render / Railway |
| Streamlit UI    | Streamlit Cloud  |
| Database        | SQLite           |

---

## ⚠️ Known Limitations

* Cache is in-memory (not persistent)
* Rate limiting is basic
* LLM may occasionally produce imperfect SQL

---

## 🔮 Future Improvements

* Redis caching
* Authentication system
* Multi-user support
* Better SQL correction loop
* Cloud DB (PostgreSQL)

---

## 👨‍💻 Author

**Prashant Gupta**

---

## 🎯 Conclusion

This project demonstrates:

* End-to-end NL2SQL system design
* LLM integration with backend APIs
* Secure query execution
* Real-world dataset simulation
* Benchmark-driven validation

---

⭐ If you found this useful, consider giving it a star!
