import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, date
import threading
import time
import serial
from adafruit_fingerprint import Adafruit_Fingerprint
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch

class FingerprintAttendanceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fingerprint Attendance System")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
       
        # Initialize sensor variables
        self.uart = None
        self.finger = None
        self.sensor_connected = False
       
        # Initialize database
        self.init_db()
       
        # Create GUI first
        self.create_widgets()
       
        # Initialize fingerprint sensor in background
        self.init_sensor_background()
       
        # Start attendance scanning thread
        self.scanning = False
        self.scan_thread = None
       
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            finger_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            department TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finger_id INTEGER,
            name TEXT,
            department TEXT,
            check_in_time TIMESTAMP,
            check_out_time TIMESTAMP,
            date DATE,
            status TEXT DEFAULT 'present')''')
        conn.commit()
        conn.close()
   
    def create_widgets(self):
        """Create main GUI widgets"""
        # Main title
        title_label = tk.Label(self.root, text="Fingerprint Attendance System",
                              font=("Arial", 20, "bold"), bg='#f0f0f0', fg='#333')
        title_label.pack(pady=10)
       
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
       
        # Create tabs
        self.create_registration_tab()
        self.create_attendance_tab()
        self.create_reports_tab()
        self.create_users_tab()
       
        # Status bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
       
    def create_registration_tab(self):
        """Create user registration tab"""
        reg_frame = ttk.Frame(self.notebook)
        self.notebook.add(reg_frame, text="User Registration")
       
        # Registration form
        form_frame = tk.Frame(reg_frame, bg='white', relief=tk.RAISED, bd=2)
        form_frame.pack(pady=20, padx=20, fill='x')
       
        tk.Label(form_frame, text="Register New User", font=("Arial", 16, "bold"),
                bg='white').pack(pady=10)
       
        # Form fields
        fields_frame = tk.Frame(form_frame, bg='white')
        fields_frame.pack(pady=10)
       
        tk.Label(fields_frame, text="Fingerprint ID (0-127):", bg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.fid_entry = tk.Entry(fields_frame, width=20)
        self.fid_entry.grid(row=0, column=1, padx=5, pady=5)
       
        tk.Label(fields_frame, text="Name:", bg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.name_entry = tk.Entry(fields_frame, width=20)
        self.name_entry.grid(row=1, column=1, padx=5, pady=5)
       
        tk.Label(fields_frame, text="Age:", bg='white').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.age_entry = tk.Entry(fields_frame, width=20)
        self.age_entry.grid(row=2, column=1, padx=5, pady=5)
       
        tk.Label(fields_frame, text="Department:", bg='white').grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.dept_entry = tk.Entry(fields_frame, width=20)
        self.dept_entry.grid(row=3, column=1, padx=5, pady=5)
       
        # Registration button
        reg_button = tk.Button(form_frame, text="Register User", command=self.register_user,
                              bg='#4CAF50', fg='white', font=("Arial", 12, "bold"),
                              padx=20, pady=10)
        reg_button.pack(pady=20)
       
        # Registration status
        self.reg_status = tk.Label(form_frame, text="", bg='white', font=("Arial", 10))
        self.reg_status.pack(pady=5)
       
    def create_attendance_tab(self):
        """Create attendance marking tab"""
        att_frame = ttk.Frame(self.notebook)
        self.notebook.add(att_frame, text="Mark Attendance")
       
        # Attendance marking section
        mark_frame = tk.Frame(att_frame, bg='white', relief=tk.RAISED, bd=2)
        mark_frame.pack(pady=20, padx=20, fill='x')
       
        tk.Label(mark_frame, text="Mark Attendance", font=("Arial", 16, "bold"),
                bg='white').pack(pady=10)
       
        # Scan button
        self.scan_button = tk.Button(mark_frame, text="Start Scanning", command=self.toggle_scanning,
                                    bg='#2196F3', fg='white', font=("Arial", 14, "bold"),
                                    padx=30, pady=15)
        self.scan_button.pack(pady=10)
       
        # Attendance status
        self.att_status = tk.Label(mark_frame, text="Click 'Start Scanning' to begin",
                                  bg='white', font=("Arial", 12))
        self.att_status.pack(pady=10)
       
        # Recent attendance
        recent_frame = tk.Frame(att_frame, bg='white', relief=tk.RAISED, bd=2)
        recent_frame.pack(pady=20, padx=20, fill='both', expand=True)
       
        tk.Label(recent_frame, text="Recent Attendance", font=("Arial", 14, "bold"),
                bg='white').pack(pady=10)
       
        # Treeview for recent attendance
        self.recent_tree = ttk.Treeview(recent_frame, columns=('Name', 'Department', 'Check-in', 'Check-out', 'Status'), show='headings')
        self.recent_tree.heading('Name', text='Name')
        self.recent_tree.heading('Department', text='Department')
        self.recent_tree.heading('Check-in', text='Check-in Time')
        self.recent_tree.heading('Check-out', text='Check-out Time')
        self.recent_tree.heading('Status', text='Status')
        self.recent_tree.pack(pady=10, padx=10, fill='both', expand=True)
       
        # Refresh button
        refresh_button = tk.Button(recent_frame, text="Refresh", command=self.refresh_recent_attendance,
                                  bg='#FF9800', fg='white', font=("Arial", 10, "bold"))
        refresh_button.pack(pady=5)
       
        # Load recent attendance
        self.refresh_recent_attendance()
       
    def create_reports_tab(self):
        """Create reports tab"""
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text="Reports")
       
        # Statistics frame
        stats_frame = tk.Frame(reports_frame, bg='white', relief=tk.RAISED, bd=2)
        stats_frame.pack(pady=20, padx=20, fill='x')
       
        tk.Label(stats_frame, text="Attendance Statistics", font=("Arial", 16, "bold"),
                bg='white').pack(pady=10)
       
        # Stats display
        self.stats_text = tk.Text(stats_frame, height=10, width=70, bg='#f9f9f9')
        self.stats_text.pack(pady=10)
       
        # Buttons frame
        buttons_frame = tk.Frame(stats_frame, bg='white')
        buttons_frame.pack(pady=10)
       
        refresh_stats_button = tk.Button(buttons_frame, text="Refresh Statistics",
                                        command=self.refresh_statistics,
                                        bg='#4CAF50', fg='white', font=("Arial", 10, "bold"))
        refresh_stats_button.pack(side=tk.LEFT, padx=5)
       
        export_button = tk.Button(buttons_frame, text="Export to PDF",
                                 command=self.export_pdf,
                                 bg='#2196F3', fg='white', font=("Arial", 10, "bold"))
        export_button.pack(side=tk.LEFT, padx=5)
       
        # Additional export options
        export_csv_button = tk.Button(buttons_frame, text="Export to CSV",
                                     command=self.export_csv,
                                     bg='#FF9800', fg='white', font=("Arial", 10, "bold"))
        export_csv_button.pack(side=tk.LEFT, padx=5)
       
    def init_sensor_background(self):
        """Initialize fingerprint sensor in background thread"""
        def init_sensor():
            try:
                self.uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
                self.finger = Adafruit_Fingerprint(self.uart)
                self.sensor_connected = True
                self.root.after(0, lambda: self.status_bar.config(text="Fingerprint sensor connected"))
            except Exception as e:
                self.sensor_connected = False
                self.root.after(0, lambda: self.status_bar.config(text=f"Sensor not connected: {e}"))
                self.root.after(0, lambda: messagebox.showwarning("Sensor Warning",
                    f"Fingerprint sensor not connected: {e}\nYou can still use the GUI to view data."))
       
        # Start sensor initialization in separate thread
        sensor_thread = threading.Thread(target=init_sensor)
        sensor_thread.daemon = True
        sensor_thread.start()
       
    def create_users_tab(self):
        """Create users management tab"""
        users_frame = ttk.Frame(self.notebook)
        self.notebook.add(users_frame, text="Registered Users")
       
        # Users list frame
        list_frame = tk.Frame(users_frame, bg='white', relief=tk.RAISED, bd=2)
        list_frame.pack(pady=20, padx=20, fill='both', expand=True)
       
        tk.Label(list_frame, text="Registered Users", font=("Arial", 16, "bold"),
                bg='white').pack(pady=10)
       
        # Treeview for users
        self.users_tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Age', 'Department'), show='headings')
        self.users_tree.heading('ID', text='Fingerprint ID')
        self.users_tree.heading('Name', text='Name')
        self.users_tree.heading('Age', text='Age')
        self.users_tree.heading('Department', text='Department')
        self.users_tree.pack(pady=10, padx=10, fill='both', expand=True)
       
        # Refresh users button
        refresh_users_button = tk.Button(list_frame, text="Refresh Users",
                                        command=self.refresh_users,
                                        bg='#FF9800', fg='white', font=("Arial", 10, "bold"))
        refresh_users_button.pack(pady=5)
       
        # Load users
        self.refresh_users()
       
    def register_user(self):
        """Register a new user"""
        try:
            finger_id = int(self.fid_entry.get())
            name = self.name_entry.get().strip()
            age = int(self.age_entry.get())
            department = self.dept_entry.get().strip()
           
            if not name or not department:
                messagebox.showerror("Error", "Please fill all fields")
                return
           
            if finger_id < 0 or finger_id > 127:
                messagebox.showerror("Error", "Fingerprint ID must be between 0 and 127")
                return
           
            if not self.sensor_connected:
                # Allow manual user addition without fingerprint for testing
                response = messagebox.askyesno("Sensor Not Connected",
                    "Fingerprint sensor not connected. Add user without fingerprint enrollment?")
                if response:
                    self.add_user(finger_id, name, age, department)
                    self.reg_status.config(text="User added without fingerprint!", fg='orange')
                    self.clear_registration_form()
                    self.refresh_users()
                return
           
            self.reg_status.config(text="Please place finger on sensor...", fg='blue')
            self.root.update()
           
            # Start enrollment in separate thread
            thread = threading.Thread(target=self.enroll_fingerprint_thread,
                                     args=(finger_id, name, age, department))
            thread.daemon = True
            thread.start()
           
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values")
        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {e}")
   
    def enroll_fingerprint_thread(self, finger_id, name, age, department):
        """Enroll fingerprint in separate thread"""
        try:
            if self.enroll_fingerprint(finger_id):
                self.add_user(finger_id, name, age, department)
                self.root.after(0, lambda: self.reg_status.config(text="User registered successfully!", fg='green'))
                self.root.after(0, self.clear_registration_form)
                self.root.after(0, self.refresh_users)
            else:
                self.root.after(0, lambda: self.reg_status.config(text="Enrollment failed!", fg='red'))
        except Exception as e:
            self.root.after(0, lambda: self.reg_status.config(text=f"Error: {e}", fg='red'))
   
    def enroll_fingerprint(self, finger_id):
        """Enroll fingerprint"""
        try:
            if not self.sensor_connected or not self.finger:
                return False
               
            # First scan
            self.root.after(0, lambda: self.reg_status.config(text="Place finger on sensor...", fg='blue'))
            timeout_counter = 0
            while self.finger.get_image() != 0x00:
                time.sleep(0.1)
                timeout_counter += 1
                if timeout_counter > 100:  # 10 second timeout
                    self.root.after(0, lambda: self.reg_status.config(text="Timeout waiting for finger", fg='red'))
                    return False
           
            if self.finger.image_2_tz(1) != 0x00:
                return False
           
            # Remove finger
            self.root.after(0, lambda: self.reg_status.config(text="Remove finger...", fg='blue'))
            timeout_counter = 0
            while self.finger.get_image() == 0x00:
                time.sleep(0.1)
                timeout_counter += 1
                if timeout_counter > 50:  # 5 second timeout
                    break
            time.sleep(1)
           
            # Second scan
            self.root.after(0, lambda: self.reg_status.config(text="Place same finger again...", fg='blue'))
            timeout_counter = 0
            while self.finger.get_image() != 0x00:
                time.sleep(0.1)
                timeout_counter += 1
                if timeout_counter > 100:  # 10 second timeout
                    self.root.after(0, lambda: self.reg_status.config(text="Timeout waiting for finger", fg='red'))
                    return False
           
            if self.finger.image_2_tz(2) != 0x00:
                return False
           
            if self.finger.create_model() != 0x00:
                return False
           
            if self.finger.store_model(finger_id) != 0x00:
                return False
           
            return True
        except Exception as e:
            print(f"Enrollment error: {e}")
            return False
   
    def add_user(self, finger_id, name, age, department):
        """Add user to database"""
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
                  (finger_id, name, age, department))
        conn.commit()
        conn.close()
   
    def clear_registration_form(self):
        """Clear registration form"""
        self.fid_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.age_entry.delete(0, tk.END)
        self.dept_entry.delete(0, tk.END)
   
    def toggle_scanning(self):
        """Toggle attendance scanning"""
        if self.scanning:
            self.scanning = False
            self.scan_button.config(text="Start Scanning", bg='#2196F3')
            self.att_status.config(text="Scanning stopped")
        else:
            if not self.sensor_connected:
                messagebox.showerror("Error", "Fingerprint sensor not connected")
                return
           
            self.scanning = True
            self.scan_button.config(text="Stop Scanning", bg='#f44336')
            self.att_status.config(text="Scanning for fingerprints...")
           
            # Start scanning thread
            self.scan_thread = threading.Thread(target=self.scan_attendance_thread)
            self.scan_thread.daemon = True
            self.scan_thread.start()
   
    def scan_attendance_thread(self):
        """Scan for attendance in separate thread"""
        while self.scanning:
            try:
                if not self.sensor_connected or not self.finger:
                    time.sleep(1)
                    continue
                   
                if self.finger.get_image() == 0x00:
                    if self.finger.image_2_tz(1) == 0x00:
                        if self.finger.finger_search() == 0x00:
                            finger_id = self.finger.finger_id
                            result = self.mark_attendance(finger_id)
                            if result:
                                action, user = result
                                if action == "check_in":
                                    self.root.after(0, lambda: self.att_status.config(
                                        text=f"Check-in recorded for {user[1]} ({user[3]})"))
                                elif action == "check_out":
                                    self.root.after(0, lambda: self.att_status.config(
                                        text=f"Check-out recorded for {user[1]} ({user[3]})"))
                                elif action == "already_checked_out":
                                    self.root.after(0, lambda: self.att_status.config(
                                        text=f"{user[1]} already completed today's attendance"))
                                self.root.after(0, self.refresh_recent_attendance)
                            else:
                                self.root.after(0, lambda: self.att_status.config(
                                    text="Unknown fingerprint detected"))
                            time.sleep(2)  # Prevent multiple scans
                        else:
                            self.root.after(0, lambda: self.att_status.config(
                                text="Fingerprint not recognized"))
                            time.sleep(1)
                time.sleep(0.1)
            except Exception as e:
                print(f"Scan error: {e}")
                time.sleep(1)
   
    def mark_attendance(self, finger_id):
        """Mark attendance for user with check-in/check-out logic"""
        user = self.get_user(finger_id)
        if not user:
            return None
       
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
       
        # Get today's date
        today = date.today().strftime('%Y-%m-%d')
       
        # Check if user has any attendance record for today
        c.execute("SELECT * FROM attendance WHERE finger_id = ? AND date = ?", (finger_id, today))
        today_record = c.fetchone()
       
        if today_record is None:
            # No record for today - this is check-in
            c.execute("""INSERT INTO attendance (finger_id, name, department, check_in_time, date, status)
                         VALUES (?, ?, ?, ?, ?, 'checked_in')""",
                      (finger_id, user[1], user[3], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), today))
            conn.commit()
            conn.close()
            return ("check_in", user)
       
        elif today_record[5] is None:  # check_out_time is None
            # Has check-in but no check-out - this is check-out
            c.execute("""UPDATE attendance SET check_out_time = ?, status = 'completed'
                         WHERE finger_id = ? AND date = ?""",
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), finger_id, today))
            conn.commit()
            conn.close()
            return ("check_out", user)
       
        else:
            # Already has both check-in and check-out for today
            conn.close()
            return ("already_checked_out", user)
   
    def get_user(self, finger_id):
        """Get user by fingerprint ID"""
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE finger_id = ?", (finger_id,))
        user = c.fetchone()
        conn.close()
        return user
   
    def refresh_recent_attendance(self):
        """Refresh recent attendance display"""
        # Clear existing items
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
       
        # Get recent attendance
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("""SELECT name, department, check_in_time, check_out_time, status
                     FROM attendance ORDER BY check_in_time DESC LIMIT 15""")
        rows = c.fetchall()
        conn.close()
       
        # Add to treeview
        for row in rows:
            name, dept, check_in, check_out, status = row
            check_in_display = check_in.split()[1][:5] if check_in else "N/A"  # Show only HH:MM
            check_out_display = check_out.split()[1][:5] if check_out else "Not yet"
           
            # Color code based on status
            item_id = self.recent_tree.insert('', 'end', values=(name, dept, check_in_display, check_out_display, status))
           
            if status == 'completed':
                self.recent_tree.set(item_id, 'Status', 'Completed')
            elif status == 'checked_in':
                self.recent_tree.set(item_id, 'Status', 'Checked In')
   
    def refresh_users(self):
        """Refresh users display"""
        # Clear existing items
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
       
        # Get users
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY finger_id")
        rows = c.fetchall()
        conn.close()
       
        # Add to treeview
        for row in rows:
            self.users_tree.insert('', 'end', values=row)
   
    def refresh_statistics(self):
        """Refresh attendance statistics"""
        self.stats_text.delete(1.0, tk.END)
       
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
       
        # Total registered users
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
       
        # Total attendance records
        c.execute("SELECT COUNT(*) FROM attendance")
        total_attendance = c.fetchone()[0]
       
        # Today's attendance
        today = date.today().strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
        today_attendance = c.fetchone()[0]
       
        # Today's completed attendance (both check-in and check-out)
        c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'completed'", (today,))
        today_completed = c.fetchone()[0]
       
        # Today's checked-in only
        c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'checked_in'", (today,))
        today_checked_in = c.fetchone()[0]
       
        # Attendance by department
        c.execute("SELECT department, COUNT(*) FROM attendance GROUP BY department")
        dept_attendance = c.fetchall()
       
        # User attendance summary with working hours
        c.execute("""
            SELECT u.name, u.department,
                   COUNT(a.finger_id) as days_present,
                   SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as days_completed,
                   AVG(CASE WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL
                       THEN (julianday(a.check_out_time) - julianday(a.check_in_time)) * 24
                       ELSE NULL END) as avg_hours
            FROM users u
            LEFT JOIN attendance a ON u.finger_id = a.finger_id
            GROUP BY u.finger_id
            ORDER BY days_present DESC
        """)
        user_summary = c.fetchall()
       
        # Today's status
        c.execute("""
            SELECT u.name, u.department, a.check_in_time, a.check_out_time, a.status
            FROM users u
            LEFT JOIN attendance a ON u.finger_id = a.finger_id AND a.date = ?
            ORDER BY a.check_in_time DESC
        """, (today,))
        today_status = c.fetchall()
       
        conn.close()
       
        # Display statistics
        stats = f"=== ATTENDANCE STATISTICS ===\n\n"
        stats += f"Total Registered Users: {total_users}\n"
        stats += f"Total Attendance Records: {total_attendance}\n"
        stats += f"Today's Attendance: {today_attendance}\n"
        stats += f"Today's Completed (Check-in + Check-out): {today_completed}\n"
        stats += f"Today's Checked-in Only: {today_checked_in}\n"
        stats += f"Today's Absent: {total_users - today_attendance}\n\n"
       
        stats += "=== TODAY'S STATUS ===\n"
        stats += f"{'Name':<20} {'Department':<15} {'Check-in':<10} {'Check-out':<10} {'Status':<12}\n"
        stats += "-" * 75 + "\n"
        for name, dept, check_in, check_out, status in today_status:
            if name:  # Only show users with records today
                check_in_time = check_in.split()[1][:5] if check_in else "N/A"
                check_out_time = check_out.split()[1][:5] if check_out else "N/A"
                status_display = status if status else "Absent"
                stats += f"{name:<20} {dept:<15} {check_in_time:<10} {check_out_time:<10} {status_display:<12}\n"
        stats += "\n"
       
        stats += "=== DEPARTMENT WISE ATTENDANCE ===\n"
        for dept, count in dept_attendance:
            stats += f"{dept}: {count} records\n"
        stats += "\n"
       
        stats += "=== USER ATTENDANCE SUMMARY ===\n"
        stats += f"{'Name':<20} {'Department':<15} {'Days Present':<12} {'Days Completed':<15} {'Avg Hours':<10}\n"
        stats += "-" * 80 + "\n"
        for name, dept, days_present, days_completed, avg_hours in user_summary:
            avg_hours_display = f"{avg_hours:.1f}" if avg_hours else "N/A"
            stats += f"{name:<20} {dept:<15} {days_present:<12} {days_completed:<15} {avg_hours_display:<10}\n"
       
        self.stats_text.insert(1.0, stats)
   
    def export_pdf(self):
        """Export attendance report to PDF"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
           
            if filename:
                conn = sqlite3.connect("users.db")
                c = conn.cursor()
                
                # Get all necessary data
                # Basic statistics
                c.execute("SELECT COUNT(*) FROM users")
                total_users = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM attendance")
                total_attendance = c.fetchone()[0]
                
                today = date.today().strftime('%Y-%m-%d')
                c.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today,))
                today_attendance = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'completed'", (today,))
                today_completed = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'checked_in'", (today,))
                today_checked_in = c.fetchone()[0]
                
                # Today's detailed status
                c.execute("""
                    SELECT u.name, u.department, a.check_in_time, a.check_out_time, a.status
                    FROM users u
                    LEFT JOIN attendance a ON u.finger_id = a.finger_id AND a.date = ?
                    ORDER BY u.name
                """, (today,))
                today_status = c.fetchall()
                
                # Department wise attendance
                c.execute("SELECT department, COUNT(*) FROM attendance GROUP BY department")
                dept_attendance = c.fetchall()
                
                # User attendance summary
                c.execute("""
                    SELECT u.name, u.department,
                           COUNT(a.finger_id) as days_present,
                           SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as days_completed,
                           AVG(CASE WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL
                               THEN (julianday(a.check_out_time) - julianday(a.check_in_time)) * 24
                               ELSE NULL END) as avg_hours
                    FROM users u
                    LEFT JOIN attendance a ON u.finger_id = a.finger_id
                    GROUP BY u.finger_id
                    ORDER BY days_present DESC
                """)
                user_summary = c.fetchall()
                
                # Recent attendance records
                c.execute("""
                    SELECT name, department, check_in_time, check_out_time, status, date
                    FROM attendance 
                    ORDER BY check_in_time DESC 
                    LIMIT 20
                """)
                recent_attendance = c.fetchall()
                
                conn.close()
                
                # Create PDF document
                doc = SimpleDocTemplate(filename, pagesize=A4)
                story = []
                styles = getSampleStyleSheet()
                
                # Custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    spaceAfter=30,
                    alignment=1,  # Center alignment
                    textColor=colors.darkblue
                )
                
                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=14,
                    spaceAfter=12,
                    textColor=colors.darkblue
                )
                
                # Title
                story.append(Paragraph("Fingerprint Attendance System Report", title_style))
                story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                story.append(Spacer(1, 20))
                
                # Summary Statistics
                story.append(Paragraph("Summary Statistics", heading_style))
                summary_data = [
                    ['Metric', 'Value'],
                    ['Total Registered Users', str(total_users)],
                    ['Total Attendance Records', str(total_attendance)],
                    ['Today\'s Attendance', str(today_attendance)],
                    ['Today\'s Completed (Check-in + Check-out)', str(today_completed)],
                    ['Today\'s Checked-in Only', str(today_checked_in)],
                    ['Today\'s Absent', str(total_users - today_attendance)]
                ]
                
                summary_table = Table(summary_data)
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(summary_table)
                story.append(Spacer(1, 20))
                
                # Today's Status
                story.append(Paragraph("Today's Attendance Status", heading_style))
                today_data = [['Name', 'Department', 'Check-in', 'Check-out', 'Status']]
                
                for name, dept, check_in, check_out, status in today_status:
                    if name:  # Only show users with records
                        check_in_time = check_in.split()[1][:5] if check_in else "N/A"
                        check_out_time = check_out.split()[1][:5] if check_out else "N/A"
                        status_display = status if status else "Absent"
                        today_data.append([name, dept or "N/A", check_in_time, check_out_time, status_display])
                
                if len(today_data) > 1:
                    today_table = Table(today_data)
                    today_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 8)
                    ]))
                    story.append(today_table)
                else:
                    story.append(Paragraph("No attendance records for today.", styles['Normal']))
                story.append(Spacer(1, 20))
                
                # Department wise attendance
                if dept_attendance:
                    story.append(Paragraph("Department-wise Attendance", heading_style))
                    dept_data = [['Department', 'Total Records']]
                    for dept, count in dept_attendance:
                        dept_data.append([dept or "N/A", str(count)])
                    
                    dept_table = Table(dept_data)
                    dept_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(dept_table)
                    story.append(Spacer(1, 20))
                
                # User attendance summary
                story.append(Paragraph("User Attendance Summary", heading_style))
                user_data = [['Name', 'Department', 'Days Present', 'Days Completed', 'Avg Hours']]
                
                for name, dept, days_present, days_completed, avg_hours in user_summary:
                    avg_hours_display = f"{avg_hours:.1f}" if avg_hours else "N/A"
                    user_data.append([
                        name, 
                        dept or "N/A", 
                        str(days_present), 
                        str(days_completed), 
                        avg_hours_display
                    ])
                
                user_table = Table(user_data)
                user_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8)
                ]))
                story.append(user_table)
                story.append(Spacer(1, 20))
                
                # Recent attendance records
                story.append(Paragraph("Recent Attendance Records (Last 20)", heading_style))
                recent_data = [['Name', 'Department', 'Date', 'Check-in', 'Check-out', 'Status']]
                
                for name, dept, check_in, check_out, status, date_record in recent_attendance:
                    check_in_time = check_in.split()[1][:5] if check_in else "N/A"
                    check_out_time = check_out.split()[1][:5] if check_out else "N/A"
                    recent_data.append([
                        name, 
                        dept or "N/A", 
                        date_record, 
                        check_in_time, 
                        check_out_time, 
                        status or "N/A"
                    ])
                
                recent_table = Table(recent_data)
                recent_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 7)
                ]))
                story.append(recent_table)
                
                # Build PDF
                doc.build(story)
                messagebox.showinfo("Success", f"PDF report exported successfully to:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
    
    def export_csv(self):
        """Export attendance data to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
           
            if filename:
                conn = sqlite3.connect("users.db")
                c = conn.cursor()
                
                # Get all attendance data with user details
                c.execute("""
                    SELECT u.name, u.department, a.check_in_time, a.check_out_time, 
                           a.date, a.status,
                           CASE WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL
                               THEN printf('%.2f', (julianday(a.check_out_time) - julianday(a.check_in_time)) * 24)
                               ELSE 'N/A' END as hours_worked
                    FROM users u
                    LEFT JOIN attendance a ON u.finger_id = a.finger_id
                    ORDER BY a.date DESC, a.check_in_time DESC
                """)
                
                rows = c.fetchall()
                conn.close()
                
                # Write to CSV
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow(['Name', 'Department', 'Check-in Time', 'Check-out Time', 
                                   'Date', 'Status', 'Hours Worked'])
                    
                    # Write data
                    for row in rows:
                        writer.writerow(row)
                
                messagebox.showinfo("Success", f"CSV file exported successfully to:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")

# Add this method to complete the class if needed
def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = FingerprintAttendanceGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()