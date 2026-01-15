# 🚀 AIOS Deployment Guide - GitHub & Render

## Prerequisites Checklist
- ✅ GitHub repository exists
- ✅ Render account connected to GitHub
- ✅ `render.yaml` configured (already done)
- ✅ Docker build tested locally

---

## Step-by-Step Deployment

### Step 1: Check Git Status

```bash
cd C:\Users\Naman\Desktop\ai-trader
git status
```

You should see modified and new files.

---

### Step 2: Stage All Changes

```bash
# Add all new and modified files
git add .

# Verify what will be committed
git status
```

**Expected files to commit:**
- `web_mvp_fresh/components/AIOSLogo.tsx` (new)
- `web_mvp_fresh/components/NewsPanel.tsx` (new)
- `web_mvp_fresh/components/TrendingNews.tsx` (new)
- `web_mvp_fresh/components/LoadingScreen.tsx` (new)
- `web_mvp_fresh/components/SkeletonCard.tsx` (new)
- `web_mvp_fresh/app/page.tsx` (modified)
- `web_mvp_fresh/app/layout.tsx` (modified)
- `web_mvp_fresh/app/coin/[symbol]/page.tsx` (modified)
- `web_mvp_fresh/lib/api.ts` (modified)
- `web_mvp_fresh/next.config.ts` (modified)
- `engine_api/main.py` (modified)
- `engine_api/models.py` (modified)
- `engine_api/worker.py` (modified)
- `engine_api/news_service.py` (new)
- `requirements.txt` (modified)
- `Dockerfile` (modified)
- `Dockerfile.backend` (new)
- `Dockerfile.frontend` (new)
- `docker-compose.yml` (new)
- `start.sh` (new)
- `render.yaml` (modified)
- `.dockerignore` (modified)

---

### Step 3: Commit Changes

```bash
git commit -m "AIOS rebrand with news integration and Docker deployment

- Rebranded to AIOS (Autonomous Intelligence Operating System)
- Added real-time crypto news via SerpAPI (client-side)
- Created trending Bitcoin news component (3 articles)
- Enhanced UI with responsive 3-column layout
- Added animated AIOS logo and loading states
- Implemented skeleton loaders for better UX
- Fixed V3 trend field and V4 data extraction
- Added Docker configuration (unified + compose)
- Updated mobile/desktop responsive spacing
- Direct SerpAPI calls from frontend (no backend dependency for news)"
```

---

### Step 4: Push to GitHub

```bash
# Push to main branch (or your default branch)
git push origin main
```

**Alternative if you use a different branch:**
```bash
git push origin master
```

---

### Step 5: Verify GitHub Push

1. Open your browser
2. Go to: `https://github.com/YOUR_USERNAME/ai-trader`
3. Refresh the page
4. Verify files are updated (look for recent commit timestamp)

---

### Step 6: Monitor Render Deployment

**Render will automatically detect the push and start deploying.**

1. Go to: https://dashboard.render.com
2. Click on your service: `ai-trader-dashboard`
3. Go to the **"Events"** tab
4. You should see: "Deploy started" (triggered by GitHub push)

---

### Step 7: Watch Build Logs

1. In Render dashboard, click on the current deployment
2. View real-time build logs
3. Wait for these key messages:
   ```
   Building frontend...
   ✓ Compiled successfully
   Installing Python dependencies...
   Starting AIOS Platform...
   Platform is ready!
   ```

**Build time:** 5-8 minutes

---

### Step 8: Access Deployment

Once build completes:

1. **Your Live URL**: `https://ai-trader-dashboard.onrender.com`
2. Click the URL in Render dashboard
3. Wait 30-60 seconds for first load (cold start on free tier)

---

### Step 9: Test Deployment

**Critical Tests:**

✅ **Home Page**
- AIOS logo displayed
- Trending Bitcoin news loads (3 articles)
- Search bar functional
- Active engines grid shows

✅ **Search**
- Search for "BTC/USDT"
- Click "Analyze Market"

✅ **Coin Detail**
- Chart renders
- Symbol-specific news loads
- All 4 engine panels display

✅ **News Feature**
- News auto-refreshes
- Articles open in new tab
- Thumbnails display correctly

---

## Troubleshooting

