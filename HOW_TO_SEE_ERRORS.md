# How to See Errors in BeyondLines

## 1. Browser Console (Frontend Errors)

### How to Open:
- **Chrome/Edge**: Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
- **Firefox**: Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
- **Safari**: Enable Developer menu first: Preferences → Advanced → "Show Develop menu", then `Cmd+Option+I`

### What to Look For:
- **Red errors** in the Console tab
- **Network tab** → Failed requests (red status codes like 500, 404)
- **Console tab** → JavaScript errors, API call failures

### Example Errors You Might See:
```
GET http://127.0.0.1:8000/api/posts 500 (Internal Server Error)
Failed to fetch dashboard stats: NetworkError
Uncaught TypeError: Cannot read property 'posts' of null
```

---

## 2. Backend Terminal (API Errors)

### Where:
The terminal where you ran `uvicorn src.api.main:app ...`

### What to Look For:
- **Python tracebacks** (stack traces)
- **ERROR** log messages
- **500 Internal Server Error** responses
- **Exception details**

### Example Output:
```
ERROR:     Exception in ASGI application
Traceback (most recent call last):
  File "src/api/routes/collection.py", line 45, in get_collection_status
    ...
ValueError: cannot access local variable 'datetime'
INFO:     127.0.0.1:52341 - "GET /api/collection/status HTTP/1.1" 500 Internal Server Error
```

---

## 3. UI Error Messages (User-Facing)

### Where:
- **Toast notifications** (top-right corner, usually)
- **Error banners** on pages
- **Inline form errors** (red text under inputs)
- **Empty states** with error messages

### What They Look Like:
- Red toast: "Failed to load posts"
- Red banner: "Collection failed: Authentication error"
- Form error: "Username is required"

---

## 4. Network Tab (API Request/Response)

### How to Open:
1. Open browser DevTools (`F12`)
2. Click **Network** tab
3. Refresh page or trigger an action
4. Click on any request to see details

### What to Check:
- **Status code**:
  - `200` = Success ✅
  - `404` = Not Found ❌
  - `500` = Server Error ❌
  - `401` = Unauthorized ❌
- **Response body**: Click on request → **Response** tab → See error message
- **Request payload**: Click on request → **Payload** tab → See what was sent

### Example:
```
GET /api/collection/status
Status: 500 Internal Server Error
Response: {"detail": "cannot access local variable 'datetime'"}
```

---

## 5. Backend Logs (Detailed)

### Where:
- Terminal running `uvicorn`
- Log files in `logs/` directory (if configured)

### What to Look For:
- Lines starting with `ERROR:`
- Lines starting with `WARNING:`
- Full Python tracebacks
- Request/response logs

---

## Quick Debugging Workflow

### Step 1: Check Browser Console
```bash
# Open DevTools (F12)
# Look at Console tab for red errors
# Look at Network tab for failed requests
```

### Step 2: Check Backend Terminal
```bash
# Look at the uvicorn terminal
# Scroll up to see recent errors
# Look for ERROR or Exception messages
```

### Step 3: Check Network Tab
```bash
# In DevTools → Network tab
# Find the failed request (red status)
# Click it → Check Response tab for error details
```

### Step 4: Check UI
```bash
# Look for toast notifications
# Look for error banners on the page
# Check if page shows "Error loading data"
```

---

## Common Error Patterns

### 1. CORS Error
**Browser Console:**
```
Access to fetch at 'http://127.0.0.1:8000/api/posts' from origin 'http://localhost:4173'
has been blocked by CORS policy
```
**Fix:** Check backend CORS settings in `src/api/main.py`

### 2. 500 Internal Server Error
**Network Tab:**
```
Status: 500
Response: {"detail": "Error message here"}
```
**Backend Terminal:**
```
ERROR: Exception in ASGI application
Traceback...
```
**Fix:** Check backend logs for the actual error

### 3. 404 Not Found
**Network Tab:**
```
Status: 404
Response: {"detail": "Not Found"}
```
**Fix:** Check if API endpoint exists, check URL spelling

### 4. Network Error
**Browser Console:**
```
Failed to fetch
NetworkError when attempting to fetch resource
```
**Fix:** Check if backend is running, check URL/port

### 5. TypeError / Undefined
**Browser Console:**
```
Uncaught TypeError: Cannot read property 'posts' of null
```
**Fix:** Check if API response is null, add null checks in frontend

---

## Testing Error Visibility

### Test 1: Break Something on Purpose
1. Stop the backend (`Ctrl+C` in uvicorn terminal)
2. Try to load Dashboard
3. **You should see:**
   - Browser Console: Network error
   - UI: Error message or loading spinner stuck
   - Network Tab: Failed request (red)

### Test 2: Invalid API Call
1. Open browser console
2. Type: `fetch('http://127.0.0.1:8000/api/nonexistent')`
3. **You should see:**
   - Network Tab: 404 error
   - Console: Error response

### Test 3: Backend Error
1. Make a collection request
2. If it fails, **you should see:**
   - Backend Terminal: Python traceback
   - Network Tab: 500 error with details
   - UI: Error toast or message

---

## Pro Tips

1. **Keep both terminals visible**: Frontend dev server + Backend uvicorn
2. **Keep browser DevTools open** while testing
3. **Check Network tab first** when something doesn't work
4. **Copy error messages** to share for debugging
5. **Check backend logs** for detailed Python errors

---

## Quick Commands

### View Backend Logs in Real-Time
```bash
# If logs are in a file:
tail -f logs/beyondlines_*.log

# Or just watch the uvicorn terminal
```

### Clear Browser Console
```bash
# In DevTools Console, click the 🚫 icon or press Ctrl+L
```

### Filter Network Requests
```bash
# In Network tab, type in filter box:
# - "api" to see only API calls
# - "500" to see only errors
# - "collection" to see collection-related requests
```
