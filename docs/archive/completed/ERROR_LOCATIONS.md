# Where Errors Appear - Visual Guide

## 🎯 Quick Answer: 3 Places to Check

### 1. **Browser Console** (Most Important!)
**How to open:** Press `F12` → Click **Console** tab

**What you'll see:**
```
❌ GET http://127.0.0.1:8000/api/posts 500 (Internal Server Error)
❌ Failed to fetch dashboard stats: NetworkError
❌ Uncaught TypeError: Cannot read property 'posts' of null
```

**Location:** Bottom of browser or right side panel

---

### 2. **Backend Terminal** (Python Errors)
**Where:** The terminal where you ran `uvicorn src.api.main:app ...`

**What you'll see:**
```
ERROR:     Exception in ASGI application
Traceback (most recent call last):
  File "src/api/routes/collection.py", line 45
    ...
ValueError: cannot access local variable 'datetime'
INFO:     127.0.0.1:52341 - "GET /api/collection/status HTTP/1.1" 500
```

**Location:** Your terminal window running the backend

---

### 3. **UI Error Messages** (User-Facing)
**Where:** On the page itself

**What you'll see:**
- **Red error box** in the left sidebar (Collection page)
- **Red toast notification** in bottom-right corner
- **Error banner** at top of page
- **"Error loading data"** text where content should be

**Location:** Visible on the webpage

---

## 📍 Specific Locations by Feature

### Collection Page (`/collection`)
**Errors appear:**
- **Left sidebar** (Controls panel) - Red box with error message
- **Browser Console** - Network errors, API failures
- **Backend Terminal** - Python exceptions

**Example:**
```
[Left Sidebar]
┌─────────────────────────┐
│ ⚠️ Error Box            │
│ Collector responded     │
│ with 500                │
└─────────────────────────┘
```

---

### Dashboard (`/`)
**Errors appear:**
- **Top of page** - "Failed to load stats" message
- **Browser Console** - API call failures
- **Backend Terminal** - Database query errors

---

### Feed (`/feed`)
**Errors appear:**
- **Empty state** - "Error loading posts"
- **Browser Console** - Fetch errors
- **Backend Terminal** - Query errors

---

### Publishing (`/publishing`)
**Errors appear:**
- **Toast notification** (bottom-right) - Red toast with ❌
- **Browser Console** - API errors
- **Backend Terminal** - Validation errors

**Example Toast:**
```
┌─────────────────────────┐
│ ❌ Failed to save       │
│    transformation       │
│                    [×]  │
└─────────────────────────┘
(Bottom-right corner)
```

---

## 🔍 How to Debug Step-by-Step

### Step 1: Open Browser DevTools
```
Press F12 (or Cmd+Option+I on Mac)
```

### Step 2: Check Console Tab
```
Look for red error messages
Copy the error text
```

### Step 3: Check Network Tab
```
1. Click "Network" tab in DevTools
2. Refresh page or trigger action
3. Look for red requests (failed)
4. Click on failed request
5. Check "Response" tab for error details
```

### Step 4: Check Backend Terminal
```
Look at uvicorn terminal
Scroll up to see recent errors
Copy the traceback
```

---

## 🎨 Visual Examples

### Browser Console Error:
```
Console (F12)
├─ ❌ GET /api/collection/status 500
├─ ❌ TypeError: Cannot read property 'data' of undefined
└─ ⚠️  Failed to fetch: NetworkError
```

### Backend Terminal Error:
```
$ uvicorn src.api.main:app ...
ERROR: Exception in ASGI application
Traceback (most recent call last):
  File "...", line 45, in get_collection_status
    ...
ValueError: cannot access local variable 'datetime'
```

### UI Error Box:
```
┌─────────────────────────────────┐
│ ⚠️ Collector responded with 500 │
│    (HTTP 500)                   │
└─────────────────────────────────┘
```

### Toast Notification:
```
                    ┌──────────────┐
                    │ ❌ Error      │
                    │ Failed to... │
                    │          [×] │
                    └──────────────┘
                    (Bottom-right)
```

---

## 🚨 Common Error Patterns

### Pattern 1: Backend Not Running
**Browser Console:**
```
Failed to fetch
NetworkError when attempting to fetch resource
```

**UI:**
- Loading spinner never stops
- "Error loading data" message

**Fix:** Start backend with `uvicorn src.api.main:app ...`

---

### Pattern 2: API Returns 500
**Browser Console:**
```
GET /api/collection/status 500 (Internal Server Error)
```

**Network Tab Response:**
```json
{
  "detail": "cannot access local variable 'datetime'"
}
```

**Backend Terminal:**
```
ERROR: ValueError: cannot access local variable 'datetime'
```

**Fix:** Check backend logs, fix the Python error

---

### Pattern 3: CORS Error
**Browser Console:**
```
Access to fetch at 'http://127.0.0.1:8000/api/posts'
from origin 'http://localhost:4173' has been blocked by CORS policy
```

**Fix:** Check CORS settings in `src/api/main.py`

---

## 💡 Pro Tips

1. **Keep DevTools open** while testing - errors appear immediately
2. **Keep backend terminal visible** - see Python errors in real-time
3. **Check Network tab first** when something doesn't work
4. **Copy error messages** to share for debugging
5. **Filter Network tab** by typing "api" to see only API calls

---

## 🧪 Test Error Visibility

Try this to see all error locations:

1. **Stop the backend** (`Ctrl+C` in uvicorn terminal)
2. **Open browser** to `http://localhost:4173`
3. **Open DevTools** (`F12`)
4. **Go to Collection page**
5. **Click "Run threads"**

**You should see:**
- ✅ Browser Console: Network error
- ✅ Network Tab: Failed request (red)
- ✅ UI: Error message in left sidebar
- ✅ Backend Terminal: (Nothing, because it's stopped)

---

## 📝 Quick Reference

| Error Type | Where to Look | What to Check |
|------------|---------------|---------------|
| Frontend JS Error | Browser Console | Red error messages |
| API Call Failed | Network Tab | Status code, Response body |
| Backend Python Error | Backend Terminal | Traceback, ERROR logs |
| User-Facing Error | UI Page | Error boxes, toasts, banners |
