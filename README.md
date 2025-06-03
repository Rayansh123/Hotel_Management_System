# Hotel Management System 🏨

A comprehensive **Hotel Booking and Management System** developed as part of a 4th-semester DBMS course project. It leverages **Streamlit** for the user interface and **MySQL** for database operations. 

**Note**-This is not a costumer/guest side platform for booking or any other operation; this is a hotlier/hotel management side system created for them to manage their bookings, staff, customer relations, rooms and tracking changes.

---

## 🛠 Tech Stack

- **Frontend / UI:** Streamlit (Python)  
- **Backend / Logic:** Python  
- **Database:** MySQL  
- **Mailing:** SMTP (for sending booking receipts via email)   

---

## ✨ Features

- 📋 Guest registration and room booking  
- 📄 Receipt generation in PDF format  
- 📧 Email confirmation with attached receipt  
- 🛏️ Room availability and booking status tracking  
- 👤 Staff and CRM management  
- 🏅 Loyalty points system  
- 🔁 Database triggers, events, and procedures to automate updates and actions  

---
## 🔄 Demo Workflow & Feature Walkthrough (Hotelier-Facing System)

This Hotel Management System is designed for internal use by **hotel staff and administrators** to streamline operations such as guest registration, room booking, staff CRM, and automated loyalty rewards — all through a single dashboard built with **Streamlit** and backed by a **MySQL database**.

---

### 🧑‍💼 1. Guest Registration
- Hotel staff inputs guest details like name, email, and phone number.
- If the guest already exists (based on email), the system fetches their CRM record.
- New guests are automatically added to the `CRM` table with 0 loyalty points (via trigger).

---

### 🛏 2. Room Booking
- Select room, check-in & check-out dates, guest id, payment method.
- The system:
  - Verifies no overlapping booking exists using a trigger.
  - Calculates total amount based on stay duration and room price.
  - Applies ₹100 **loyalty discount** if eligible.
  - Sets room status to `Booked` automatically.
- **Loyalty points** are updated after every second paid stay (see logic below).
- On booking deletion or guest deletion, associated rooms are freed automatically.

---

### 💎 3. Loyalty Points Logic

#### ✅ How it Works:
- Each time a booking is made with payment (`Cash`, `UPI`, `Credit Card`):
  - A counter is incremented for that guest.
  - If the number of completed **paid stays becomes even (2, 4, 6...)**, the guest is awarded **100 loyalty points**.

#### 🔁 Discount Application:
- During a future booking, if:
  - Guest has **100 loyalty points**, and
  - This is an **odd-numbered** paid stay (3rd, 5th, 7th...),
  - Then ₹100 is automatically **deducted** from the total booking amount.
  - Loyalty points are reset to 0 after use.

```sql
-- Trigger Logic for Points Addition:
IF paid_stays % 2 = 0 AND paid_stays > 0 THEN
    UPDATE CRM SET Loyalty_Points = 100;

-- Trigger Logic for Discount:
IF (paid_stays + 1) % 2 = 1 AND current_points = 100 THEN
    SET NEW.Total_Amount = NEW.Total_Amount - 100;
    UPDATE CRM SET Loyalty_Points = 0;
```
---
### 🧾 4. Receipt & Email Integration
After booking, the system:
- 📄 Generates a PDF receipt containing full booking details.
- 📧 Sends the receipt to the guest via email (SMTP setup required in `.env`).

---

### 🏨 5. Room Status Management
- 🟢 Booked rooms are marked automatically via trigger.
- ⏰ A daily scheduled event checks for expired bookings and frees up rooms.
- 🧹 Manual room freeing is also triggered on:
  - Booking cancellation
  - Guest deletion

---

### 🗃 6. CRM Panel
Staff can view and track:
- Guest details 
- Loyalty points    

✅ This helps improve customer experience and enables loyalty-based targeting.

---

### ⚙️ 7. Automation (SQL Triggers & Events)
The system uses a combination of **triggers**, **procedures**, and **scheduled events** to ensure:

- 🚫 No double booking (`prevent_overlapping_bookings`)
- 🟢 Room status updated on booking/cancellation
- 🔁 Daily room status cleanup (`daily_room_cleanup`)
- 🎁 Loyalty point tracking and discount application
- 🧾 Receipt generation with point deductions

---
### 📊 Interactive Tables Overview in Streamlit UI:

