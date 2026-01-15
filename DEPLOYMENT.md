# Deployment Guide: AI Trader Platform

## 📦 Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- GitHub repository set up
- Render account (for cloud deployment)

---

## 🚀 Local Docker Development

### 1. Build and Run with Docker Compose

```bash
# From the project root directory
cd c:\Users\Naman\Desktop\ai-trader

# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

**Services will be available at:**
- Frontend (Dashboard): http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 2. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### 3. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f backend
```

### 4. Rebuild After Code Changes

```bash
# Rebuild specific service
docker-compose up -d --build frontend

# Rebuild all
docker-compose up -d --build
```

---

## 🌐 Render Deployment

### Architecture on Render

Since Render's free tier allows one service per repository, we'll deploy as a **monolithic service** that serves both the frontend and backend.

### Option 1: Single Service Deployment (Recommended for Free Tier)

#### Step 1: Create a unified Dockerfile

Already created as `Dockerfile` (see below).

#### Step 2: Update `render.yaml`

```yaml
services:
  - type: web
    name: ai-trader-dashboard
    env: docker
    region: ohio
    plan: free
    branch: main
    autoDeploy: true
    dockerfilePath: ./Dockerfile
    healthCheckPath: /coins
    envVars:
      - key: PYTHONUNBUFFERED
        value: 1
      - key: PORT
        value: 3000
```

#### Step 3: Commit and Push

```bash
git add .
git commit -m "Add Docker configuration for deployment"
git push origin main
```

Render will automatically detect the changes and redeploy.

---

### Option 2: Separate Services (Paid Plan Required)

If you upgrade to a paid plan, you can run frontend and backend separately:

#### Update `render.yaml`:

```yaml
services:
  # Backend API
  - type: web
    name: ai-trader-backend
    env: docker
    region: ohio
    plan: starter
    branch: main
    autoDeploy: true
    dockerfilePath: ./Dockerfile.backend
    healthCheckPath: /coins
    envVars:
      - key: PYTHONUNBUFFERED
        value: 1

  # Frontend Dashboard
  - type: web
    name: ai-trader-frontend
    env: docker
    region: ohio
    plan: starter
    branch: main
    autoDeploy: true
    dockerfilePath: ./Dockerfile.frontend
    envVars:
      - key: NEXT_PUBLIC_API_URL
        fromService:
          name: ai-trader-backend
          type: web
          property: host
```

---

## 🔧 Environment Variables

### Backend (.env)
```
PYTHONPATH=/app
PYTHONUNBUFFERED=1
```

### Frontend (set in Render dashboard or docker-compose)
```
NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
```

---

## 🛠️ Troubleshooting

### Issue: Frontend can't reach backend

**Solution**: Update API URL in `lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### Issue: Build fails on Render

**Check**:
1. Dockerfile paths are correct
2. All dependencies in requirements.txt/package.json
3. Build logs in Render dashboard

### Issue: Health check failing

**Check**:
1. Backend `/coins` endpoint is accessible
2. Services started in correct order (backend before frontend)
3. Ports are correctly exposed

---

## 📊 Production Checklist

- [ ] Environment variables configured in Render dashboard
- [ ] Health checks passing
- [ ] API URL points to correct backend
- [ ] CORS configured for frontend domain
- [ ] Logs directory has write permissions
- [ ] SSL/HTTPS enabled (automatic on Render)

---

## 🎯 Quick Commands Reference

```bash
# Local Development
docker-compose up --build        # Start services
docker-compose down             # Stop services
docker-compose logs -f          # View logs

# Docker Build Individual Services
docker build -f Dockerfile.backend -t ai-trader-backend .
docker build -f Dockerfile.frontend -t ai-trader-frontend .

# Run Individual Containers
docker run -p 8000:8000 ai-trader-backend
docker run -p 3000:3000 ai-trader-frontend

# Clean Up
docker-compose down -v          # Remove containers and volumes
docker system prune -a          # Remove all unused images
```

---

## 📝 Deployment Steps Summary

1. **Local Testing**:
   ```bash
   docker-compose up --build
   # Visit http://localhost:3000
   ```

2. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Docker configuration ready"
   git push origin main
   ```

3. **Render Auto-Deploy**:
   - Render detects changes
   - Builds Docker image
   - Deploys automatically
   - Visit: `https://your-app.onrender.com`

4. **Verify**:
   - ✅ Frontend loads
   - ✅ API endpoints respond
   - ✅ Engine data displays

---

## 🔗 Useful Links

- **Local Dashboard**: http://localhost:3000
- **Local API Docs**: http://localhost:8000/docs
- **Render Dashboard**: https://dashboard.render.com
- **GitHub Repo**: https://github.com/your-username/ai-trader
