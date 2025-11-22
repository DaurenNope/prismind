# BeyondLines Feature Testing Checklist

## Prerequisites
- ✅ Backend running: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- ✅ Frontend running: `cd frontend && npm run dev` (or `npm run build && npm run preview`)
- ✅ Supabase credentials configured in environment
- ✅ Browser open to `http://localhost:4173` (or dev port)

---

## 1. Dashboard (`/`)

### ✅ Basic Stats
- [ ] Total posts count displays correctly
- [ ] Platform breakdown (Twitter, Reddit, Threads) shows accurate counts
- [ ] Analyzed vs Unanalyzed counts are correct
- [ ] Stats refresh when data changes

### ✅ Overview Telemetry
- [ ] System heartbeat shows last automation run
- [ ] Operations log displays recent activities (collection, rewrites, digests)
- [ ] Workflow matrix shows:
  - Rewrites queue count
  - Collectors status (healthy/unhealthy)
  - Learning stats (posted content, engagement)
- [ ] All timestamps are humanized correctly ("2h ago", "5m ago")

### ✅ Platform Cadence
- [ ] Each platform shows last sync time
- [ ] Post counts per platform are accurate
- [ ] Export CSV button works (if implemented)

---

## 2. Feed (`/feed`)

### ✅ Post Listing
- [ ] Posts load and display correctly
- [ ] Post cards show: title, content preview, author, platform, timestamp
- [ ] Pagination works (load more / infinite scroll)
- [ ] Empty state shows when no posts

### ✅ Filtering
- [ ] Platform filter (All, Threads, Twitter, Reddit, Telegram, RSS) works
- [ ] Status filter (All, Analyzed, Awaiting AI) works
- [ ] Search by title/content/author works
- [ ] Filters combine correctly (e.g., "Threads + Analyzed")
- [ ] Filter panel is compact and doesn't take too much space

### ✅ Auto-refresh
- [ ] Feed auto-refreshes every 30-60 seconds
- [ ] New posts appear without manual refresh
- [ ] Refresh indicator shows when polling

---

## 3. Collection (`/collection`)

### ✅ Status Cards
- [ ] Each platform (Threads, Twitter, Reddit, Telegram) shows:
  - Last run timestamp
  - Post count from last run
  - Status (idle, error, success)
  - Status message
- [ ] Error states display failure reasons
- [ ] Success states show collected counts

### ✅ Manual Triggers
- [ ] "Run threads" button triggers collection
- [ ] "Run twitter" button triggers collection
- [ ] "Run reddit" button triggers collection
- [ ] "Run telegram" button triggers collection (if enabled)
- [ ] Button shows loading state during collection
- [ ] Success/error feedback appears after run

### ✅ Log Stream
- [ ] Log entries appear in chronological order (newest first)
- [ ] Each log shows: timestamp, platform, status, message, post count
- [ ] Error logs show error details
- [ ] Log stream auto-updates when new runs complete
- [ ] Logs are readable and formatted correctly

### ✅ Real-time Updates
- [ ] Status cards update after collection completes
- [ ] Log stream shows new entry immediately
- [ ] No need to manually refresh page

---

## 4. Publishing (`/publishing`)

### ✅ Transformations Queue
- [ ] Draft transformations display correctly
- [ ] Shows: persona, content preview, source post, created date
- [ ] "Ready for posting" filter works
- [ ] Date filter works (filter by created_at)
- [ ] Edit button opens editor
- [ ] Save button updates transformation
- [ ] Mark as Ready/Draft toggles work
- [ ] Delete button removes transformation

### ✅ Scheduled Posts
- [ ] Scheduled posts list displays correctly
- [ ] Shows: persona, platform, scheduled time, status
- [ ] Date filter works
- [ ] Edit button allows rescheduling
- [ ] Publish Now button works
- [ ] Delete button handles foreign key constraints (marks as cancelled if posted)

### ✅ Schedule Modal
- [ ] Opens when clicking "Schedule" on transformation
- [ ] Persona selector works
- [ ] Platform selector works (Threads, Twitter, Telegram)
- [ ] Date/time picker works
- [ ] Validation prevents past dates
- [ ] Submit creates scheduled post
- [ ] Error handling shows validation errors

---

## 5. Analysis (`/analysis`)

### ✅ Stats Cards
- [ ] Total analyzed count is accurate
- [ ] Queue size shows unanalyzed posts
- [ ] Recent analysis count is correct
- [ ] Stats refresh automatically

