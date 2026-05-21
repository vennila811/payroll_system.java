from datetime import datetime
from functools import wraps
import os
import hashlib

from flask import Flask, redirect, render_template, request, session, url_for
import mysql.connector

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-in-production")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="payroll_db",
    )


conn = get_db_connection()
cursor = conn.cursor()


def ensure_payroll_table():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll (
            pay_id INT AUTO_INCREMENT PRIMARY KEY,
            emp_id INT NOT NULL,
            pay_month VARCHAR(20) NOT NULL,
            basic_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
            bonus DECIMAL(12,2) NOT NULL DEFAULT 0,
            overtime_hours DECIMAL(10,2) NOT NULL DEFAULT 0,
            overtime_rate DECIMAL(10,2) NOT NULL DEFAULT 0,
            overtime_pay DECIMAL(12,2) NOT NULL DEFAULT 0,
            pf DECIMAL(12,2) NOT NULL DEFAULT 0,
            prof_tax DECIMAL(12,2) NOT NULL DEFAULT 0,
            other_deductions DECIMAL(12,2) NOT NULL DEFAULT 0,
            income_tax DECIMAL(12,2) NOT NULL DEFAULT 0,
            gross_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
            total_deductions DECIMAL(12,2) NOT NULL DEFAULT 0,
            net_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute("SHOW COLUMNS FROM payroll")
    existing_columns = {row[0] for row in cursor.fetchall()}
    required_columns = {
        "pay_month": "VARCHAR(20) NOT NULL DEFAULT ''",
        "basic_salary": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "bonus": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "overtime_hours": "DECIMAL(10,2) NOT NULL DEFAULT 0",
        "overtime_rate": "DECIMAL(10,2) NOT NULL DEFAULT 0",
        "overtime_pay": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "pf": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "prof_tax": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "other_deductions": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "income_tax": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "gross_salary": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "total_deductions": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "net_salary": "DECIMAL(12,2) NOT NULL DEFAULT 0",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }

    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE payroll ADD COLUMN {column_name} {column_definition}")

    cursor.execute(
        """
        UPDATE payroll
        SET pay_month = DATE_FORMAT(created_at, '%Y-%m')
        WHERE pay_month IS NULL OR pay_month = ''
        """
    )

    conn.commit()


ensure_payroll_table()


def ensure_employees_table():
    """Ensure employees table has password column for employee login"""
    try:
        cursor.execute("SHOW COLUMNS FROM employees")
        existing_columns = {row[0] for row in cursor.fetchall()}
        if "dob" not in existing_columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN dob DATE NULL")
        if "hire_date" not in existing_columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN hire_date DATE NULL")
        if "status" not in existing_columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Active'")
        if "password" not in existing_columns:
            cursor.execute("ALTER TABLE employees ADD COLUMN password VARCHAR(255)")

        cursor.execute("UPDATE employees SET status = 'Active' WHERE status IS NULL OR status = ''")
        cursor.execute("SELECT emp_id FROM employees WHERE password IS NULL OR password = ''")
        for (emp_id,) in cursor.fetchall():
            cursor.execute(
                "UPDATE employees SET password = %s WHERE emp_id = %s",
                (hashlib.sha256(str(emp_id).encode()).hexdigest(), emp_id),
            )
        conn.commit()
        print("Ensured employees table has login and status columns")
    except Exception as e:
        print(f"Error ensuring employees table: {e}")


ensure_employees_table()


def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hash_password_value):
    """Verify password against hash"""
    return hash_password(password) == hash_password_value


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


def employee_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("employee_logged_in"):
            return redirect(url_for("employee_login"))
        return func(*args, **kwargs)

    return wrapper


