# 🏥 NL2SQL Clinic Assistant

An AI-powered **Natural Language to SQL (NL2SQL)** system built using **Vanna AI 2.0**, **FastAPI**, **SQLite**, and **Streamlit**.

This application allows users to ask questions in plain English and retrieve structured data insights without writing SQL.

---

## 🚀 Live Demo

* 🌐 **Streamlit App:**
  https://prashantgupta77-nl2sql-clinic-assistant-app-rb7pf6.streamlit.app/

* ⚡ **FastAPI Docs:**
  https://nl2sql-clinic-assistant-fastapi.onrender.com/docs

* 📡 **Health Check:**
  https://nl2sql-clinic-assistant-fastapi.onrender.com/health

---

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://prashantgupta77-nl2sql-clinic-assistant-app-rb7pf6.streamlit.app/)

---

## 🚀 Key Features

* Natural Language → SQL conversion using AI
* Multi-table joins, aggregations, and filters
* Safe SQL execution (SELECT-only validation)
* Structured API responses (JSON + tables)
* Automatic chart generation using Plotly
* Interactive Streamlit dashboard
* Query caching and performance optimization
* Benchmark system with 20/20 queries passing

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

## 📁 Project Structure

```text
project/
│
├── setup_database.py       # Create SQLite database + generate dummy clinic data
├── seed_memory.py          # Seed Vanna agent with verified NL → SQL examples
├── vanna_setup.py          # Initialize Vanna agent, tools, and memory
├── main.py                 # FastAPI backend (API endpoints, SQL execution)
├── app.py                  # Streamlit UI (dashboard + user interaction)
├── run_benchmark.py        # Automated benchmark runner (20 test queries)
│
├── clinic.db               # SQLite database file (pre-generated data)
├── seed_data.json          # Stored training examples for agent memory
│
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── RESULTS.md              # Benchmark output report (auto-generated)
└── benchmark_results.json  # Raw benchmark results (JSON format)
```

---

## ⚙️ Run Locally

### 1️⃣ Clone Repository

```bash
git clone https://github.com/PrashantGupta77/nl2sql-clinic-assistant.git
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
streamlit run app.py
```

---

## 📡 API Endpoints

### POST `/chat`

```json
{
  "question": "Which doctor earns the most revenue?"
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

* All assignment queries handled successfully
* Deterministic responses using seeded SQL mapping

---

## 🔐 Security

* Only `SELECT` queries allowed
* Dangerous SQL blocked:

  * INSERT, UPDATE, DELETE
  * DROP, ALTER, TRUNCATE
* Input validation enforced
* Basic rate limiting enabled

---

## 🚀 Deployment

| Component       | Platform        |
| --------------- | --------------- |
| FastAPI Backend | Render          |
| Streamlit UI    | Streamlit Cloud |
| Database        | SQLite          |

---

## ⚠️ Known Limitations

* Cache is in-memory (not persistent)
* Rate limiting is basic
* LLM may occasionally generate imperfect SQL for unseen queries

---

## 🔮 Future Improvements

* Redis caching
* Authentication system
* Multi-user support
* Advanced SQL correction loop
* PostgreSQL / cloud database support

---

## 👨‍💻 Author

**Prashant Gupta**

---

## 🎯 Conclusion

This project demonstrates:

* End-to-end NL2SQL system design
* LLM-powered backend architecture
* Secure and controlled SQL execution
* Real-world dataset simulation
* Benchmark-driven validation

---

⭐ If you found this useful, consider giving it a star!
