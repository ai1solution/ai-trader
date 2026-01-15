# 🚀 Quick Deploy Guide - AI Trader Dashboard

## 📋 What You Get

- **Unified Docker Container**: Frontend (Next.js) + Backend (FastAPI) in one image
- **Production Ready**: Optimized builds, health checks, logging
- **Platform**: Deploys on Render (Free Tier), runs locally with Docker

---

## ⚡ Quick Start - Local Docker

### Step 1: Build the Container

```bash
cd C:\Users\Naman\Desktop\ai-trader
docker build -t ai-trader-dashboard .
```

**Build time**: ~3-5 minutes

### Step 2: Run the Container

```bash
docker run -p 3000:3000 -p 8000:8000 ai-trader-dashboard
```

### Step 3: Access the Dashboard

Open your browser:
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

---

## 🌐 Deploy to Render - Exact Steps

### Prerequisites
✅ GitHub repository configured  
✅ Render account logged in  

### Step 1: Commit Docker Configuration

```bash
cd C:\Users\Naman\Desktop\ai-trader

# Add all Docker files
git add Dockerfile render.yaml start.sh .dockerignore
git add web_mvp_fresh/next.config.ts
git add web_mvp_fresh/lib/api.ts
git add web_mvp_fresh/app/api/

# Commit
git commit -m "Add Docker configuration for Render deployment"

# Push to GitHub
git push origin main
```

### Step 2: Render Auto-Deployment

**If this is your first deployment:**

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml`
5. Click **"Apply"**

**If already deployed:**

- Render will auto-detect the push
- Auto-deploy will trigger automatically
- Watch progress in dashboard

### Step 3: Wait for Deployment

- Build time: ~5-8 minutes
- Watch logs in Render dashboard
- Look for: "`Platform is ready!`"

### Step 4: Access Your Live Dashboard

Your app will be at:
```
https://ai-trader-dashboard.onrender.com
```

**Note**: Free tier may spin down after inactivity. First request may take 30-60 seconds to wake up.

---

## 🐳 Docker Compose (Development)

For local development with separate containers:

```bash
# Start both services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## 🔍 Verify Deployment

### Local

```bash
# Test backend
curl http://localhost:8000/coins

# Test frontend
curl http://localhost:3000
```

### Production (Render)

```bash
# Replace with your Render URL
curl https://ai-trader-dashboard.onrender.com/api/coins
```

---

## 🛠️ Troubleshooting

### "Build Failed" on Render

**Check:**
1. All files committed to git
2. `Dockerfile` is in project root
3. `render.yaml` paths are correct

**View logs:**
- Go to Render dashboard → Build logs

### "Health Check Failed"

**Common causes:**
- Backend not starting (check Python dependencies)
- Port mismatch (should be 3000)
- Startup taking too long (increase health check wait time)

**Fix:** Update `render.yaml`:
```yaml
healthCheckPath: /
```

### Frontend Can't Reach Backend

**Check `lib/api.ts`:**

The API client auto-detects environment:
- Local: Uses `http://localhost:8000`
- Production: Uses `/api` (proxied)

**Verify** the api.ts file has:
```typescript
const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
    ? '/api'
    : 'http://localhost:8000';
```

### Container Crashes on Startup

**View logs:**
```bash
# Local
docker logs <container-id>

# Render
Dashboard → Logs tab
```

**Common fixes:**
1. Check Python dependencies installed
2. Verify Node version (should be 20+)
3. Check write permissions for logs/results

---

## 📊 File Checklist

Before deploying, ensure these files exist:

```
ai-trader/
├── Dockerfile                          ✅ Main container definition
├── Dockerfile.backend                  ✅ Backend-only (for docker-compose)
├── Dockerfile.frontend                 ✅ Frontend-only (for docker-compose)
├── docker-compose.yml                  ✅ Local development orchestration
├── start.sh                            ✅ Unified container startup script
├── render.yaml                         ✅ Render deployment config
├── .dockerignore                       ✅ Build optimization
├── requirements.txt                    ✅ Python dependencies
├── engine_api/                         ✅ Backend API code
├── v1_legacy/, v2_modern/, v3/, v4/   ✅ Engine code
└── web_mvp_fresh/
    ├── next.config.ts                  ✅ Next.js config (standalone mode)
    ├── lib/api.ts                      ✅ API client (env-aware)
    └── app/api/[...proxy]/route.ts     ✅ API proxy for production
```

---

## 🎯 Quick Commands Reference

```bash
# LOCAL DOCKER
docker build -t ai-trader-dashboard .                    # Build image
docker run -p 3000:3000 ai-trader-dashboard              # Run container
docker ps                                                 # List running containers
docker logs <container-id>                               # View logs
docker stop <container-id>                               # Stop container

# DOCKER COMPOSE
docker-compose up --build                                # Start all services
docker-compose down                                      # Stop all services
docker-compose logs -f backend                           # View backend logs

# GIT DEPLOYMENT
git add .                                                 # Stage changes
git commit -m "Update deployment config"                  # Commit
git push origin main                                      # Deploy to Render

# CLEANUP
docker system prune -a                                    # Remove unused images
docker volume prune                                       # Remove unused volumes
```

---

## 📈 Performance Tips

### Render Free Tier
- **Cold starts**: ~30-60 seconds
- **Active**: Fast response times
- **Spin down**: After 15 min inactivity

**Keep alive trick** (optional):
Use a service like UptimeRobot to ping your app every 5 minutes.

### Docker Image Size
Current optimized size: ~800MB

**Further optimize:**
- Multi-stage builds (already done ✅)
- .dockerignore (already done ✅)
- Minimal base images (already done ✅)

---

## ✅ Deployment Success Checklist

After deployment, verify:

- [ ] Frontend loads at your Render URL
- [ ] API responds at `/api/coins`
- [ ] Search for a symbol (e.g., BTC/USDT)
- [ ] Coin detail page loads
- [ ] All 4 engine panels show data
- [ ] Chart renders with live data
- [ ] No console errors in browser
- [ ] Health check passing in Render dashboard

---

## 🆘 Getting Help

**Logs locations:**

Local:
- Backend: Container stdout
- Frontend: Container stdout

Render:
- Dashboard → Your Service → Logs tab

**Common error messages:**

1. **"Module not found"** → Missing dependency
2. **"Port already in use"** → Kill existing process
3. **"Permission denied"** → Check file permissions
4. **"Build timed out"** → Reduce image size

---

## 🔗 Next Steps

Once deployed:

1. **Custom Domain** (Render paid plan)
2. **Environment Variables** (in Render dashboard)
3. **SSL Certificate** (automatic on Render)
4. **Monitoring** (Render provides basic metrics)
5. **Scale Up** (upgrade plan for better performance)

---

**Need help?** Check the full deployment guide in `DEPLOYMENT.md`
