# Docker Build Fix - Complete Testing Guide

## Issue
Docker build fails with module-not-found errors even though local build succeeds.

## Root Cause
The file structure in Docker might be getting flattened incorrectly when copying `web_mvp_fresh`.

## Solution: Revert to @ Alias + Fix tsconfig

The `@/` alias is the correct Next.js pattern. The issue is likely the `tsconfig.json` configuration in Docker.

### Step 1: Revert Imports Back to @ Alias

```bash
cd c:\Users\Naman\Desktop\ai-trader\web_mvp_fresh

# Check current imports
grep -r "from '\.\./\.\./\.\./lib" app/
grep -r "from '\.\./lib" components/
```

### Step 2: Update tsconfig.json

The issue is `moduleResolution: "bundler"` might not work in Docker. Change to `"node"`:

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
    "moduleResolution": "node",  // Changed from "bundler"
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    },
    "baseUrl": "."  // Add this
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": ["node_modules"]
}
```

### Step 3: Alternative - Keep Relative Paths but Fix Docker Copy

If reverting doesn't work, the issue is the Docker COPY command.

Current Dockerfile (line 26):
```dockerfile
COPY web_mvp_fresh .
```

This copies the CONTENTS of web_mvp_fresh to /app, which means:
- `web_mvp_fresh/app` → `/app/app` ✅
- `web_mvp_fresh/lib` → `/app/lib` ✅  
- `web_mvp_fresh/components` → `/app/components` ✅

This should work! So the structure is correct.

### Step 4: Test Build Locally in Docker

```bash
cd c:\Users\Naman\Desktop\ai-trader

# Clean build
docker build --no-cache -t ai-trader-test .

# If it fails, check the build context:
docker build -t ai-trader-debug --target frontend-builder .
docker run --rm -it ai-trader-debug sh
ls -la
ls -la app/
ls -la lib/
ls -la components/
```

## Quick Fix to Try First

Since local build works, try this:

1. **Clean Everything**:
```bash
cd c:\Users\Naman\Desktop\ai-trader\web_mvp_fresh
rm -rf .next
rm -rf node_modules
npm install
npm run build  # Should work locally
```

2. **Rebuild Docker**:
```bash
cd c:\Users\Naman\Desktop\ai-trader
docker build --no-cache -t ai-trader-dashboard .
```

## Final Solution: Add .npmrc

The issue might be npm caching in Docker. Create `.npmrc`:

```
# web_mvp_fresh/.npmrc
fetch-retries=5
fetch-retry-factor=2
fetch-retry-mintimeout=10000
fetch-retry-maxtimeout=60000
```

Then rebuild.

## Last Resort: Simplify Dockerfile

Replace the frontend-builder stage with:

```dockerfile
FROM node:20-alpine as frontend-builder

WORKDIR /build/web_mvp_fresh

# Copy package files
COPY web_mvp_fresh/package*.json ./
RUN npm ci

# Copy all source
COPY web_mvp_fresh/ ./

# Build
ENV NEXT_PUBLIC_API_URL=/api
ENV NODE_ENV=production
RUN npm run build
```

Then in final stage:
```dockerfile
COPY --from=frontend-builder /build/web_mvp_fresh/.next/standalone ./frontend
COPY --from=frontend-builder /build/web_mvp_fresh/.next/static ./frontend/.next/static
COPY --from=frontend-builder /build/web_mvp_fresh/public ./frontend/public
```

---

**Current Status**: Local build ✅ works | Docker build ❌ fails
**Next Action**: Try clean rebuild first, then tsconfig changes
