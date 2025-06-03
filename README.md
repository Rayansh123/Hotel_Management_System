# Hotel Management System 🏨

A comprehensive **Hotel Booking and Management System** developed as part of a 4th-semester DBMS course project. It leverages **Streamlit** for the user interface and **MySQL** for database operations.

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
