# AI Trader - Cryptocurrency Trading Platform

Professional cross-platform crypto trading system with algorithmic strategies, live charts, backtesting, and advanced analytics.

**Platforms**: Web, iOS, Android  
**Backend**: FastAPI + Python  
**Frontend**: React Native + Expo

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 16+
- npm or yarn

### Installation

#### 1. Clone Repository
```bash
cd ai-trader
```

#### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Or if requirements.txt doesn't exist:
pip install fastapi uvicorn ccxt pandas numpy ta-lib python-dateutil rich
```

#### 3. Frontend Setup
```bash
cd mobile-app
npm install
cd ..
```

---

## 🖥️ Running Locally

### Start Backend API Server
```bash
# From project root (ai-trader/)
python -m api.server

# Server will start on http://localhost:8000
# API docs available at http://localhost:8000/docs
```

**API Endpoints**:
- `GET /v4/status` - Trading engine status
- `POST /v4/start` - Start trading engine
- `POST /v4/stop` - Stop trading engine
- `GET /market/ohlcv` - Get candlestick data
- `GET /market/price/{symbol}` - Get current price
- `POST /analyze/regime` - Analyze market regime
- Full docs: http://localhost:8000/docs

### Start Mobile App
```bash
# From project root
cd mobile-app
npm start

# Or use Expo CLI directly
npx expo start
```

**Access Options**:
- **Web**: Open http://localhost:8082 in your browser
- **Mobile**: Scan QR code with Expo Go app (iOS/Android)
- **iOS Simulator**: Press `i` in terminal
- **Android Emulator**: Press `a` in terminal

---

## 📱 Mobile App Features

### ✅ Implemented
- **Dashboard**: Live P&L tracking, engine controls, auto-refresh (5s)
- **Charts**: Real-time price charts with Victory Native
  - Symbol selector (BTC, ETH, etc.)
  - Timeframe selector (1m, 5m, 15m, 1h, 1d)
  - 24h price change display
- **Backtest**: Configuration interface with date/symbol selection
- **Navigation**: Bottom tab navigation
- **Theme**: Dark crypto-themed UI with neon accents

### 🚧 Coming Soon
- Trade log viewer
- Settings screen
- Push notifications
- Offline support

---

## 🔧 Backend Trading Engines

### V4 Engine (Latest)
Advanced multi-strategy system with:
- **Regime Awareness**: ADX-based market classification
- **Universe Selection**: Dynamic symbol filtering
- **Portfolio Management**: Shared capital allocation
- **Expectancy Protection**: Auto-disable on consecutive losses

**Start V4 Engine**:
```bash
python v4/main.py --mode paper --symbols BTCUSDT ETHUSDT

# Or via API:
curl -X POST http://localhost:8000/v4/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"paper","symbols":["BTC/USDT","ETH/USDT"],"strategies":["momentum"]}'
```

### V3 Engine (Legacy)
```bash
python v3/live_mock.py --symbols FETUSDT WLDUSDT GRTUSDT
```

### V2 Engine (Modern)
```bash
python v2_modern/main.py live
```

### V1 Engine (Legacy)
```bash
python v1_legacy/trading_engine.py
```

---

## 📊 Project Structure

```
ai-trader/
├── api/                    # FastAPI backend
│   ├── server.py          # Main API server
│   ├── routers/           # API endpoints
│   │   ├── v4.py         # V4 engine control
│   │   ├── market.py     # Market data (OHLCV, prices)
│   │   ├── analysis.py   # Regime & universe analysis
│   │   └── legacy.py     # V3 runner
│   └── manager.py        # Runner lifecycle management
│
├── v4/                    # V4 Trading Engine
│   ├── main.py           # CLI entry point
│   ├── engine/           # Core trading logic
│   ├── strategies/       # Strategy implementations
│   ├── data/             # Data providers (CCXT)
│   └── config/           # Configuration
│
├── v3/                    # V3 Trading Engine (Legacy)
│   └── live_mock.py      # Live paper trading
│
├── mobile-app/            # React Native App
│   ├── App.tsx           # Main navigation
│   ├── src/
│   │   ├── screens/      # Dashboard, Charts, Backtest
│   │   ├── components/   # Reusable UI components
│   │   ├── services/     # API clients
│   │   ├── store/        # State management (Zustand)
│   │   └── theme/        # Design system
│   └── package.json
│
├── frontend/              # Web Dashboard (Enhanced HTML/CSS/JS)
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
└── results/               # Trading logs
    └── trades.csv        # Historical trades
