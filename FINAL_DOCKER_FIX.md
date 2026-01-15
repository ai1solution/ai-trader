# 🎯 FINAL FIX - Webpack Alias Configuration

## The Problem
Docker builds fail with module-not-found, even though:
- ✅ tsconfig.json is correct
- ✅ Local builds work  
- ✅ All configs are in Git

## Root Cause
Next.js in Docker doesn't reliably read tsconfig.json paths. 
We need to explicitly configure webpack.

## The Solution
Added webpack alias configuration directly to `next.config.ts`.

---

## ✅ EXACT STEPS TO DEPLOY

### Step 1: Verify Local Build
```powershell
cd C:\Users\Naman\Desktop\ai-trader\web_mvp_fresh
npm run build
```
**Expected:** ✓ Compiled successfully

### Step 2: Commit Changes
```powershell
cd C:\Users\Naman\Desktop\ai-trader
git add web_mvp_fresh/next.config.ts
git add web_mvp_fresh/tsconfig.json  
git add DOCKER_BUILD_FIX_STEPS.md
git commit -m "Fix Docker build with explicit webpack alias configuration"
```

### Step 3: Push to GitHub
```powershell
git push origin master
```

### Step 4: Trigger Render Deploy
1. **Go to:** https://dashboard.render.com
2. **Find:** `aios-platform` service
3. **Click:** "Manual Deploy" → **"Clear build cache & deploy"**

⚠️ **IMPORTANT:** You MUST clear the build cache, or it will use old cached layers!

---

## What Was Changed

### `web_mvp_fresh/next.config.ts`

**Before:**
```typescript
const nextConfig: NextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};
```

**After:**
```typescript
import path from "path";

const nextConfig: NextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  webpack: (config) => {
    // Explicitly set @ alias for Docker compatibility
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname),
    };
    return config;
  },
};
```

---

## Why This Works

1. **tsconfig.json** → TypeScript type checking ✓
2. **webpack.config** → Module bundling ✓  
3. **Both needed** → Docker build success ✓

The tsconfig tells TypeScript where files are.
The webpack config tells the bundler where to find them.

---

## Verification

After deploy succeeds, test:

1. **Home page:** https://aios-platform.onrender.com
2. **News loads:** Trending Bitcoin articles
3. **Search works:** Try "BTC/USDT"
4. **Chart renders:** On coin detail page
5. **No errors:** Check browser console (F12)

---

## If It STILL Fails

### Last Resort: Check What's Being Copied

Add this to Dockerfile after line 26 (COPY web_mvp_fresh .):

```dockerfile
# Debug: List what was copied
RUN ls -la
RUN cat tsconfig.json
RUN cat next.config.ts
```

This will show in the build logs what files Docker is seeing.

Then remove these debug lines after confirming.

---

## Summary

**Before:** tsconfig.json only (doesn't work in Docker)
**After:** tsconfig.json + webpack alias (works everywhere)

**Deploy command:**
```powershell
cd C:\Users\Naman\Desktop\ai-trader
git add .
git commit -m "Fix Docker: add webpack alias"
git push origin master
```

Then **clear cache** on Render and deploy! 🚀