The Streamlit interface presents key tables from the database in a clean, user-friendly way for hotel staff. These views support sorting, filtering, and exporting — making management quick and efficient.

---

#### 👤 1. Guest Directory (in Guest Registration Tab)
- Displays all registered guests with details such as:
  - Name, Email, Phone Number, Gender, Address, ID Proof
- **Interactive Features**:
  - 🔍 **Search** by name, email, phone, or any field
  - ↕️ **Sort alphabetically or numerically** by any column
  - 🎯 **Filter** guests based on custom criteria
  - 📤 **Download table as CSV** for backups or reports

---

#### 📆 2. Active Bookings (in Room Booking Tab)
- Shows all active and future bookings with:
  - Guest Name, Room Number, Check-in/Check-out Dates, Payment Method, Total Amount
- **Key Features**:
  - 🔄 Automatically updated upon new bookings
  - ❌ Option to cancel bookings (also frees up rooms)
  - ↕️ Sort by dates, payment methods, or total amount
  - 🔍 Search by guest name or room number
  - 📤 Export as CSV

---

#### 🛏️ 3. Available Rooms (in Room Booking Tab)
- View of all rooms currently **not booked**, showing:
  - Room Number, Type, Price, Status
- **Interactive Options**:
  - 📊 Quickly assess room inventory
  - ↕️ Sort by price or room type
  - 🔍 Filter rooms by type or price range

---

#### 🧑‍💼 4. Staff Directory (in Staff Management Tab)
- Lists hotel staff members with:
  - Name, Role, Email, Phone Number
- **Management Utilities**:
  - ➕ Add or remove staff entries
  - ↕️ Sort by name or role
  - 🔍 Search staff by name, role, or contact
  - 📤 Export for HR or audit purposes

---

#### 💎 5. Customer Loyalty Program (in CRM View Tab)
- Customer Relationship Management view tied to guest data:
  - Guest ID, Loyalty Points, Booking History, Return Visit Frequency
- **CRM Use-Cases**:
  - 🎁 Track **loyalty rewards eligibility**
  - 📈 Identify high-returning guests for special offers
  - 🔍 Search guests by ID or filter based on loyalty points
  - 📤 Export for marketing or analytics

---

### 💡 Additional UI Highlights
- ✅ **Real-time data updates** on every booking, cancellation, or registration.
- 📎 All tables support **CSV export** to ensure data portability and offline access.
- 📎 **Table-level controls** include:
  - 🔍 A global **search bar**
  - 📑 **Column visibility toggles** to show/hide specific columns
  - 🖥️ **Fullscreen mode** toggle for detailed inspection
- 📌 **Per-column controls** include:
  - ↕️ **Sort Ascending / Descending**
  - 📏 **Autosize column**
  - 📌 **Pin column** (left or right)
  - ❌ **Hide column**
  - 💱 **Format column** (options include):
    - Automatic
    - Localized
    - Plain
    - Compact
    - Dollar, Euro
    - Percent
    - Scientific
    - Accounting
---

📌 **Note**: This project is **backend-focused** — there is **no public-facing frontend** for guests.  
It’s built for **hotels to operate, monitor, and manage their systems internally**.

---

## 🚀 Getting Started (Run it Yourself)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Rayansh123/Hotel_Management_System.git
   ```

2. **Set up your MySQL database:**

   - Use the `Database.sql` file in the repo to create the schema and populate initial data.

3. **Create your `.env` file:**

   Create a `config.env` file in the root folder with your DB & other credentials:

   ```env
   DB_HOST=localhost
   DB_USER=yourusername
   DB_PASSWORD=yourpassword
   DB_NAME=hotel_management

   EMAIL_ADDRESS=youremailaddress_using_which_you_generated_app_password
   EMAIL_PASSWORD=a_16_didgit_app_password #i used gmail app password
   SMTP_SERVER=smtp.gmail.com(in case it's google that you're using)
   SMTP_PORT=port_number(587)
   
   HOTEL_NAME="yourhotelname"
   HOTEL_ADDRESS=yourhoteladdress
   HOTEL_PHONE=+91 0000000000
   ```

4. **Run the app:**

   ```bash
   streamlit run app.py
   ```

---

## 🧠 Project Background

This project was built as an academic exercise to demonstrate mastery over **relational databases**, **SQL procedures/triggers**, and practical **Python-based web app development**. It mimics real-world hotel operations to simulate a functional management system with automation and user interaction.

---

> Feel free to fork, explore, or extend the project as you like!