### ✅ Queue Preview
- [ ] Shows unanalyzed posts
- [ ] Post previews are readable
- [ ] Platform badges are correct

### ✅ Batch Controls
- [ ] "Analyze Next Batch" button works
- [ ] Batch size selector works
- [ ] Progress indicator shows during analysis
- [ ] Success/error feedback appears

### ✅ Recent Analysis Feed
- [ ] Shows recently analyzed posts
- [ ] Displays: post ID, platform, analysis timestamp, value score
- [ ] Feed updates after batch analysis
- [ ] Clicking post shows full details

---

## 6. Settings (`/settings`)

### ✅ Credentials Tab
- [ ] Threads section shows:
  - Username field
  - Password field (masked)
  - Cookie file upload
  - Enable/disable toggle
- [ ] Twitter section shows same fields
- [ ] Reddit section shows:
  - Client ID
  - Client Secret
  - Username
  - Password
  - Enable/disable toggle
- [ ] Telegram section shows:
  - Bot token field
  - Enable/disable toggle
- [ ] Changes save on blur/change
- [ ] Success toast appears on save
- [ ] Error toast appears on failure

### ✅ Automation Tab
- [ ] Collection interval input works
- [ ] Rewrite cycle input works
- [ ] Values persist (localStorage or backend)

### ✅ Advanced Tab
- [ ] Supabase URL field works
- [ ] Supabase key field works (masked)
- [ ] Danger zone buttons are visible
- [ ] Clear cookies button works (with confirmation)
- [ ] Reset config button works (with confirmation)

---

## 7. Navigation & Layout

### ✅ Sidebar
- [ ] All nav items are visible
- [ ] Active page is highlighted
- [ ] Clicking nav item navigates correctly
- [ ] Sidebar collapses on mobile
- [ ] Hamburger menu works on mobile

### ✅ Top Bar
- [ ] Logo displays correctly
- [ ] Release channel badge shows
- [ ] User avatar/initials show
- [ ] Mobile menu toggle works

### ✅ Responsive Design
- [ ] Layout works on desktop (1280px+)
- [ ] Layout works on tablet (768px-1279px)
- [ ] Layout works on mobile (<768px)
- [ ] No horizontal scrolling
- [ ] Text is readable at all sizes

---

## 8. Error Handling

### ✅ API Errors
- [ ] 500 errors show user-friendly message
- [ ] 404 errors handled gracefully
- [ ] Network errors show retry option
- [ ] Loading states show during API calls

### ✅ Validation Errors
- [ ] Form validation shows inline errors
- [ ] Required fields are marked
- [ ] Invalid input is highlighted
- [ ] Error messages are clear

---

## 9. Performance

### ✅ Loading States
- [ ] Skeleton loaders show during data fetch
- [ ] No flash of empty content
- [ ] Transitions are smooth

### ✅ Auto-refresh
- [ ] Polling doesn't cause performance issues
- [ ] Multiple tabs don't conflict
- [ ] Background updates don't interrupt user

---

## 10. Data Accuracy

### ✅ Real vs Mock Data
- [ ] Dashboard stats are from real database
- [ ] Feed posts are from real database
- [ ] Collection logs are from real database
- [ ] Publishing data is from real database
- [ ] No hard-coded placeholder data

### ✅ Data Consistency
- [ ] Post counts match across pages
- [ ] Platform breakdowns are consistent
- [ ] Timestamps are accurate
- [ ] Status reflects actual state

---

## Quick Test Script

Run these in order:

1. **Dashboard**: Check all stats load, verify numbers make sense
2. **Feed**: Filter by platform, search for a known post
3. **Collection**: Click "Run threads", watch log stream update
4. **Publishing**: View transformations, try editing one
5. **Analysis**: Click "Analyze Next Batch", watch queue update
6. **Settings**: Add a credential, verify it saves

---

## Known Issues to Watch For

- [ ] Threads collector collecting non-post content (should be fixed)
- [ ] DuplicateWidgetID errors in Svelte (migrated, shouldn't appear)
- [ ] Collection 500 errors (datetime issue should be fixed)
- [ ] Missing collection logs (should be fixed with new logging)

---

## Notes

- Test with real Supabase data when possible
- Check browser console for errors
- Check backend logs for exceptions
- Verify data persists after page refresh
