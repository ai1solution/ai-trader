# 🚀 AIOS - Render Deployment Guide

## ✅ Configuration Fixed

The following issues were identified and fixed for Render deployment:

### Issues Found:
1. **PORT handling** - Render assigns PORT dynamically (10000), not 3000
2. **Backend accessibility** - Backend was binding to 0.0.0.0, should be localhost
3. **Health check** - Wasn't using correct PORT variable
4. **Missing API proxy check** - No verification that /api proxy exists

### Files Updated:

#### 1. `render.yaml`
- ✅ Added `dockerCommand: ./start.sh`
- ✅ Set PORT to 10000 (Render's default)
- ✅ Added NEXT_PUBLIC_API_URL=/api
- ✅ Renamed service to `aios-platform`

#### 2. `start.sh`
- ✅ Backend now binds to `127.0.0.1:8000` (localhost only)
- ✅ Frontend binds to `0.0.0.0:$PORT` (Render's PORT)
- ✅ Added proper health checks with retries
- ✅ Better error handling and logging
- ✅ Waits for services to be ready before declaring success

#### 3. `Dockerfile`
- ✅ Added `procps` package for process management
- ✅ Updated PORT default to 10000
- ✅ Extended health check start period to 40s
- ✅ Added better comments

---

## 🎯 Deployment Steps

### Step 1: Commit All Changes

```bash
cd C:\Users\Naman\Desktop\ai-trader

git add .
git commit -m "Fix Render deployment configuration

- Update render.yaml with correct PORT and docker command
- Fix start.sh to bind backend to localhost
- Update Dockerfile for Render compatibility
- Add proper health checks and error handling"

git push origin main
```

### Step 2: Monitor Render Build

1. Go to: https://dashboard.render.com
2. Select your service: `aios-platform`
3. Watch the build logs
4. Build time: 5-10 minutes

### Step 3: Verify Deployment

Once deployed, your app will be available at:
```
https://aios-platform.onrender.com
```

**Test checklist:**
- ✅ Home page loads
- ✅ AIOS logo displays
- ✅ Trending Bitcoin news loads
- ✅ Search works
- ✅ Engine data displays
- ✅ Coin detail page works
- ✅ Charts render

---

## 🔧 How It Works

### Architecture on Render:

```
                   ┌─────────────────────────┐
                   │   Render Container      │
                   │                         │
                   │  ┌──────────────────┐   │
Internet ────────► │  │  Next.js (PORT)  │   │
(Port 443)         │  │   Frontend       │   │
                   │  └────────┬─────────┘   │
                   │           │             │
                   │           │ /api proxy  │
                   │           ▼             │
                   │  ┌──────────────────┐   │
                   │  │  FastAPI (8000)  │   │
                   │  │   Backend        │   │
                   │  └──────────────────┘   │
                   │                         │
                   └─────────────────────────┘
```

### Port Configuration:

1. **External (Internet):** HTTPS (443)
2. **Render → Container:** Dynamic PORT (usually 10000)
3. **Frontend (Next.js):** Binds to `0.0.0.0:$PORT`
4. **Backend (FastAPI):** Binds to `127.0.0.1:8000`
5. **Next.js /api proxy:** Forwards requests to `http://localhost:8000`

---

## 🐛 Troubleshooting

### Issue: Build Fails

**Check:**
```bash
# Test local build
cd C:\Users\Naman\Desktop\ai-trader
docker build -t aios-test .
```

**Solution:**
- If local build works, check Render build logs
- Common issue: Missing node_modules (npm ci fails)
- Fix: Ensure package-lock.json is committed

### Issue: Deployment Crashes

**Check Render logs:**
1. Dashboard → Your Service → Logs
2. Look for errors in:
   - Backend startup
   - Frontend startup
   - Health check failures

**Common causes:**
- Backend not starting (check engine_api/main.py)
- Frontend can't connect to backend (check /api proxy)
- PORT mismatch

### Issue: Health Check Failing

**Symptoms:** "Service unhealthy" in Render

**Fix:**
- Check if frontend is actually running on PORT
- Verify health check path returns 200 OK
- Check start.sh logs for errors

### Issue: News Not Loading

**Check:**
- Browser console for errors
- SerpAPI key is correct
- CORS allowed in engine_api/main.py

---

## 📊 Environment Variables (Render Dashboard)

Optional vars you can set:

```
SERPAPI_KEY=your_key_here
RENDER_EXTERNAL_URL=your-app.onrender.com
```

---

## 💰 Cost Breakdown

**Render Free Tier:**
- ✅ 750 hours/month (enough for 24/7)
- ✅ Auto-sleep after 15 min inactivity
- ✅ 512 MB RAM
- ✅ Shared CPU
- ✅ Custom domain supported

**First request after sleep:** 30-60 seconds (cold start)

---

## 🎉 Success Indicators

When deployment succeeds, you'll see:

```
✓ Build completed
✓ Deploy live
✓ Health checks passing
```

And in the logs:
```
Starting AIOS Platform...
✓ Backend is ready (PID: xxx)
✓ Frontend is ready (PID: xxx)
✓ AIOS Platform is LIVE!
```

---

## 📝 Post-Deployment

### Custom Domain (Optional)

1. Render Dashboard → Settings → Custom Domain
2. Add your domain
3. Update DNS (A or CNAME record)
4. SSL auto-provisioned

### Monitoring

Render provides:
- Deployment history
- Live logs
- Metrics (CPU, RAM, requests)
- Auto-restart on crash

Access: Dashboard → Your Service → Metrics

---

## 🚀 Quick Deploy Checklist

- [ ] All code committed to GitHub
- [ ] `render.yaml` updated with fixed configuration
- [ ] `Dockerfile` has correct PORT handling
- [ ] `start.sh` properly starts both services
- [ ] Pushed to `main` branch
- [ ] Render auto-deploys
- [ ] Build completes (5-10 min)
- [ ] Health checks pass
- [ ] App accessible at Render URL
- [ ] All features work

---

**Ready to deploy! 🎯**

All configurations are now optimized for Render. Just commit and push!