```

---

## 🧪 Testing

### Test API Endpoints
```bash
python test_api.py

# Or manually test with curl:
curl http://localhost:8000/
curl http://localhost:8000/v4/status
curl http://localhost:8000/market/price/BTC/USDT
```

### Test Mobile App
1. Start API server: `python -m api.server`
2. Start mobile app: `cd mobile-app && npm start`
3. Open http://localhost:8082 in browser
4. Navigate through tabs (Dashboard, Charts, Backtest)
5. Test engine Start/Stop buttons

---

## 🐳 Docker Deployment (Optional)

```bash
# Build image
docker build -t ai-trader-api .

# Run container
docker run -p 8000:8000 ai-trader-api
```

## 🚀 Deployment to Render

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   # Create a repo on GitHub
   git remote add origin https://github.com/YOUR_USERNAME/ai-trader.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Create a [Render account](https://render.com).
   - Go to Dashboard -> New -> Web Service.
   - Connect your GitHub repo.
   - Select "Docker" as the Runtime.
   - Click "Create Web Service".
   
   *Alternatively, use the `render.yaml` blueprint*:
   - Go to Blueprints -> New Blueprint Instance.
   - Connect your repo.
   - Render will automatically detect the configuration.

---

## 🔑 Configuration

### API Server
Edit `api/server.py`:
```python
# Change host/port
uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
```

### Mobile App API Endpoint
Edit `mobile-app/src/services/api.ts`:
```typescript
const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000'  // For web browser
  : 'http://YOUR_COMPUTER_IP:8000';  // For physical device
```

**Find your IP**:
- Windows: `ipconfig` → IPv4 Address
- Mac/Linux: `ifconfig` → inet

### V4 Engine Config
Edit `v4/config/config.yaml`:
```yaml
mode: paper  # or backtest
initial_balance: 1000.0
symbols:
  - BTC/USDT
  - ETH/USDT
```

---

## 📈 Usage Examples

### Start Complete Stack
```bash
# Terminal 1: API Server
python -m api.server

# Terminal 2: Mobile App
cd mobile-app && npm start

# Terminal 3: V4 Engine (optional)
python v4/main.py --mode paper
```

### Run Historical Backtest
```bash
python v4/main.py \
  --mode backtest \
  --symbols BTCUSDT ETHUSDT \
  --experiment full
```

### Access Web Dashboard
```bash
# Simple web UI
open frontend/index.html

# Or serve with Python
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

---

## 🛠️ Development

### Install Dev Dependencies
```bash
# Backend
pip install pytest black flake8

# Frontend
cd mobile-app
npm install --save-dev @types/react
```

### Code Formatting
```bash
# Python
black .

# TypeScript/JavaScript
cd mobile-app
npx prettier --write "src/**/*.{ts,tsx}"
```

---

## 📝 Environment Variables

Create `.env` file (optional):
```bash
API_HOST=0.0.0.0
API_PORT=8000
EXCHANGE=binance
LOG_LEVEL=INFO
```

---

## 🚦 Troubleshooting

### API Server Won't Start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Mac/Linux

# Kill process or use different port
```

### Mobile App Can't Connect to API
1. Check API server is running: `curl http://localhost:8000/`
2. Update IP in `mobile-app/src/services/api.ts`
3. Ensure devices are on same network
4. Check firewall settings

### Charts Not Loading
1. Verify Victory Native is installed: `npm list victory-native`
2. Clear Metro cache: `npx expo start -c`
3. Check API market endpoints: `curl http://localhost:8000/market/ohlcv?symbol=BTC/USDT&timeframe=1h`

---

## 📦 Dependencies

### Backend
- fastapi
- uvicorn
- ccxt (crypto exchange library)
- pandas, numpy
- python-dateutil

### Frontend
- React Native + Expo
- React Navigation
- Victory Native (charts)
- Zustand (state management)
- Axios (HTTP client)

---

## 🎯 Roadmap

- [x] V4 trading engine with regime awareness
- [x] FastAPI REST API
- [x] React Native mobile app
- [x] Real-time charts
- [x] Backtest interface
- [ ] Trade log viewer
- [ ] Settings screen
- [ ] WebSocket live data
- [ ] Redis caching
- [ ] Production deployment

---

## 📄 License

MIT

---

## 🤝 Support

For issues or questions:
1. Check API docs: http://localhost:8000/docs
2. Review code in `v4/PROJECT_STATE.md`
3. Test with `test_api.py`

---

**Current Status**: ✅ MVP Complete - Ready for Production Development

Last Updated: 2026-01-11
