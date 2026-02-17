# Step-by-Step Guide: View User Data in DB Browser for SQLite 📊

## Prerequisites

✅ DB Browser for SQLite installed (you already have it open)
✅ Database file: `QuantPulse-Backend/quantpulse.db`
✅ New user registered: Raja Rathour (imraja729@gmail.com)

---

## Step 1: Open the Database File

### Option A: If DB Browser is Already Open

1. **Click "File"** in the top menu bar
2. **Click "Open Database"** (or press `Ctrl+O`)
3. **Navigate to your project folder:**
   - Go to: `C:\Users\RAJA\QuantPulse\QuantPulse-Backend`
4. **Select the file:** `quantpulse.db`
5. **Click "Open"**

### Option B: If DB Browser is Closed

1. **Open DB Browser for SQLite** application
2. **Click "Open Database"** button on the welcome screen
3. **Navigate to:** `C:\Users\RAJA\QuantPulse\QuantPulse-Backend`
4. **Select:** `quantpulse.db`
5. **Click "Open"**

---

## Step 2: View Database Structure

Once the database is open, you'll see **4 tabs** at the top:
- Database Structure
- Browse Data
- Edit Pragmas
- Execute SQL

**You should currently be on the "Database Structure" tab.**

### What You'll See:

```
📁 Tables (1)
  └─ 📊 users
      ├─ 🔑 id (INTEGER) - Primary Key
      ├─ 📧 email (VARCHAR(255))
      ├─ 🔒 hashed_password (VARCHAR(255))
      ├─ 👤 full_name (VARCHAR(255))
      ├─ ✅ is_active (BOOLEAN)
      ├─ ✉️ is_verified (BOOLEAN)
      ├─ 👑 is_admin (BOOLEAN)
      ├─ ⚙️ preferences (TEXT)
      ├─ 📅 created_at (DATETIME)
      ├─ 🔄 updated_at (DATETIME)
      └─ 🕐 last_login (DATETIME)

📑 Indices (2)
  ├─ ix_users_email (UNIQUE)
  └─ ix_users_id
```

This shows your database has 1 table called "users" with 11 columns.

---

## Step 3: Browse User Data

1. **Click the "Browse Data" tab** (second tab at the top)

2. **In the "Table:" dropdown**, select **"users"**
   - It should already be selected by default

3. **You'll now see a spreadsheet-like view** with all your users!

---

## Step 4: View Your New User (Raja Rathour)

### What You'll See in the Table:

| id | email | hashed_password | full_name | is_active | is_verified | is_admin | preferences | created_at | updated_at | last_login |
|----|-------|-----------------|-----------|-----------|-------------|----------|-------------|------------|------------|------------|
| 1 | test@example.com | $2b$12$ws7T6d... | Test User | 1 | 0 | 0 | NULL | 2026-02-17 06:08:41 | 2026-02-17 06:11:31 | 2026-02-17 06:11:31 |
| 2 | imraja729@gmail.com | $2b$12$... | Raja Rathour | 1 | 0 | 0 | NULL | 2026-02-17 07:02:04 | 2026-02-17 07:02:04 | 2026-02-17 07:02:04 |

### Understanding the Data:

**Row 2 (Your New User):**
- **id:** 2 (second user in database)
- **email:** imraja729@gmail.com ✓
- **hashed_password:** $2b$12$... (bcrypt encrypted - secure!)
- **full_name:** Raja Rathour ✓
- **is_active:** 1 (Yes, account is active)
- **is_verified:** 0 (No, email not verified yet)
- **is_admin:** 0 (No, regular user)
- **preferences:** NULL (no preferences set)
- **created_at:** 2026-02-17 07:02:04 (when you registered)
- **updated_at:** 2026-02-17 07:02:04 (last update)
- **last_login:** 2026-02-17 07:02:04 (when you logged in)

---

## Step 5: View Detailed Information

### To see the full hashed password:

1. **Click on the cell** with the hashed password (starts with `$2b$12$`)
2. **Look at the bottom panel** - it will show the full value
3. **Example:** `$2b$12$AbCdEfGhIjKlMnOpQrStUvWxYz1234567890...`

### To see all columns (if some are hidden):

1. **Scroll horizontally** using the bottom scrollbar
2. Or **resize columns** by dragging the column headers

---

## Step 6: Refresh to See Real-Time Updates

### Test Real-Time Integration:

