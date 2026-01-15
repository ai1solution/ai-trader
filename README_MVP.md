# Analytics & Insights MVP

A read-only analytics platform exposing the internal state of algorithmic trading engines (v1-v4).

## Architecture
- **Backend**: FastAPI service (`engine_api/`) managing isolated engine workers.
- **Frontend**: Next.js 14 application (`web_mvp/`) with real-time polling.
- **Engines**:
  - `v1`: Legacy Momentum (Trend/Velocity)
  - `v2`: Modern (Confidence/Signal)
  - `v3`: Strict (State Machine/Regime)
  - `v4`: Capital Aware (Risk/PnL)

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Start Backend
```bash
# Install dependencies (if not already)
pip install fastapi uvicorn ccxt

# Run Server (from root directory)
uvicorn engine_api.main:app --reload
```
Server runs on `http://localhost:8000`.

### 2. Start Frontend
```bash
cd web_mvp_fresh
npm install
npm run dev
```
Frontend runs on `http://localhost:3000`.

## Usage
1. Open `http://localhost:3000`.
2. Enter a symbol (e.g., `BTC/USDT`, `ETH/USDT`).
3. Click "Analyze".
4. View real-time state, price graph, and multi-version insights.

## Developer Notes
- **Concurrency**: v1-v3 run in thread pool executors; v4 runs natively async.
- **State**: In-memory ephemeral storage. Reset on restart.