### Issue: Build Fails

**Check:**
1. View build logs in Render
2. Look for error messages
3. Common issues:
   - Missing dependencies
   - Docker build timeout
   - Port conflicts

**Fix:**
```bash
# Test build locally first
docker build -t ai-trader-dashboard .

# If successful locally, push again
git push origin main --force
```

### Issue: News Not Loading

**Check browser console:**
- SerpAPI key should work (already embedded)
- CORS errors? (Should be fine with direct calls)

**Verify:**
1. Open DevTools (F12)
2. Check Network tab
3. Look for `serpapi.com` requests

### Issue: Backend Not Responding

**Render Free Tier Note:**
- Services spin down after 15 minutes of inactivity
- First request may take 30-60 seconds

**Solution:**
- Wait patiently on first load
- Use UptimeRobot to keep alive (optional)

### Issue: Docker Out of Memory

**Render Free Tier Limits:**
- 512 MB RAM
- If build fails, consider:
  1. Splitting into 2 services (paid plan)
  2. Optimizing Docker image size
  3. Using Render's starter plan

---

## Environment Variables (Optional)

If you want to move the SerpAPI key to environment variable:

1. Go to Render dashboard
2. Click your service
3. Go to **"Environment"** tab
4. Add:
   ```
   Key: NEXT_PUBLIC_SERPAPI_KEY
   Value: 37298880d0fcef3adfd0564c3a7cca6fd95b1077fa33677fb1cc5fd1ee21cfb6
   ```
5. Redeploy

Then update `NewsPanel.tsx`:
```typescript
const SERPAPI_KEY = process.env.NEXT_PUBLIC_SERPAPI_KEY || '37298880d0fcef3adfd0564c3a7cca6fd95b1077fa33677fb1cc5fd1ee21cfb6';
```

---

## Post-Deployment

### Custom Domain (Optional - Paid Plan)

1. Render dashboard → Your service → Settings
2. Scroll to "Custom Domain"
3. Add your domain (e.g., `aios.yourdomain.com`)
4. Update DNS records as instructed

### Monitoring

**Render provides:**
- Request logs
- Build logs
- Health check status
- Auto-restart on crashes

**Access logs:**
```
Render Dashboard → Your Service → Logs
```

---

## Quick Reference Commands

```bash
# Full deployment flow
cd C:\Users\Naman\Desktop\ai-trader
git add .
git commit -m "Your message"
git push origin main

# Check status
git status
git log --oneline -5

# Force rebuild on Render (if auto-deploy didn't trigger)
# Manual Deploy button in Render dashboard

# View remote
git remote -v

# Check branch
git branch
```

---

## Success Checklist

After deployment, verify:

- [ ] GitHub shows latest commit
- [ ] Render build completed successfully
- [ ] Live URL loads (https://ai-trader-dashboard.onrender.com)
- [ ] AIOS logo and branding visible
- [ ] Trending Bitcoin news loads (3 articles)
- [ ] Search works
- [ ] Coin detail page renders chart
- [ ] All 4 engines show data
- [ ] News auto-refreshes
- [ ] Mobile responsive (test on phone)

---

## Rollback (If Needed)

```bash
# If something breaks, rollback to previous commit
git log --oneline -10  # Find previous commit hash
git revert <commit-hash>
git push origin main

# Or in Render: Dashboard → Deploy → Select previous deploy → Redeploy
```

---

## Notes

**Render Free Tier:**
- Auto-deploys on every push to `main`
- Builds can take 5-8 minutes
- Services sleep after 15 min inactivity
- 750 hours/month (enough for 24/7)

**Production Checklist:**
- ✅ HTTPS automatic (Render handles SSL)
- ✅ Auto-restart on crashes
- ✅ Health checks configured
- ✅ Environment isolated
- ✅ Logs accessible

---

## Support

**If deployment fails:**
1. Check Render build logs
2. Test Docker build locally
3. Verify all files committed to git
4. Check `render.yaml` syntax

**Render Support:**
- https://render.com/docs
- Community forum: https://community.render.com

---

**You're all set! 🎉**

Your AIOS platform will be live at:
`https://ai-trader-dashboard.onrender.com`

(Exact URL shown in Render dashboard)