# Helper function to get dashboard stats
def get_dashboard_stats():
    try:
        cursor.execute("SELECT COUNT(*) FROM employees")
        total_employees = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM attendance")
        total_attendance = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM payroll")
        total_payroll = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(basic_salary) FROM employees")
        result = cursor.fetchone()[0]
        total_salary = result if result else 0

        return {
            "total_employees": total_employees,
            "total_attendance": total_attendance,
            "total_payroll": total_payroll,
            "total_salary": f"{total_salary:,.2f}",
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "total_employees": 0,
            "total_attendance": 0,
            "total_payroll": 0,
            "total_salary": 0,
        }


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("index"))
    if session.get("employee_logged_in"):
        return redirect(url_for("employee_dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("index"))

        error = "Invalid admin username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# HOME - Dashboard
@app.route("/")
@login_required
def index():
    try:
        cursor.execute(
            """
            SELECT
                e.emp_id,
                e.name,
                e.email,
                e.designation,
                COALESCE(d.dept_name, 'N/A') AS dept_name,
                e.basic_salary,
                e.phone,
                e.status
            FROM employees e
            LEFT JOIN department d ON e.dept_id = d.dept_id
            ORDER BY e.emp_id
        """
        )
        employees = cursor.fetchall()
        stats = get_dashboard_stats()
        return render_template(
            "index.html",
            employees=employees,
            total_employees=stats["total_employees"],
            total_attendance=stats["total_attendance"],
            total_payroll=stats["total_payroll"],
            total_salary=stats["total_salary"],
        )
    except Exception as e:
        return f"Error: {e}"


# ADD EMPLOYEE
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_employee():
    if request.method == "POST":
        try:
            data = (
                request.form["name"],
                request.form["gender"],
                request.form["dob"],
                request.form["age"],
                request.form["experience"],
                request.form["phone"],
                request.form["email"],
                request.form["address"],
                request.form["designation"],
                request.form["salary"],
                int(request.form["dept_id"]),
                request.form["hire_date"],
                request.form.get("status", "Active"),
            )

            cursor.execute(
                     """INSERT INTO employees (name, gender, dob, age, experience, phone, email, address, designation, basic_salary, dept_id, hire_date, status)
                         VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                data,
            )
            conn.commit()
            new_emp_id = cursor.lastrowid
            cursor.execute(
                "UPDATE employees SET password = %s WHERE emp_id = %s",
                (hash_password(str(new_emp_id)), new_emp_id),
            )
            conn.commit()
            return redirect("/")
        except Exception as e:
            return f"Error: {e}"

    try:
        cursor.execute("SELECT dept_id, dept_name FROM department")
        departments = cursor.fetchall()
        return render_template("add_employee.html", departments=departments)
    except Exception as e:
        return f"Error: {e}"


# ATTENDANCE
@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    if request.method == "POST":
        try:
            data = (
                request.form["emp_id"],
                request.form["from_date"],
                request.form["to_date"],
                request.form["status"],
                request.form.get("reason", ""),
            )

            cursor.execute(
                "INSERT INTO attendance (emp_id, from_date, to_date, status, leave_reason) VALUES (%s,%s,%s,%s,%s)",
                data,
            )
            conn.commit()
            return redirect("/attendance")
        except Exception as e:
            return f"Error: {e}"

    try:
        cursor.execute("SELECT emp_id, name, basic_salary FROM employees")
        employees = cursor.fetchall()

        cursor.execute(
            """
            SELECT a.att_id, a.emp_id, e.name, a.from_date, a.to_date, a.status, a.leave_reason
            FROM attendance a
            LEFT JOIN employees e ON a.emp_id = e.emp_id
            ORDER BY a.att_id DESC
            LIMIT 50
        """
        )
        attendance_data = cursor.fetchall()

        return render_template(
            "attendance.html", employees=employees, attendance_data=attendance_data
        )
    except Exception as e:
        return f"Error: {e}"


# PAYROLL
@app.route("/payroll", methods=["GET", "POST"])
@login_required
def payroll():
    if request.method == "POST":
        try:
            emp_id = request.form["emp_id"]
            pay_month = request.form.get("month", "").strip()
            bonus = float(request.form.get("bonus", 0))
            pf = float(request.form.get("pf", 0))
            prof_tax = float(request.form.get("prof_tax", 0))
            deduction = float(request.form.get("deduction", 0))
            tax = float(request.form.get("tax", 0))
            overtime_hours = int(float(request.form.get("hours", 0)))
            overtime_rate = 200.0

            if not pay_month:
                return "Error: Payroll month is required"

            cursor.execute(
                "SELECT name, basic_salary, designation FROM employees WHERE emp_id=%s",
                (emp_id,),
            )
            result = cursor.fetchone()

            if not result:
                return f"Error: Employee ID {emp_id} not found"

            _employee_name, basic, _designation = result
            overtime_pay = overtime_hours * overtime_rate
            gross_salary = basic + bonus + overtime_pay
            total_deductions = pf + prof_tax + deduction + tax
            net_salary = gross_salary - total_deductions

            cursor.execute(
                """
                INSERT INTO payroll (
                    emp_id, pay_month, basic_salary, bonus, overtime_hours, overtime_rate,
                    overtime_pay, pf, prof_tax, other_deductions, income_tax,
                    gross_salary, total_deductions, net_salary
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    emp_id,
                    pay_month,
                    basic,
                    bonus,
                    overtime_hours,
                    overtime_rate,
                    overtime_pay,
                    pf,
                    prof_tax,
                    deduction,
                    tax,
                    gross_salary,
                    total_deductions,
                    net_salary,
                ),
            )
            conn.commit()

            return redirect("/payslip/" + str(emp_id))
        except Exception as e:
            return f"Error: {e}"

    try:
        cursor.execute(
            """
            SELECT e.emp_id, e.name, e.basic_salary, e.designation, d.dept_name
            FROM employees e
            LEFT JOIN department d ON e.dept_id = d.dept_id
            ORDER BY e.name
            """
        )
        employees = cursor.fetchall()
        return render_template("payroll.html", employees=employees)
    except Exception as e:
        return f"Error: {e}"


# PAYSLIP
@app.route("/payslip/<emp_id>")
@login_required
def payslip(emp_id):
    try:
        cursor.execute(
            """
            SELECT p.pay_id, p.emp_id, p.pay_month, p.basic_salary, p.bonus,
                   p.overtime_hours, p.overtime_rate, p.overtime_pay, p.pf,
                   p.prof_tax, p.other_deductions, p.income_tax, p.gross_salary,
                   p.total_deductions, p.net_salary, p.created_at,
                   e.name, e.designation, d.dept_name
            FROM payroll p
            LEFT JOIN employees e ON p.emp_id = e.emp_id
            LEFT JOIN department d ON e.dept_id = d.dept_id
            WHERE p.emp_id=%s
            ORDER BY p.pay_id DESC
            LIMIT 1
            """,
            (emp_id,),
        )
        data = cursor.fetchone()
        return render_template(
            "payslip.html", p=data, today=datetime.now().strftime("%d %B %Y")
        )
    except Exception as e:
        return f"Error: {e}"


# REPORTS
@app.route("/reports")
@login_required
def reports():
    try:
        cursor.execute(
            """
            SELECT
                e.name,
                e.emp_id,
                p.net_salary,
                p.pay_id,
                COALESCE(
                    DATE_FORMAT(STR_TO_DATE(p.pay_month, '%Y-%m'), '%b %Y'),
                    DATE_FORMAT(p.created_at, '%b %Y'),
                    p.pay_month,
                    'N/A'
                ) AS pay_month
            FROM employees e
            LEFT JOIN payroll p ON e.emp_id = p.emp_id
            WHERE p.pay_id IS NOT NULL
            ORDER BY p.pay_id DESC
        """
        )
        reports_data = cursor.fetchall()

        cursor.execute(
            """
            SELECT e.name, COUNT(*) as days_present
            FROM employees e
            LEFT JOIN attendance a ON e.emp_id = a.emp_id AND a.status='Present'
            GROUP BY e.emp_id
        """
        )
        attendance_data = cursor.fetchall()

        return render_template(
            "reports.html",
            reports_data=reports_data,
            attendance_data=attendance_data,
            today=datetime.now().strftime("%d %B %Y"),
        )
    except Exception as e:
        return f"Error: {e}"


@app.route("/reports/view/<int:pay_id>")
@login_required
def view_report(pay_id):
    try:
        cursor.execute(
            """
            SELECT p.pay_id, p.emp_id,
                   COALESCE(
                       DATE_FORMAT(STR_TO_DATE(p.pay_month, '%Y-%m'), '%b %Y'),
                       DATE_FORMAT(p.created_at, '%b %Y'),
                       p.pay_month,
                       'N/A'
                   ) AS pay_month,
                   p.basic_salary, p.bonus,
                   p.overtime_hours, p.overtime_rate, p.overtime_pay, p.pf,
                   p.prof_tax, p.other_deductions, p.income_tax, p.gross_salary,
                   p.total_deductions, p.net_salary, p.created_at,
                   e.name, e.designation, d.dept_name
            FROM payroll p
            LEFT JOIN employees e ON p.emp_id = e.emp_id
            LEFT JOIN department d ON e.dept_id = d.dept_id
            WHERE p.pay_id = %s
            LIMIT 1
            """,
            (pay_id,),
        )
        report = cursor.fetchone()

        if not report:
            return "Payroll report not found"

        return render_template(
            "report_view.html",
            p=report,
            today=datetime.now().strftime("%d %B %Y"),
        )
    except Exception as e:
        return f"Error: {e}"


# EDIT EMPLOYEE
@app.route("/edit/<int:emp_id>", methods=["GET", "POST"])
@login_required
def edit_employee(emp_id):
    if request.method == "POST":
        try:
            data = (
                request.form["name"],
                request.form["gender"],
                request.form["dob"],
                request.form["experience"],
                request.form["phone"],
                request.form["email"],
                request.form["address"],
                request.form["designation"],
                request.form["salary"],
                int(request.form["dept_id"]),
                request.form["hire_date"],
                request.form.get("status", "Active"),
                emp_id,
            )

            cursor.execute(
                """UPDATE employees SET name=%s, gender=%s, dob=%s, experience=%s, phone=%s, email=%s,
                   address=%s, designation=%s, basic_salary=%s, dept_id=%s, hire_date=%s, status=%s WHERE emp_id=%s""",
                data,
            )
            conn.commit()
            return redirect("/")
        except Exception as e:
            return f"Error: {e}"

    try:
        cursor.execute(
            """
            SELECT emp_id, name, gender, dob, experience, phone, email, address,
                   designation, dept_id, hire_date, basic_salary, status
            FROM employees
            WHERE emp_id=%s
            """,
            (emp_id,),
        )
        employee = cursor.fetchone()
        cursor.execute("SELECT dept_id, dept_name FROM department")
        departments = cursor.fetchall()
        if employee:
            return render_template(
                "edit_employee.html", employee=employee, departments=departments
            )
        return "Employee not found"
    except Exception as e:
        return f"Error: {e}"


# DELETE EMPLOYEE
@app.route("/delete/<int:emp_id>")
@login_required
def delete_employee(emp_id):
    try:
        cursor.execute("DELETE FROM employees WHERE emp_id=%s", (emp_id,))
        conn.commit()
        return redirect("/")
    except Exception as e:
        return f"Error: {e}"


# ========== EMPLOYEE PORTAL ROUTES ==========

# EMPLOYEE LOGIN
@app.route("/employee-login", methods=["GET", "POST"])
def employee_login():
    if session.get("employee_logged_in"):
        return redirect(url_for("employee_dashboard"))

    error = None
    if request.method == "POST":
        emp_id = request.form.get("emp_id", "").strip()
        password = request.form.get("password", "")

        try:
            cursor.execute(
                "SELECT emp_id, name, password FROM employees WHERE emp_id=%s",
                (emp_id,),
            )
            employee = cursor.fetchone()

            if employee and employee[2] and verify_password(password, employee[2]):
                session["employee_logged_in"] = True
                session["employee_id"] = employee[0]
                session["employee_name"] = employee[1]
                return redirect(url_for("employee_dashboard"))
            else:
                error = "Invalid Employee ID or Password"
        except Exception as e:
            error = f"Login error: {e}"

    return render_template("employee_login.html", error=error)


# EMPLOYEE LOGOUT
@app.route("/employee-logout")
def employee_logout():
    session.clear()
    return redirect(url_for("employee_login"))


# EMPLOYEE DASHBOARD
@app.route("/employee-dashboard")
@employee_login_required
def employee_dashboard():
    try:
        emp_id = session.get("employee_id")
        cursor.execute(
            """
            SELECT e.emp_id, e.name, e.email, e.phone, e.designation, e.basic_salary,
                   e.hire_date, d.dept_name, e.gender, e.dob, e.address
            FROM employees e
            LEFT JOIN department d ON e.dept_id = d.dept_id
            WHERE e.emp_id=%s
            """,
            (emp_id,),
        )
        employee_info = cursor.fetchone()

        cursor.execute(
            """
            SELECT p.pay_id, p.emp_id, p.pay_month, p.basic_salary, p.gross_salary,
                   p.total_deductions, p.net_salary, p.created_at
            FROM payroll p
            WHERE p.emp_id=%s
            ORDER BY p.pay_id DESC
            LIMIT 6
            """,
            (emp_id,),
        )
        payroll_history = cursor.fetchall()

        cursor.execute(
            """
            SELECT a.att_id, a.from_date, a.to_date, a.status, a.leave_reason
            FROM attendance a
            WHERE a.emp_id=%s
            ORDER BY a.att_id DESC
            LIMIT 10
            """,
            (emp_id,),
        )
        attendance_records = cursor.fetchall()

        return render_template(
            "employee_dashboard.html",
            employee=employee_info,
            payroll_history=payroll_history,
            attendance=attendance_records,
        )
    except Exception as e:
        return f"Error: {e}"


# EMPLOYEE VIEW PAYSLIP
@app.route("/employee-payslip/<int:pay_id>")
@employee_login_required
def employee_payslip(pay_id):
    try:
        emp_id = session.get("employee_id")
        cursor.execute(
            """
            SELECT p.pay_id, p.emp_id, p.pay_month, p.basic_salary, p.bonus,
                   p.overtime_hours, p.overtime_rate, p.overtime_pay, p.pf,
                   p.prof_tax, p.other_deductions, p.income_tax, p.gross_salary,
                   p.total_deductions, p.net_salary, p.created_at,
                   e.name, e.designation, d.dept_name, e.email, e.phone
            FROM payroll p
            LEFT JOIN employees e ON p.emp_id = e.emp_id
            LEFT JOIN department d ON e.dept_id = d.dept_id
            WHERE p.pay_id=%s AND p.emp_id=%s
            """,
            (pay_id, emp_id),
        )
        payslip = cursor.fetchone()

        if not payslip:
            return "Payslip not found or unauthorized access"

        return render_template(
            "employee_payslip.html", p=payslip, today=datetime.now().strftime("%d %B %Y")
        )
    except Exception as e:
        return f"Error: {e}"


# EMPLOYEE VIEW ALL PAYSLIPS
@app.route("/employee-payslips")
@employee_login_required
def employee_payslips():
    try:
        emp_id = session.get("employee_id")
        cursor.execute(
            """
            SELECT p.pay_id, p.emp_id, p.pay_month, p.basic_salary, p.gross_salary,
                   p.total_deductions, p.net_salary, p.created_at
            FROM payroll p
            WHERE p.emp_id=%s
            ORDER BY p.pay_id DESC
            """,
            (emp_id,),
        )
        payslips = cursor.fetchall()

        return render_template("employee_payslips.html", payslips=payslips)
    except Exception as e:
        return f"Error: {e}"


# EMPLOYEE VIEW ATTENDANCE
@app.route("/employee-attendance")
@employee_login_required
def employee_attendance():
    try:
        emp_id = session.get("employee_id")
        cursor.execute(
            """
            SELECT a.att_id, a.from_date, a.to_date, a.status, a.leave_reason
            FROM attendance a
            WHERE a.emp_id=%s
            ORDER BY a.att_id DESC
            """,
            (emp_id,),
        )
        attendance_records = cursor.fetchall()

        return render_template("employee_attendance.html", attendance=attendance_records)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True)
