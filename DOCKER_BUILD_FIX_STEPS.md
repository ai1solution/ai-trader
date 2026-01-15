# 🔧 DOCKER BUILD FIX - Exact Steps

## Problem
Docker build fails with "module-not-found" even though local build works.

**Root Cause:** The `tsconfig.json` wasn't committed to Git with the `baseUrl` fix.

---

## ✅ EXACT FIX STEPS

### Step 1: Verify Local Build Works
```powershell
cd C:\Users\Naman\Desktop\ai-trader\web_mvp_fresh
npm run build
```
**Expected:** ✓ Build succeeds

### Step 2: Check Git Status
```powershell
cd C:\Users\Naman\Desktop\ai-trader
git status
```

### Step 3: Ensure tsconfig.json is Tracked
```powershell
git add web_mvp_fresh/tsconfig.json
git add web_mvp_fresh/**/*.tsx
git add web_mvp_fresh/**/*.ts
```

### Step 4: Commit with tsconfig.json
```powershell
git add .
git commit -m "Add tsconfig.json with baseUrl for Docker module resolution"
```

### Step 5: Push to GitHub
```powershell
git push origin master
```

### Step 6: Force Render Rebuild (if needed)
1. Go to https://dashboard.render.com
2. Find your service: `aios-platform`
3. Click "Manual Deploy" → "Deploy latest commit"

---

## 🔍 Verify tsconfig.json is Correct

Your `web_mvp_fresh/tsconfig.json` should have:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    },
    "baseUrl": "."  // ← THIS IS CRITICAL
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts",
    ".next/dev/types/**/*.ts",
    "**/*.mts"
  ],
  "exclude": ["node_modules"]
}
```

**Key elements:**
- ✅ `"baseUrl": "."` - Enables path resolution
- ✅ `"paths": { "@/*": ["./*"] }` - Defines @ alias
- ✅ `"jsx": "react-jsx"` - Next.js requirement
- ✅ `"moduleResolution": "bundler"` - Next.js + Docker compatible

---

## 🐛 If Still Failing

### Option A: Test Docker Build Locally

```powershell
cd C:\Users\Naman\Desktop\ai-trader

# Clean build
docker build --no-cache -t aios-test . 2>&1 | Select-String -Pattern "error|Error|ERROR|failed"

# If build succeeds
docker run -p 3000:3000 -p 8000:8000 aios-test
```

### Option B: Debug Docker Build Context

Create `.dockerignore` to ensure right files are copied:

```
# .dockerignore
node_modules
.next
.git
*.log
.env.local
web_mvp_fresh/node_modules
web_mvp_fresh/.next

# But DON'T ignore:
!web_mvp_fresh/tsconfig.json
!web_mvp_fresh/package.json
!web_mvp_fresh/next.config.ts
```

### Option C: Alternative - Use jsconfig.json

If tsconfig.json issues persist, create `web_mvp_fresh/jsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

---

## 📊 Verification Checklist

Before pushing:

- [ ] Local build works: `npm run build` succeeds
- [ ] tsconfig.json exists in `web_mvp_fresh/`
- [ ] tsconfig.json has `"baseUrl": "."`
- [ ] All component imports use `@/components/*`
- [ ] All lib imports use `@/lib/*`
- [ ] No uncommitted changes: `git status`
- [ ] Pushed to GitHub: `git push`

---

## 🎯 Quick Fix Summary

**The issue:** Docker can't resolve `@/` imports without `baseUrl` in tsconfig.json

**The solution:** Ensure tsconfig.json with baseUrl is committed and pushed

**Commands to run:**
```powershell
cd C:\Users\Naman\Desktop\ai-trader
git add web_mvp_fresh/tsconfig.json
git commit -m "Fix module resolution with baseUrl in tsconfig"
git push origin master
```

Then wait for Render to rebuild (5-10 minutes).

---

## ⚠️ Important Notes

1. **Local vs Docker:** Local builds use your local node_modules cache, Docker starts fresh
2. **tsconfig.json:** Must be in Git, not .gitignore'd
3. **Case sensitivity:** Docker Linux is case-sensitive, Windows is not
4. **Path aliases:** `@/` only works with baseUrl configured

---

## 🚀 If Everything Else Fails

As a last resort, we can switch to relative imports everywhere:

```bash
# Find all @ imports
cd web_mvp_fresh
grep -r "from '@/" app/ components/

# Then we'd convert them all to ../
```

But this should NOT be necessary if tsconfig.json is correct!

---

**Most likely fix:** Just ensure tsconfig.json is committed properly! ✅