1. **Keep DB Browser open** with the "Browse Data" tab visible

2. **Go to your browser** (`http://localhost:5173`)

3. **Register another user** or **login again**

4. **Go back to DB Browser**

5. **Click the "Refresh" button** (🔄 icon in the toolbar)
   - Or press `F5`
   - Or click: **View → Refresh**

6. **Watch the data update!** You'll see:
   - New users appear
   - `last_login` timestamps update
   - Real-time database changes

---

## Step 7: Search and Filter

### Find Specific User:

1. **Click on the "Filter" box** (top right, above the table)

2. **Type:** `Raja` or `imraja729`

3. **Press Enter**

4. **Only matching rows will show!**

### Clear Filter:

1. **Click the "X"** in the filter box
2. Or **delete the text** and press Enter

---

## Step 8: Sort Data

### Sort by any column:

1. **Click on a column header** (e.g., "created_at")
2. **Click again** to reverse sort order
3. **Arrow icon** shows sort direction (↑ or ↓)

**Examples:**
- Sort by **id** - see users in order they registered
- Sort by **last_login** - see who logged in recently
- Sort by **email** - alphabetical order

---

## Step 9: Execute Custom SQL Queries

### For Advanced Users:

1. **Click the "Execute SQL" tab** (fourth tab)

2. **Type a query**, for example:

```sql
-- Get all users
SELECT * FROM users;

-- Get only active users
SELECT id, email, full_name, created_at 
FROM users 
WHERE is_active = 1;

-- Count total users
SELECT COUNT(*) as total_users FROM users;

-- Find specific user
SELECT * FROM users 
WHERE email = 'imraja729@gmail.com';

-- Get users registered today
SELECT email, full_name, created_at 
FROM users 
WHERE DATE(created_at) = DATE('now');
```

3. **Click the "Execute" button** (▶️ icon) or press `F5`

4. **Results appear below** in a table

---

## Step 10: Export Data (Optional)

### Export to CSV/JSON:

1. **Go to "Browse Data" tab**

2. **Click "File" → "Export" → "Table as CSV file"**

3. **Choose location** and **save**

4. **Open in Excel** or any spreadsheet app

---

## Quick Reference: Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open Database | `Ctrl+O` |
| Refresh Data | `F5` |
| Execute SQL | `F5` (in Execute SQL tab) |
| Find/Filter | `Ctrl+F` |
| Close Database | `Ctrl+W` |

---

## Troubleshooting

### ❌ "Database is locked" error

**Solution:**
1. Close DB Browser
2. Stop the backend server (if running)
3. Reopen DB Browser
4. Open the database file

### ❌ Can't see new users

**Solution:**
1. Click the **Refresh button** (🔄)
2. Or close and reopen the database
3. Make sure you're looking at the "users" table

### ❌ Columns are too narrow

**Solution:**
1. **Double-click** on column dividers to auto-resize
2. Or **drag** column borders to resize manually

---

## What to Look For (Verification Checklist)

✅ **User ID:** Should be 2 (second user)
✅ **Email:** imraja729@gmail.com
✅ **Full Name:** Raja Rathour
✅ **Password:** Starts with `$2b$12$` (bcrypt hash)
✅ **Active Status:** 1 (true)
✅ **Created Date:** Today's date (2026-02-17)
✅ **Last Login:** Same as created date

---

## For Your Presentation

### Demo Flow:

1. **Show DB Browser** with current users (2 users)

2. **Switch to browser** - register a new user live

3. **Switch back to DB Browser** - click Refresh

4. **Point out:**
   - New user appeared instantly
   - Password is hashed (security!)
   - Timestamps are accurate
   - All data fields populated

5. **Click on the hashed password** - show it's encrypted

6. **Explain:** "This is real-time database integration - every registration, login, and action is immediately stored securely in the database."

---

## Summary

You now know how to:
- ✅ Open the database in DB Browser
- ✅ View all users in the table
- ✅ See your new user (Raja Rathour)
- ✅ Refresh to see real-time updates
- ✅ Filter and search users
- ✅ Execute custom SQL queries
- ✅ Export data

**Your database integration is working perfectly!** Every user registration is immediately saved with secure password hashing and proper timestamps.

---

## Next Steps

- Register more users to test
- Try logging in and watch `last_login` update
- Export user data for analysis
- Show this to your mentors - it's impressive!

**Need help?** Run `python query_db.py` in PowerShell for a quick database summary.
