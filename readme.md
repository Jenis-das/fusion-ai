# Fusion 🚀

Fusion is an advanced, high-performance **Multi-LLM Aggregator and Voting System** built with Python, Django, and Asynchronous Asyncio/HTTPX. 

The platform allows users to send a single prompt to multiple AI providers simultaneously (Workers), aggregate their outputs, and pass the combined results to a dedicated evaluator model (Judge) to determine or generate the best final response.

## 🌟 Features

- **Concurrent Multi-Model Execution**: Hits multiple upstream API endpoints (Gemini, Groq, Mistral, Cerebras, OpenRouter, SambaNova) concurrently using Python's `asyncio`.
- **Intelligent Judge Routing**: Automatically routes worker responses along with user history to a designated "Judge" model for evaluation.
- **Robust Multi-Provider Error Parsing**: A unified error-handling layer that parses completely different error JSON shapes across 6+ AI providers, elegantly identifying and standardizing rate limits ($429\text{ Too Many Requests}$) or quota-exhaustion states.
- **Resilient Fault Tolerance**: Uses asynchronous exception gathering; if one provider fails or times out, the platform continues processing the remaining operational models without breaking the user experience.
- **Secure Token Authentication**: Built on top of Django and Django REST Framework SimpleJWT, handling user sessions securely via HTTP-Only Access and Refresh JWT Cookies.

---

## 🛠️ Tech Stack

- **Backend Framework:** Django, Django REST Framework (DRF)
- **Async Networking:** `httpx`, `asyncio`
- **Authentication:** DRF SimpleJWT (Cookie-based session state)
- **Supported AI Providers:**
  - Google Gemini
  - Groq (Llama-3, etc.)
  - OpenRouter
  - Mistral AI
  - Cerebras Systems
  - SambaNova Systems

---

## 🚀 Architecture Workflow

1. **User Request**: The user submits a prompt via the dashboard.
2. **Worker Selection**: The system looks up configured worker models and triggers asynchronous HTTP requests in parallel.
3. **Consensus Aggregation**: Once workers reply, the system stitches their outputs into a uniform layout.
4. **The Verdict (Judge)**: The aggregated answers, original question, and instructions are passed to the designated "Judge" model to render the final response.

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/jenis-das/fusion.git](https://github.com/jenis-das/fusion.git)
cd fusion
```

### 2. Set Up a Virtual Environment
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```


### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Database Migrations
```
python manage.py makemigrations
python manage.py migrate
```

### 5. Run the Server
```
python manage.py runserver
```