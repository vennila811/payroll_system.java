# Employee Portal Setup Guide

## What's New

Your payroll system now has a complete **Employee Portal** with the following features:

### Employee Features:
✓ **Employee Login** - Employees can log in with their Employee ID and password
✓ **Dashboard** - View personal information, recent payslips, and attendance
✓ **Payslips** - View and download individual payslips
✓ **All Payslips** - Access complete payroll history
✓ **Attendance Records** - View personal attendance history
✓ **Data Security** - Employees can only see their own data

## Implementation Details

### Database Changes
- Added `password` column to `employees` table (VARCHAR(255))
- Passwords are hashed using SHA256 for security

### New Routes

**Employee Routes:**
- `/employee-login` - Employee login page
- `/employee-dashboard` - Employee main dashboard
- `/employee-payslips` - All payslips for the employee
- `/employee-payslip/<pay_id>` - Individual payslip view
- `/employee-attendance` - Employee attendance records
- `/employee-logout` - Employee logout

**Authentication:**
- `@employee_login_required` - Decorator to protect employee routes
- Separate session handling for employees vs admins

### New Templates
1. `employee_login.html` - Login page for employees
2. `employee_dashboard.html` - Main dashboard with overview
3. `employee_payslips.html` - List of all payslips
4. `employee_payslip.html` - Individual payslip (printable)
5. `employee_attendance.html` - Attendance history
6. `login.html` - Updated with employee login link

## How to Set Up Employee Accounts

### Step 1: Start the Application
```bash
python app.py
```

### Step 2: Create Employee Passwords (Admin Only)

Currently, you need to manually set passwords in the database. Use this method:

**Option A: Via MySQL (Recommended)**
```sql
-- Connect to payroll_db and run this for each employee:
UPDATE employees 
SET password = SHA2('password123', 256) 
WHERE emp_id = 1;  -- Replace 1 with the employee ID and 'password123' with desired password
```

**Option B: Via Python Script**
```python
import mysql.connector
import hashlib

def set_employee_password(emp_id, password):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="payroll_db"
    )
    cursor = conn.cursor()
    hashed_pwd = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("UPDATE employees SET password = %s WHERE emp_id = %s", (hashed_pwd, emp_id))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Password set for Employee ID {emp_id}")

# Usage:
set_employee_password(1, "emp123")  # Set password "emp123" for employee 1
set_employee_password(2, "emp456")  # Set password "emp456" for employee 2
```

### Step 3: Test Employee Login

1. **Admin Login First** (if needed):
   - Go to: `http://localhost:5000/login`
   - Username: `admin`
   - Password: `admin123`
   - Add an employee if you haven't already

2. **Employee Login**:
   - Go to: `http://localhost:5000/employee-login`
   - OR click "Click here to login to Employee Portal" from admin login
   - Employee ID: (e.g., `1`)
   - Password: (the password you set in Step 2)

3. **Navigate Portal**:
   - View dashboard with personal info
   - Check recent payslips
   - View attendance records
   - Download/print payslips

## Features Breakdown

### Employee Dashboard
- Personal information (name, email, phone, designation, etc.)
- Recent payroll history (last 6 months)
- Recent attendance records (last 10 entries)
- Quick access buttons to full payslips and attendance

### View Payslip
- Complete payroll breakdown
- Earnings details (basic, bonus, overtime)
- Deductions (PF, Tax, etc.)
- Net salary calculation
- Print/Save as PDF functionality
- Date generated

### Attendance View
- All attendance records in chronological order
- Status badges (Present, Absent, Leave, Half-Day)
- Leave reasons/notes
- Total records count

## Security Features

✓ **Password Hashing** - SHA256 hashing for passwords
✓ **Session Management** - Separate sessions for admin and employee
✓ **Access Control** - Employees can only view their own data
✓ **Login Required** - All employee routes require authentication

## Admin vs Employee Access

### Admin Can:
- Add/Edit/Delete employees
- Manage payroll
- View all reports
- Access all employee data

### Employee Can:
- View own profile
- View own payslips
- View own attendance
- Download payslips
- Logout

### Employee Cannot:
- Modify any data
- View other employees' data
- Access admin functions
- Change payroll information

## Testing Checklist

- [ ] Employee can login with correct credentials
- [ ] Employee sees only their own data
- [ ] Payslip displays correctly with all fields
- [ ] Attendance records show correctly
- [ ] Print/PDF functionality works
- [ ] Logout clears employee session
- [ ] Admin features still work independently
- [ ] Password hashing is working (check DB)

## Troubleshooting

### "Invalid Employee ID or Password"
- Make sure password was set correctly in database
- Check employee ID format
- Ensure employee exists in database

### Employee sees blank dashboard
- Check if payroll exists for that employee
- Verify employee record has all required fields

### Session issues
- Clear browser cookies
- Make sure FLASK_SECRET_KEY is set in environment

## Next Steps (Optional Enhancements)

1. **Add Password Reset Feature**
   - Email-based password reset
   - Security questions

2. **Add Employee Registration**
   - Self-service account creation
   - Email verification

3. **PDF Export**
   - Better formatted PDF download
   - Email payslips directly

4. **Mobile Responsive**
   - Better mobile UI
   - Mobile app integration

5. **Advanced Reports**
   - Yearly salary breakdown
   - Tax summaries
   - Deduction reports

## Files Modified

### Backend (app.py)
- Added `hashlib` import for password hashing
- Added `ensure_employees_table()` function
- Added `hash_password()` and `verify_password()` functions
- Added `employee_login_required` decorator
- Updated login route to handle both admin and employee
- Added 7 new routes for employee portal

### Templates Created
- `employee_login.html`
- `employee_dashboard.html`
- `employee_payslip.html`
- `employee_payslips.html`
- `employee_attendance.html`

### Templates Modified
- `login.html` - Added employee login link

## Database Schema Changes

```sql
-- New column added to employees table:
ALTER TABLE employees ADD COLUMN password VARCHAR(255);
```

## Environment Variables (Optional)

For enhanced security, you can set these in your environment:

```bash
set FLASK_SECRET_KEY=your-secret-key-here
set ADMIN_USERNAME=admin
set ADMIN_PASSWORD=admin123
```

## Support

For issues or questions about the employee portal, check:
1. Employee password is set in database
2. Employee ID is correct
3. No special characters in employee ID
4. Database connection is working

---

**Implementation Complete!** Your payroll system now has a full-featured employee portal. ✓
