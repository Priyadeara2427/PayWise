# 💰 PayWise – Smart Cash Flow & Decision Intelligence System

## 📌 Problem Statement (Track 3: Fintech)

Small businesses often rely only on their **current bank balance** without visibility into:

* Upcoming obligations
* Payment timelines
* Trade-offs between decisions

This leads to:

* ❌ Cash shortfalls
* ❌ Delayed payments
* ❌ Poor financial decisions

### 🎯 Our Solution: PayWise

**PayWise** is a semi-autonomous financial intelligence system that:

* Models short-term financial state
* Detects liquidity risks
* Suggests optimal financial actions with reasoning

---

# 🚀 System Capabilities

## 1. 📥 Multi-Source Financial State Modeling

* Inputs:

  * Bank statements (CSV)
  * Digital invoices (PDF)
  * Images (OCR)
* Output:

```json
{
  "cash_balance": 20000,
  "payables": [...],
  "receivables": [...]
}
```

---

## 2. ⚠️ Constraint & Runway Detection

* Detects:

  * Cash shortfall scenarios
* Computes:

  * 📉 Days to zero (solvency countdown)
* Helps answer:
  👉 “How long can I survive with current cash?”

---

## 3. 🧠 Predictive Decision Engine

Each obligation is evaluated based on:

* Urgency (due date)
* Risk / penalty
* Flexibility

### Output:

* Prioritized obligations
* Suggested actions:

  * Pay now
  * Delay
  * Partial payment

---

## 4. ✉️ Context-Aware Action Preparation (Groq API)

* Generates:

  * Negotiation emails
  * Payment plans
* Tone adapts based on:

  * Vendor vs Customer
  * Risk level

---

## 5. 🔍 Explainability (COT Reasoning)

* Human-readable explanations:

  * Why one payment is prioritized over another
  * Trade-off reasoning

---

# 🏗️ Full Tech Stack

## 🧠 Backend

* Python
* FastAPI

## 📊 Data Processing

* Pandas
* NumPy
* Regex + datetime

## 📄 OCR

* pytesseract
* pdf2image

## 🤖 AI Layer

* **Groq API (LLM)**

  * Email drafting
  * Explanation generation

## 🎨 Frontend

* React.js
* Tailwind CSS
* Axios

---

# 🖥️ Frontend (React) – Complete Design

## 🎯 Goal

Make the system **usable for non-technical users** with clear, actionable insights.

---

## 📱 Pages & Components

### 1. 🔐 Authentication Page

* Login / Signup
* Simple UI
* JWT-based auth

---

### 2. 📊 Dashboard (Main Page)

Shows:

* 💰 Current Cash Balance
* ⚠️ Risk Level (LOW / MEDIUM / HIGH)
* ⏳ Days to Zero
* 📈 Cash Timeline Graph

### Components:

* `SummaryCard`
* `RiskIndicator`
* `TimelineChart`

---

### 3. 📂 Upload & Data Ingestion Page

* Upload:

  * CSV
  * PDF
  * Images
* Drag & Drop UI
* Shows:

  * Extracted records preview

---

### 4. 📋 Obligations Page

Displays:

* Payables
* Receivables

### Features:

* Sorting by:

  * Due date
  * Risk score
* Highlight:

  * Overdue payments

---

### 5. 🧠 Decision Engine Page

Shows:

* Priority list of payments
* Suggested actions:

  * Pay
  * Delay
  * Negotiate

### Includes:

* Reasoning (COT explanation)

---

### 6. ✉️ Smart Actions Page

* Generated outputs:

  * Negotiation emails
  * Payment plans

Example:

```text
Subject: Request for Payment Extension

Dear ABC Enterprises,
Due to temporary cash flow constraints...
```

---

### 7. 📈 Timeline Visualization Page

* Interactive graph:

  * Cash vs Date
* Shows:

  * When balance goes negative

---

# 🏗️ Frontend Folder Structure

```bash
frontend/
│
├── src/
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── SummaryCard.jsx
│   │   ├── TimelineChart.jsx
│   │   ├── RiskBadge.jsx
│   │
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Upload.jsx
│   │   ├── Obligations.jsx
│   │   ├── Decisions.jsx
│   │   ├── Actions.jsx
│   │
│   ├── api/
│   │   ├── api.js
│   │
│   ├── App.jsx
│   ├── main.jsx
│
├── package.json
```

---

# 🔗 API Integration (Frontend ↔ Backend)

### Example (Axios)

```javascript
import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000"
});

export const getRisk = () => API.get("/risk");
export const uploadFile = (data) => API.post("/upload", data);
```

---

# ⚙️ Setup Instructions

## Backend

```bash
pip install -r requirements.txt
python backend/test.py
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

---

# 🧪 Sample Output

## ⚠️ Risk Report

```json
{
  "risk_level": "HIGH",
  "projected_cash": -94087,
  "days_to_zero": "Immediate Risk"
}
```

---

# 🧠 System Architecture

```text
[Frontend (React)]
        ↓
[FastAPI Backend]
        ↓
[Step 1: Ingestion]
        ↓
[Step 2: Processing]
        ↓
[Step 3: Risk Engine]
        ↓
[Groq API (AI Outputs)]
```

---

# 🔮 Future Enhancements

* 🔔 Real-time alerts
* 📱 Mobile app
* ☁️ Cloud deployment
* 🤖 ML risk prediction

---

# 👩‍💻 Author

**Priya Verma**
PayWise – Fintech Decision Intelligence System

---

# 📜 License

Academic / Hackathon Use Only

---

## ⭐ Final Note

PayWise transforms:
👉 **“I have ₹20,000”**
into
👉 **“I can survive 3 days, delay vendor X, pay vendor Y, and send this email.”**
