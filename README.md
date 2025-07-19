# Fingerprint Attendance System with Raspberry Pi 4 + R307

This is a **GUI-based biometric attendance system** developed in Python for **Raspberry Pi 4** using the **R307 Fingerprint Sensor**. It allows user registration, real-time attendance logging (check-in/check-out), data filtering, and report generation (PDF/CSV). A clean Tkinter-based interface is provided for usability.

---

##  Features

1. **Fingerprint-based login & attendance**
2.  **User registration** with Name, Age, Department, and Finger ID
3.  **Date-wise attendance view** with filtering by Department & Status
4.  **Live statistics & reports**
5.  Export to **PDF and CSV**
6.  Admin controls to **edit or delete users**
7.  Built-in SQLite database for lightweight storage
8.  Background threading for smooth scanning

---

##  Components Required

| Component                        | Quantity |
|----------------------------------|----------|
| Raspberry Pi 4 Model B           | 1        |
| Fingerprint Sensor Module R307   | 1        |
| Jumper Wires                     | ~5       |
| Breadboard (optional)            | 1        |
| MicroSD Card (32GB+)             | 1        |
| Power Supply (5V 2.5A)           | 1        |
| Monitor + HDMI + Keyboard        | 1        |
| *(Optional)* External LCD Display| 1        |

---

##  Raspberry Pi Setup

### 1. Install Raspberry Pi OS
- Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
- Recommended: Raspberry Pi OS with Desktop

### 2. Enable Serial Communication
```bash
sudo raspi-config
```
- Go to Interface Options → Serial

- Disable login shell over - serial

- Enable serial interface
### 3. Connect R307 to Pi GPIO

| **R307 Pin** | **Raspberry Pi GPIO Pin** | **Function**        |
|--------------|----------------------------|---------------------|
| **VCC**      | **5V (Pin 2 or Pin 4)**     | Power Supply        |
| **GND**      | **GND (Pin 6 or Pin 9)**    | Ground              |
| **TX**       | **GPIO 15 (UART RX, Pin 10)** | R307 Transmit → Pi Receive |
| **RX**       | **GPIO 14 (UART TX, Pin 8)** | R307 Receive ← Pi Transmit |
### 4. Usage
1. Clone the project or transfer files to your Pi.

2. Connect the R307 sensor properly.

3. Run the main program:
```bash
python3 Main.py
```
### 5. Modules Overview
- Register User: Captures and saves fingerprint + user data.

![User Registration](https://github.com/gpratik143/PiScan-Attendance/blob/main/Outputs/Attendance.png)
- Mark Attendance: Allows check-in/check-out with fingerprint match.

![Attendance](https://github.com/gpratik143/PiScan-Attendance/blob/main/Outputs/MarkAttendance.png)
- Date-wise Attendance: Filter logs by date, department, or status.

![Date Wise Attendance](https://github.com/gpratik143/PiScan-Attendance/blob/main/Outputs/DateWiseFilter.png)
- Reports: View attendance stats and generate PDF or CSV reports.

![Report](https://github.com/gpratik143/PiScan-Attendance/blob/main/Outputs/Statistics.png)
- User Management: Edit or delete registered users.

### 5. Database Structure (users.db)
Stores biometric-registered user profiles.
###  `users` Table

| **Field**     | **Type**  | **Description**                     |
|---------------|-----------|-------------------------------------|
| `finger_id`   | INTEGER   | Unique ID assigned to each fingerprint (Primary Key) |
| `name`        | TEXT      | Full name of the user               |
| `age`         | INTEGER   | Age of the user                     |
| `department`  | TEXT      | Department or group the user belongs to |

###  `attendance` Table

Logs daily attendance status for each registered user.

| **Field**        | **Type**  | **Description**                                    |
|------------------|-----------|----------------------------------------------------|
| `id`             | INTEGER   | Auto-incremented primary key                       |
| `finger_id`      | INTEGER   | References `users.finger_id`                      |
| `check_in_time`  | TEXT      | Timestamp of check-in (`YYYY-MM-DD HH:MM:SS`)     |
| `check_out_time` | TEXT      | Timestamp of check-out (`YYYY-MM-DD HH:MM:SS`)    |
| `date`           | TEXT      | Attendance date (`YYYY-MM-DD`)                    |
| `status`         | TEXT      | Status string (`checked_in`, `completed`, `absent`) |

### 6. Exports & Reports


The system provides robust options to export attendance data for analysis and reporting:



###  PDF Reports (via ReportLab)

PDF generation is handled using the **ReportLab** library, supporting high-quality, printable reports.

####  Available PDF Exports:
- **Daily Attendance Summary**
  - Shows check-in/check-out times
  - Status: `Checked In`, `Completed`, `Absent`
  - Worked hours calculation
- **Date-wise Attendance Report**
  - Filter by date, department, or status
  - Includes summary statistics (present, absent, completed)
  - Exported with timestamp and filters used

Each PDF report includes:
- Date and time of generation
- Attendance statistics summary
- Detailed table of users with attendance info



###  CSV Export

CSV files are exported in a format compatible with Excel, Google Sheets, and other spreadsheet tools.

####  CSV Contents:
- `Name`
- `Department`
- `Date`
- `Check-in Time`
- `Check-out Time`
- `Status` (e.g., `checked_in`, `completed`, `absent`)

####  Export Options:
- Export **all data**
- Easily filter or sort by department or date range externally
- Useful for archival, HR processing, or third-party integration

## 7. Troubleshooting

Common issues and their solutions when working with the fingerprint attendance system:

| Issue                    | Solution                                                                 |
|--------------------------|--------------------------------------------------------------------------|
| Sensor not detected      | Check wiring, restart Raspberry Pi, and ensure `/dev/serial0` is used    |
| Permission error         | Run the application with elevated privileges: `sudo python3 Main.py`    |
| GUI freezes              | Make sure fingerprint scanning is handled in background threads          |
| ImportError              | Use `pip3 install <missing_package>` to install required Python modules  |

Additional tips:
- Confirm the sensor is properly connected: TX ↔ RX
- Verify UART is enabled via `raspi-config`
- Run `ls /dev/serial*` to confirm the serial interface exists

## 8. Author

Pratik Gupta  
B.Tech CSE - Jaypee University of Engineering & Technology (JUET), Guna  
GitHub: [https://github.com/gpratik143](https://github.com/gpratik143)  
Email: gpratik154@gmail.com

## 9. License

This project is intended for educational and academic use only.  
For commercial or other types of usage, please request permission from the author.
