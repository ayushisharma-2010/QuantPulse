# Database Integration Testing Guide 🧪

## ✅ Setup Complete!

**Backend Server:** Running on `http://localhost:8000` ✓
**Frontend Server:** Running on `http://localhost:5173` ✓
**Database:** SQLite (`quantpulse.db`) ✓

---

## 🎯 Test the Real Database Integration

### Test 1: Register a New User

1. **Open your browser:** Go to `http://localhost:5173`

2. **Click "Sign Up"** or go to `http://localhost:5173/signup`

3. **Fill in the form:**
   - Full Name: `Your Name`
   - Email: `yourname@example.com`
   - Password: `Test123456!` (must have 8+ chars, 1 digit, 1 uppercase)
   - Check the terms checkbox

4. **Click "Create Account"**

5. **What happens:**
   - Frontend sends POST request to backend API
   - Backend saves user to database with bcrypt hashed password
   - Backend returns user data
   - Frontend auto-logs you in with JWT token
   - You're redirected to dashboard

6. **Verify in database:**
   ```powershell
   cd QuantPulse-Backend
   python query_db.py
   ```
   You should see your new user!

---

### Test 2: Login with Existing User

1. **Logout** (if logged in)

2. **Go to Sign In:** `http://localhost:5173/signin`

3. **Use the test account we created earlier:**
   - Email: `test@example.com`
   - Password: `TestPassword123!`

4. **Click "Sign In"**

5. **What happens:**
   - Frontend sends credentials to backend
   - Backend checks database for user
   - Backend verifies password hash with bcrypt
   - Backend generates JWT token (7-day expiration)
   - Frontend stores token and user data
   - You're redirected to dashboard

6. **Verify last login updated:**
   ```powershell
   cd QuantPulse-Backend
   python query_db.py
   ```
   The `last_login` timestamp should be updated!

---

### Test 3: Protected Routes (Token Verification)

1. **While logged in**, open browser DevTools (F12)

2. **Go to Application/Storage tab** → Local Storage → `http://localhost:5173`

3. **You should see:**
   - `auth_token`: Your JWT token
   - `user_data`: Your user information

4. **Try accessing dashboard:** `http://localhost:5173/dashboard`
   - Should work because you have a valid token

5. **Delete the token** from Local Storage

6. **Refresh the page**
   - Should redirect to sign in (protected route working!)

---

### Test 4: Real-Time Database Updates

**Open two windows side by side:**

**Window 1:** Browser at `http://localhost:5173`
**Window 2:** PowerShell running `python query_db.py`

**Test Flow:**
1. Register a new user in Window 1
2. Immediately run `python query_db.py` in Window 2
3. See the new user appear instantly!

This proves real-time database integration.

---

### Test 5: View Database in DB Browser

1. **Open DB Browser for SQLite**

2. **Open Database:** `QuantPulse-Backend/quantpulse.db`

3. **Click "Browse Data" tab**

4. **Select "users" table**

5. **You'll see:**
   - All registered users
   - Hashed passwords (secure!)
   - Creation timestamps
   - Last login times
   - All user data

6. **Register a new user in the browser**

7. **Click "Refresh" in DB Browser**

8. **See the new user appear immediately!**

---

## 🔍 What to Look For

### ✅ Success Indicators

**Registration:**
- User appears in database immediately
- Password is hashed (starts with `$2b$12$`)
- Email is unique (can't register same email twice)
- `created_at` timestamp is set
- User gets auto-logged in

**Login:**
- JWT token is generated
- Token stored in localStorage
- `last_login` timestamp updates in database
- User data fetched from database
- Dashboard accessible

**Security:**
- Passwords never stored in plain text
- JWT tokens expire after 7 days
- Protected routes require valid token
- SQL injection prevented by ORM

---

## 🧪 Advanced Tests

### Test Invalid Credentials

1. Try logging in with wrong password
2. Should show error: "Login failed"
3. No token generated
4. User stays on login page

### Test Duplicate Email

1. Register with an email that already exists
2. Should show error: "Registration failed"
3. No duplicate user created in database

### Test Token Expiration

1. Login and get token
2. Manually edit token in localStorage (corrupt it)
3. Try accessing dashboard
4. Should redirect to login (invalid token)

### Test Password Requirements

1. Try registering with weak password (e.g., "test")
2. Should show validation error
3. Must have 8+ characters, 1 digit, 1 uppercase

---

## 📊 Database Queries to Run

### See all users:
```powershell
cd QuantPulse-Backend
python query_db.py
```

### See database schema:
```powershell
python query_db.py schema
```

### Full database inspection:
```powershell
python inspect_db.py
```

### Count users:
```powershell
python -c "from app.database import SessionLocal; from app.models.user import User; db = SessionLocal(); print(f'Total users: {db.query(User).count()}'); db.close()"
```

---

## 🎬 Demo Flow for Presentation

**Show mentors this flow:**

1. **Open DB Browser** showing empty or few users

2. **Open browser** at `http://localhost:5173/signup`

3. **Register a new user** with your name/email

4. **Immediately refresh DB Browser** - show new user appeared!

5. **Click on the user row** - show hashed password (security!)

6. **Logout and login again** with same credentials

7. **Refresh DB Browser** - show `last_login` updated!

8. **Open DevTools** - show JWT token in localStorage

9. **Explain the flow:**
   - Frontend → API → Database → Response
   - Real-time updates
   - Secure password hashing
   - JWT token authentication

---

## 🚨 Troubleshooting

### Frontend can't connect to backend

**Check:**
- Backend running on port 8000?
- Frontend running on port 5173?
- CORS enabled in backend? (should be by default)

**Fix:**
```powershell
# Check backend
curl http://localhost:8000/docs

# Should show Swagger UI
```

### Database locked error

**Fix:**
- Close DB Browser for SQLite
- Stop backend server
- Restart backend server

### Token not working

**Fix:**
- Clear localStorage in browser
- Logout and login again
- Check token hasn't expired (7 days)

---

## ✅ Success Checklist

- [ ] Backend server running
- [ ] Frontend server running
- [ ] Can register new user
- [ ] User appears in database
- [ ] Can login with credentials
- [ ] JWT token generated
- [ ] Dashboard accessible when logged in
- [ ] Protected routes work
- [ ] Last login updates in database
- [ ] Password is hashed in database
- [ ] Can view database in DB Browser
- [ ] Real-time updates visible

---

## 🎉 You're Ready!

Your database is fully integrated and working in real-time with both frontend and backend. Every registration, login, and user action is immediately reflected in the database.

**Next Steps:**
- Add more features (password reset, email verification)
- Deploy to production with PostgreSQL
- Add user roles and permissions
- Implement session management

**For Presentation:**
Show the complete flow from registration to database storage to login - it's impressive and production-ready!
