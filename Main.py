import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, date, timedelta
import threading
import time
import serial
from adafruit_fingerprint import Adafruit_Fingerprint
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from tkcalendar import DateEntry  # You may need to install: pip install tkcalendar

class FingerprintAttendanceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fingerprint Attendance System")
        self.root.geometry("1300x800")
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
        self.create_datewise_attendance_tab()  # New tab
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

    def create_datewise_attendance_tab(self):
        """Create date-wise attendance tab"""
        datewise_frame = ttk.Frame(self.notebook)
        self.notebook.add(datewise_frame, text="Date-wise Attendance")
        
        # Filter section
        filter_frame = tk.Frame(datewise_frame, bg='white', relief=tk.RAISED, bd=2)
        filter_frame.pack(pady=20, padx=20, fill='x')
        
        tk.Label(filter_frame, text="Date-wise Attendance Filter", font=("Arial", 16, "bold"),
                bg='white').pack(pady=10)
        
        # Filter controls
        controls_frame = tk.Frame(filter_frame, bg='white')
        controls_frame.pack(pady=10)
        
        # Date selection
        tk.Label(controls_frame, text="Select Date:", bg='white', font=("Arial", 12)).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.date_var = tk.StringVar()
        self.date_entry = DateEntry(controls_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Department filter
        tk.Label(controls_frame, text="Department:", bg='white', font=("Arial", 12)).grid(row=0, column=2, sticky='e', padx=5, pady=5)
        self.dept_filter_var = tk.StringVar()
        self.dept_filter_combo = ttk.Combobox(controls_frame, textvariable=self.dept_filter_var, width=15)
        self.dept_filter_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # Status filter
        tk.Label(controls_frame, text="Status:", bg='white', font=("Arial", 12)).grid(row=0, column=4, sticky='e', padx=5, pady=5)
        self.status_filter_var = tk.StringVar()
        self.status_filter_combo = ttk.Combobox(controls_frame, textvariable=self.status_filter_var, width=15)
        self.status_filter_combo['values'] = ('All', 'Present', 'Absent', 'Checked In', 'Completed')
        self.status_filter_combo.set('All')
        self.status_filter_combo.grid(row=0, column=5, padx=5, pady=5)
        
        # Filter buttons
        buttons_frame = tk.Frame(filter_frame, bg='white')
        buttons_frame.pack(pady=10)
        
        filter_button = tk.Button(buttons_frame, text="Filter Attendance", command=self.filter_datewise_attendance,
                                 bg='#4CAF50', fg='white', font=("Arial", 12, "bold"))
        filter_button.pack(side=tk.LEFT, padx=5)
        
        clear_filter_button = tk.Button(buttons_frame, text="Clear Filter", command=self.clear_datewise_filter,
                                       bg='#FF9800', fg='white', font=("Arial", 12, "bold"))
        clear_filter_button.pack(side=tk.LEFT, padx=5)
        
        export_date_button = tk.Button(buttons_frame, text="Export Date Report", command=self.export_datewise_report,
                                      bg='#2196F3', fg='white', font=("Arial", 12, "bold"))
        export_date_button.pack(side=tk.LEFT, padx=5)
        
        # Date-wise attendance display
        display_frame = tk.Frame(datewise_frame, bg='white', relief=tk.RAISED, bd=2)
        display_frame.pack(pady=20, padx=20, fill='both', expand=True)
        
        tk.Label(display_frame, text="Date-wise Attendance Records", font=("Arial", 14, "bold"),
                bg='white').pack(pady=10)
        
        # Summary info
        self.datewise_summary = tk.Label(display_frame, text="", bg='white', font=("Arial", 11))
        self.datewise_summary.pack(pady=5)
        
        # Treeview for date-wise attendance
        self.datewise_tree = ttk.Treeview(display_frame, columns=('Name', 'Department', 'Date', 'Check-in', 'Check-out', 'Status', 'Hours'), show='headings')
        self.datewise_tree.heading('Name', text='Name')
        self.datewise_tree.heading('Department', text='Department')
        self.datewise_tree.heading('Date', text='Date')
        self.datewise_tree.heading('Check-in', text='Check-in Time')
        self.datewise_tree.heading('Check-out', text='Check-out Time')
        self.datewise_tree.heading('Status', text='Status')
        self.datewise_tree.heading('Hours', text='Hours Worked')
        
        # Configure column widths
        self.datewise_tree.column('Name', width=120)
        self.datewise_tree.column('Department', width=100)
        self.datewise_tree.column('Date', width=80)
        self.datewise_tree.column('Check-in', width=80)
        self.datewise_tree.column('Check-out', width=80)
        self.datewise_tree.column('Status', width=80)
        self.datewise_tree.column('Hours', width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.datewise_tree.yview)
        self.datewise_tree.configure(yscrollcommand=scrollbar.set)
        
        self.datewise_tree.pack(side=tk.LEFT, pady=10, padx=10, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load department options
        self.load_department_options()
        
        # Load today's attendance by default
        self.date_entry.set_date(date.today())
        self.filter_datewise_attendance()

    def load_department_options(self):
        """Load department options for filter"""
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT DISTINCT department FROM users WHERE department IS NOT NULL ORDER BY department")
        departments = [row[0] for row in c.fetchall()]
        conn.close()
        
        self.dept_filter_combo['values'] = ['All'] + departments
        self.dept_filter_combo.set('All')

    def filter_datewise_attendance(self):
        """Filter and display date-wise attendance"""
        # Clear existing items
        for item in self.datewise_tree.get_children():
            self.datewise_tree.delete(item)
        
        selected_date = self.date_entry.get_date().strftime('%Y-%m-%d')
        selected_dept = self.dept_filter_var.get()
        selected_status = self.status_filter_var.get()
        
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        
        # Build query based on filters
        query = """
            SELECT u.name, u.department, a.date, a.check_in_time, a.check_out_time, a.status,
                   CASE WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL
                       THEN printf('%.2f', (julianday(a.check_out_time) - julianday(a.check_in_time)) * 24)
                       ELSE 'N/A' END as hours_worked,
                   CASE WHEN a.finger_id IS NULL THEN 'Absent' ELSE COALESCE(a.status, 'Present') END as display_status
            FROM users u
            LEFT JOIN attendance a ON u.finger_id = a.finger_id AND a.date = ?
        """
        params = [selected_date]
        
        # Add department filter
        if selected_dept != 'All':
            query += " WHERE u.department = ?"
            params.append(selected_dept)
        
        query += " ORDER BY u.name"
        
        c.execute(query, params)
        rows = c.fetchall()
        
        # Count statistics
        present_count = 0
        absent_count = 0
        completed_count = 0
        checked_in_count = 0
        
        # Add to treeview and count statistics
        for row in rows:
            name, dept, date_val, check_in, check_out, status, hours, display_status = row
            
            # Format display values
            check_in_display = check_in.split()[1][:5] if check_in else "N/A"
            check_out_display = check_out.split()[1][:5] if check_out else "N/A"
            
            # Determine final status for display
            if status == 'completed':
                final_status = 'Completed'
                completed_count += 1
                present_count += 1
            elif status == 'checked_in':
                final_status = 'Checked In'
                checked_in_count += 1
                present_count += 1
            elif status is None:
                final_status = 'Absent'
                absent_count += 1
            else:
                final_status = status
                present_count += 1
            
            # Apply status filter
            if selected_status != 'All':
                if selected_status == 'Present' and final_status == 'Absent':
                    continue
                elif selected_status == 'Absent' and final_status != 'Absent':
                    continue
                elif selected_status == 'Checked In' and final_status != 'Checked In':
                    continue
                elif selected_status == 'Completed' and final_status != 'Completed':
                    continue
            
            # Add to treeview
            item_id = self.datewise_tree.insert('', 'end', values=(
                name, dept or 'N/A', selected_date, check_in_display, check_out_display, final_status, hours
            ))
            
            # Color code based on status
            if final_status == 'Absent':
                self.datewise_tree.set(item_id, 'Status', 'Absent')
            elif final_status == 'Completed':
                self.datewise_tree.set(item_id, 'Status', 'Completed')
            elif final_status == 'Checked In':
                self.datewise_tree.set(item_id, 'Status', 'Checked In')
        
        conn.close()
        
        # Update summary
        total_users = len(rows)
        summary_text = f"Date: {selected_date} | Total Users: {total_users} | Present: {present_count} | Absent: {absent_count} | Completed: {completed_count} | Checked In Only: {checked_in_count}"
        self.datewise_summary.config(text=summary_text)

    def clear_datewise_filter(self):
        """Clear date-wise filters"""
        self.date_entry.set_date(date.today())
        self.dept_filter_combo.set('All')
        self.status_filter_combo.set('All')
        self.filter_datewise_attendance()

    def export_datewise_report(self):
        """Export date-wise attendance report"""
        selected_date = self.date_entry.get_date().strftime('%Y-%m-%d')
        selected_dept = self.dept_filter_var.get()
        selected_status = self.status_filter_var.get()
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialname=f"attendance_report_{selected_date}.pdf"
            )
            
            if filename:
                self.generate_datewise_pdf_report(filename, selected_date, selected_dept, selected_status)
                messagebox.showinfo("Success", f"Date-wise report exported successfully to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export date-wise report: {str(e)}")

    def generate_datewise_pdf_report(self, filename, selected_date, selected_dept, selected_status):
        """Generate PDF report for date-wise attendance"""
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        
        # Get filtered data
        query = """
            SELECT u.name, u.department, a.date, a.check_in_time, a.check_out_time, a.status,
                   CASE WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL
                       THEN printf('%.2f', (julianday(a.check_out_time) - julianday(a.check_in_time)) * 24)
                       ELSE 'N/A' END as hours_worked,
                   CASE WHEN a.finger_id IS NULL THEN 'Absent' ELSE COALESCE(a.status, 'Present') END as display_status
            FROM users u
            LEFT JOIN attendance a ON u.finger_id = a.finger_id AND a.date = ?
        """
        params = [selected_date]
        
        if selected_dept != 'All':
            query += " WHERE u.department = ?"
            params.append(selected_dept)
        
        query += " ORDER BY u.name"
        
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        # Create PDF
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,
            textColor=colors.darkblue
        )
        
        story.append(Paragraph("Date-wise Attendance Report", title_style))
        story.append(Paragraph(f"Date: {selected_date}", styles['Normal']))
        story.append(Paragraph(f"Department Filter: {selected_dept}", styles['Normal']))
        story.append(Paragraph(f"Status Filter: {selected_status}", styles['Normal']))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Statistics
        present_count = sum(1 for row in rows if row[7] != 'Absent')
        absent_count = sum(1 for row in rows if row[7] == 'Absent')
        completed_count = sum(1 for row in rows if row[5] == 'completed')
        checked_in_count = sum(1 for row in rows if row[5] == 'checked_in')
        
        stats_data = [
            ['Metric', 'Count'],
            ['Total Users', str(len(rows))],
            ['Present', str(present_count)],
            ['Absent', str(absent_count)],
            ['Completed (Check-in + Check-out)', str(completed_count)],
            ['Checked In Only', str(checked_in_count)]
        ]
        
        stats_table = Table(stats_data)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Detailed attendance table
        story.append(Paragraph("Detailed Attendance Records", styles['Heading2']))
        
        table_data = [['Name', 'Department', 'Check-in', 'Check-out', 'Status', 'Hours']]
        
        for row in rows:
            name, dept, date_val, check_in, check_out, status, hours, display_status = row
            
            check_in_display = check_in.split()[1][:5] if check_in else "N/A"
            check_out_display = check_out.split()[1][:5] if check_out else "N/A"
            
            final_status = 'Completed' if status == 'completed' else 'Checked In' if status == 'checked_in' else 'Absent' if status is None else status
            
            table_data.append([
                name, dept or 'N/A', check_in_display, check_out_display, final_status, hours
            ])
        
        detail_table = Table(table_data)
        detail_table.setStyle(TableStyle([
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
        story.append(detail_table)
        
        doc.build(story)
       
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
        self.stats_text = tk.Text(stats_frame, height=12, width=80, bg='#f9f9f9')
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
       
        # Buttons frame
        users_buttons_frame = tk.Frame(list_frame, bg='white')
        users_buttons_frame.pack(pady=10)
       
        # Refresh users button
        refresh_users_button = tk.Button(users_buttons_frame, text="Refresh Users",
                                        command=self.refresh_users,
                                        bg='#4CAF50', fg='white', font=("Arial", 10, "bold"))
        refresh_users_button.pack(side=tk.LEFT, padx=5)
       
        # Delete user button
        delete_user_button = tk.Button(users_buttons_frame, text="Delete Selected User",
                                      command=self.delete_user,
                                      bg='#f44336', fg='white', font=("Arial", 10, "bold"))
        delete_user_button.pack(side=tk.LEFT, padx=5)
       
        # Edit user button
        edit_user_button = tk.Button(users_buttons_frame, text="Edit Selected User",
                                    command=self.edit_user,
                                    bg='#FF9800', fg='white', font=("Arial", 10, "bold"))
        edit_user_button.pack(side=tk.LEFT, padx=5)
       
        # Load users
        self.refresh_users()
   
    def refresh_users(self):
        """Refresh users list"""
        # Clear existing items
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
       
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT finger_id, name, age, department FROM users ORDER BY name")
        users = c.fetchall()
        conn.close()
       
        for user in users:
            self.users_tree.insert('', 'end', values=user)
   
    def delete_user(self):
        """Delete selected user"""
        selected_item = self.users_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a user to delete")
            return
       
        user_data = self.users_tree.item(selected_item)['values']
        finger_id = user_data[0]
        name = user_data[1]
       
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete user '{name}'?\nThis will also delete all their attendance records."):
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE finger_id = ?", (finger_id,))
            c.execute("DELETE FROM attendance WHERE finger_id = ?", (finger_id,))
            conn.commit()
            conn.close()
           
            messagebox.showinfo("Success", f"User '{name}' has been deleted")
            self.refresh_users()
   
    def edit_user(self):
        """Edit selected user"""
        selected_item = self.users_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a user to edit")
            return
       
        user_data = self.users_tree.item(selected_item)['values']
        finger_id, name, age, department = user_data
       
        # Create edit dialog
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit User")
        edit_window.geometry("400x300")
        edit_window.configure(bg='white')
       
        tk.Label(edit_window, text="Edit User Details", font=("Arial", 14, "bold"),
                bg='white').pack(pady=10)
       
        # Edit form
        form_frame = tk.Frame(edit_window, bg='white')
        form_frame.pack(pady=20)
       
        tk.Label(form_frame, text="Fingerprint ID:", bg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        id_label = tk.Label(form_frame, text=str(finger_id), bg='white', font=("Arial", 10, "bold"))
        id_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
       
        tk.Label(form_frame, text="Name:", bg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        name_var = tk.StringVar(value=name)
        name_entry = tk.Entry(form_frame, textvariable=name_var, width=20)
        name_entry.grid(row=1, column=1, padx=5, pady=5)
       
        tk.Label(form_frame, text="Age:", bg='white').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        age_var = tk.StringVar(value=str(age))
        age_entry = tk.Entry(form_frame, textvariable=age_var, width=20)
        age_entry.grid(row=2, column=1, padx=5, pady=5)
       
        tk.Label(form_frame, text="Department:", bg='white').grid(row=3, column=0, sticky='e', padx=5, pady=5)
        dept_var = tk.StringVar(value=department if department else "")
        dept_entry = tk.Entry(form_frame, textvariable=dept_var, width=20)
        dept_entry.grid(row=3, column=1, padx=5, pady=5)
       
        def save_changes():
            new_name = name_var.get().strip()
            new_age = age_var.get().strip()
            new_dept = dept_var.get().strip()
           
            if not new_name:
                messagebox.showerror("Error", "Name cannot be empty")
                return
           
            try:
                new_age = int(new_age) if new_age else None
            except ValueError:
                messagebox.showerror("Error", "Age must be a valid number")
                return
           
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("UPDATE users SET name = ?, age = ?, department = ? WHERE finger_id = ?",
                     (new_name, new_age, new_dept, finger_id))
            conn.commit()
            conn.close()
           
            messagebox.showinfo("Success", "User details updated successfully")
            edit_window.destroy()
            self.refresh_users()
       
        # Buttons
        buttons_frame = tk.Frame(edit_window, bg='white')
        buttons_frame.pack(pady=20)
       
        save_button = tk.Button(buttons_frame, text="Save Changes", command=save_changes,
                               bg='#4CAF50', fg='white', font=("Arial", 10, "bold"))
        save_button.pack(side=tk.LEFT, padx=5)
       
        cancel_button = tk.Button(buttons_frame, text="Cancel", command=edit_window.destroy,
                                 bg='#f44336', fg='white', font=("Arial", 10, "bold"))
        cancel_button.pack(side=tk.LEFT, padx=5)
   
    def register_user(self):
        """Register new user with fingerprint"""
        if not self.sensor_connected:
            messagebox.showerror("Error", "Fingerprint sensor not connected")
            return
       
        finger_id = self.fid_entry.get().strip()
        name = self.name_entry.get().strip()
        age = self.age_entry.get().strip()
        department = self.dept_entry.get().strip()
       
        if not finger_id or not name:
            messagebox.showerror("Error", "Fingerprint ID and Name are required")
            return
       
        try:
            finger_id = int(finger_id)
            if finger_id < 0 or finger_id > 127:
                messagebox.showerror("Error", "Fingerprint ID must be between 0 and 127")
                return
        except ValueError:
            messagebox.showerror("Error", "Fingerprint ID must be a valid number")
            return
       
        try:
            age = int(age) if age else None
        except ValueError:
            messagebox.showerror("Error", "Age must be a valid number")
            return
       
        # Check if finger ID already exists
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE finger_id = ?", (finger_id,))
        existing_user = c.fetchone()
        conn.close()
       
        if existing_user:
            messagebox.showerror("Error", f"Fingerprint ID {finger_id} is already registered to {existing_user[0]}")
            return
       
        # Start fingerprint enrollment
        self.reg_status.config(text="Place finger on sensor...", fg='blue')
        self.root.update()
       
        def enroll_finger():
            try:
                # Enroll fingerprint
                if self.finger.enroll_finger(finger_id):
                    # Save to database
                    conn = sqlite3.connect("users.db")
                    c = conn.cursor()
                    c.execute("INSERT INTO users (finger_id, name, age, department) VALUES (?, ?, ?, ?)",
                             (finger_id, name, age, department))
                    conn.commit()
                    conn.close()
                   
                    self.root.after(0, lambda: self.reg_status.config(text="User registered successfully!", fg='green'))
                    self.root.after(0, self.clear_registration_form)
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"User '{name}' registered successfully!"))
                else:
                    self.root.after(0, lambda: self.reg_status.config(text="Fingerprint enrollment failed", fg='red'))
            except Exception as e:
                self.root.after(0, lambda: self.reg_status.config(text=f"Error: {str(e)}", fg='red'))
       
        # Run enrollment in separate thread
        enroll_thread = threading.Thread(target=enroll_finger)
        enroll_thread.daemon = True
        enroll_thread.start()
   
    def clear_registration_form(self):
        """Clear registration form"""
        self.fid_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.age_entry.delete(0, tk.END)
        self.dept_entry.delete(0, tk.END)
   
    def toggle_scanning(self):
        """Toggle attendance scanning"""
        if not self.sensor_connected:
            messagebox.showerror("Error", "Fingerprint sensor not connected")
            return
       
        if not self.scanning:
            self.scanning = True
            self.scan_button.config(text="Stop Scanning", bg='#f44336')
            self.att_status.config(text="Scanning for fingerprints...", fg='blue')
            self.start_scanning_thread()
        else:
            self.scanning = False
            self.scan_button.config(text="Start Scanning", bg='#2196F3')
            self.att_status.config(text="Scanning stopped", fg='black')
   
    def start_scanning_thread(self):
        """Start fingerprint scanning in separate thread"""
        def scan_loop():
            while self.scanning:
                try:
                    if self.finger.get_image() == 0:  # Finger detected
                        if self.finger.image_2_tz(1) == 0:  # Convert image
                            if self.finger.finger_search() == 0:  # Search for match
                                finger_id = self.finger.finger_id
                                confidence = self.finger.confidence
                               
                                # Get user info
                                conn = sqlite3.connect("users.db")
                                c = conn.cursor()
                                c.execute("SELECT name, department FROM users WHERE finger_id = ?", (finger_id,))
                                user_info = c.fetchone()
                               
                                if user_info:
                                    name, department = user_info
                                    current_time = datetime.now()
                                    current_date = current_time.date()
                                   
                                    # Check if user already has attendance for today
                                    c.execute("SELECT id, check_in_time, check_out_time, status FROM attendance WHERE finger_id = ? AND date = ?",
                                             (finger_id, current_date))
                                    existing_record = c.fetchone()
                                   
                                    if existing_record:
                                        record_id, check_in_time, check_out_time, status = existing_record
                                        if status == 'checked_in':
                                            # Mark check-out
                                            c.execute("UPDATE attendance SET check_out_time = ?, status = 'completed' WHERE id = ?",
                                                     (current_time, record_id))
                                            message = f"Check-out: {name} ({department})"
                                            status_text = "Check-out recorded"
                                        else:
                                            message = f"Already completed: {name} ({department})"
                                            status_text = "Already marked for today"
                                    else:
                                        # Mark check-in
                                        c.execute("INSERT INTO attendance (finger_id, name, department, check_in_time, date, status) VALUES (?, ?, ?, ?, ?, ?)",
                                                 (finger_id, name, department, current_time, current_date, 'checked_in'))
                                        message = f"Check-in: {name} ({department})"
                                        status_text = "Check-in recorded"
                                   
                                    conn.commit()
                                    conn.close()
                                   
                                    self.root.after(0, lambda: self.att_status.config(text=status_text, fg='green'))
                                    self.root.after(0, lambda: messagebox.showinfo("Attendance", message))
                                    self.root.after(0, self.refresh_recent_attendance)
                                   
                                    # Brief pause after successful scan
                                    time.sleep(3)
                                else:
                                    conn.close()
                                    self.root.after(0, lambda: self.att_status.config(text="Fingerprint not registered", fg='red'))
                            else:
                                self.root.after(0, lambda: self.att_status.config(text="No match found", fg='orange'))
                        else:
                            self.root.after(0, lambda: self.att_status.config(text="Image processing failed", fg='red'))
                   
                    time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                except Exception as e:
                    self.root.after(0, lambda: self.att_status.config(text=f"Scanning error: {str(e)}", fg='red'))
                    time.sleep(1)
       
        self.scan_thread = threading.Thread(target=scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()
   
    def refresh_recent_attendance(self):
        """Refresh recent attendance display"""
        # Clear existing items
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
       
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("""SELECT name, department, check_in_time, check_out_time, status
                    FROM attendance 
                    WHERE date = date('now') 
                    ORDER BY check_in_time DESC""")
        records = c.fetchall()
        conn.close()
       
        for record in records:
            name, department, check_in, check_out, status = record
            check_in_display = check_in.split()[1][:5] if check_in else "N/A"
            check_out_display = check_out.split()[1][:5] if check_out else "N/A"
            status_display = "Completed" if status == "completed" else "Checked In"
           
            self.recent_tree.insert('', 'end', values=(name, department, check_in_display, check_out_display, status_display))
   
    def refresh_statistics(self):
        """Refresh attendance statistics"""
        self.stats_text.delete(1.0, tk.END)
       
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
       
        # Get today's statistics
        today = date.today()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
       
        c.execute("SELECT COUNT(DISTINCT finger_id) FROM attendance WHERE date = ?", (today,))
        present_today = c.fetchone()[0]
       
        c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'completed'", (today,))
        completed_today = c.fetchone()[0]
       
        c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'checked_in'", (today,))
        checked_in_only = c.fetchone()[0]
       
        # Get weekly statistics
        week_start = today - timedelta(days=today.weekday())
        c.execute("SELECT COUNT(DISTINCT finger_id) FROM attendance WHERE date >= ?", (week_start,))
        present_this_week = c.fetchone()[0]
       
        # Get monthly statistics
        month_start = today.replace(day=1)
        c.execute("SELECT COUNT(DISTINCT finger_id) FROM attendance WHERE date >= ?", (month_start,))
        present_this_month = c.fetchone()[0]
       
        # Get department-wise statistics for today
        c.execute("""SELECT u.department, COUNT(DISTINCT a.finger_id) as present_count
                    FROM users u
                    LEFT JOIN attendance a ON u.finger_id = a.finger_id AND a.date = ?
                    WHERE u.department IS NOT NULL
                    GROUP BY u.department""", (today,))
        dept_stats = c.fetchall()
       
        conn.close()
       
        # Display statistics
        stats_text = f"""
ATTENDANCE STATISTICS
{'='*50}

TODAY'S ATTENDANCE ({today.strftime('%Y-%m-%d')})
{'='*50}
Total Registered Users: {total_users}
Present Today: {present_today}
Absent Today: {total_users - present_today}
Completed (Check-in + Check-out): {completed_today}
Checked In Only: {checked_in_only}
Attendance Rate: {(present_today/total_users*100):.1f}% if total_users > 0 else 0%

WEEKLY STATISTICS
{'='*50}
Present This Week: {present_this_week}
Weekly Attendance Rate: {(present_this_week/total_users*100):.1f}% if total_users > 0 else 0%

MONTHLY STATISTICS
{'='*50}
Present This Month: {present_this_month}
Monthly Attendance Rate: {(present_this_month/total_users*100):.1f}% if total_users > 0 else 0%

DEPARTMENT-WISE ATTENDANCE (Today)
{'='*50}
"""
       
        for dept, count in dept_stats:
            if dept:
                stats_text += f"{dept}: {count} present\n"
       
        self.stats_text.insert(tk.END, stats_text)
   
    def export_pdf(self):
        """Export attendance report to PDF"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialname=f"attendance_report_{date.today().strftime('%Y_%m_%d')}.pdf"
            )
           
            if filename:
                self.generate_pdf_report(filename)
                messagebox.showinfo("Success", f"Report exported successfully to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
   
    def generate_pdf_report(self, filename):
        """Generate PDF report"""
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        
        # Get today's attendance data
        today = date.today()
        c.execute("""SELECT u.name, u.department, a.check_in_time, a.check_out_time, a.status,
                           CASE WHEN a.check_in_time IS NOT NULL AND a.check_out_time IS NOT NULL
                               THEN printf('%.2f', (julianday(a.check_out_time) - julianday(a.check_in_time)) * 24)
                               ELSE 'N/A' END as hours_worked
                    FROM users u
                    LEFT JOIN attendance a ON u.finger_id = a.finger_id AND a.date = ?
                    ORDER BY u.name""", (today,))
        attendance_data = c.fetchall()
        conn.close()
        
        # Create PDF
        doc = SimpleDocTemplate(filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,
            textColor=colors.darkblue
        )
        
        story.append(Paragraph("Daily Attendance Report", title_style))
        story.append(Paragraph(f"Date: {today.strftime('%Y-%m-%d')}", styles['Normal']))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary statistics
        total_users = len(attendance_data)
        present_users = sum(1 for row in attendance_data if row[2] is not None)
        completed_users = sum(1 for row in attendance_data if row[4] == 'completed')
        
        summary_data = [
            ['Metric', 'Count'],
            ['Total Users', str(total_users)],
            ['Present Today', str(present_users)],
            ['Absent Today', str(total_users - present_users)],
            ['Completed (Check-in + Check-out)', str(completed_users)],
            ['Attendance Rate', f"{(present_users/total_users*100):.1f}%" if total_users > 0 else "0%"]
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
        
        # Detailed attendance table
        story.append(Paragraph("Detailed Attendance", styles['Heading2']))
        
        table_data = [['Name', 'Department', 'Check-in', 'Check-out', 'Status', 'Hours Worked']]
        
        for row in attendance_data:
            name, dept, check_in, check_out, status, hours = row
            check_in_display = check_in.split()[1][:5] if check_in else "Absent"
            check_out_display = check_out.split()[1][:5] if check_out else "N/A"
            status_display = "Completed" if status == "completed" else "Checked In" if status == "checked_in" else "Absent"
            
            table_data.append([
                name, dept or 'N/A', check_in_display, check_out_display, status_display, hours
            ])
        
        attendance_table = Table(table_data)
        attendance_table.setStyle(TableStyle([
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
        
        story.append(attendance_table)
        doc.build(story)
   
    def export_csv(self):
        """Export attendance data to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=f"attendance_data_{date.today().strftime('%Y_%m_%d')}.csv"
            )
           
            if filename:
                conn = sqlite3.connect("users.db")
                c = conn.cursor()
                c.execute("""SELECT u.name, u.department, a.date, a.check_in_time, a.check_out_time, a.status
                            FROM users u
                            LEFT JOIN attendance a ON u.finger_id = a.finger_id
                            ORDER BY a.date DESC, u.name""")
                data = c.fetchall()
                conn.close()
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Name', 'Department', 'Date', 'Check-in Time', 'Check-out Time', 'Status'])
                    for row in data:
                        writer.writerow(row)
                
                messagebox.showinfo("Success", f"CSV exported successfully to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")

# Main application
def main():
    root = tk.Tk()
    app = FingerprintAttendanceGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()