import streamlit as st
from db_utils import run_query
import pandas as pd

# Page Config
st.set_page_config(layout="wide", page_title="Hotel Management System")

def main():
    tab1, tab2, tab3, tab4 = st.tabs(["Guest Registration", "Room Booking", "Staff Management", "CRM View"])
    
    # TAB 1: Guest Registration
    with tab1:
        st.header("Guest Registration")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("guest_form", clear_on_submit=True):
                st.subheader("Register New Guest")
                name = st.text_input("Full Name*")
                email = st.text_input("Email*")
                phone = st.text_input("Phone*", max_chars=10)
                address = st.text_area("Address")
                
                if st.form_submit_button("Register Guest"):
                    if not all([name, email, phone]):
                        st.error("Fields marked with * are required!")
                    elif len(phone) != 10:
                        st.error("Phone must be 10 digits")
                    else:
                        run_query(
                            "INSERT INTO Guest (Name, Email, Phone, Address) VALUES (%s, %s, %s, %s)",
                            (name, email, phone, address),
                            fetch=False
                        )
                        st.success(f"Guest {name} registered successfully!")
        
        with col2:
            st.subheader("All Guests")
            guests = run_query("SELECT * FROM Guest ORDER BY Guest_ID DESC")
            st.dataframe(pd.DataFrame(guests), use_container_width=True)
    
    # TAB 2: Room Booking (with payment method dropdown)
    with tab2:
        st.header("Room Booking")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("booking_form"):
                st.subheader("New Booking")
                guest_id = st.number_input("Guest ID*", min_value=1, step=1)
                room_id = st.number_input("Room ID*", min_value=1, step=1)
                check_in = st.date_input("Check-In Date*")
                check_out = st.date_input("Check-Out Date*", min_value=check_in)
                payment_method = st.selectbox(
                    "Payment Method",
                    ["Pending", "Credit Card", "Cash", "UPI"],
                    index=0  # Default to "Pending"
                )
                
                if st.form_submit_button("Confirm Booking"):
                    # Check if room exists
                    room_exists = run_query(
                        "SELECT 1 FROM Room WHERE Room_ID = %s", 
                        (room_id,)
                    )
                    
                    if not room_exists:
                        st.error("Room ID does not exist!")
                    else:
                        # Check availability
                        is_available = run_query(
                            """SELECT 1 FROM Room 
                            WHERE Room_ID = %s 
                            AND Status = 'Available'
                            AND Room_ID NOT IN (
                                SELECT Room_ID FROM Booking 
                                WHERE Check_Out_Date > %s 
                                AND Check_In_Date < %s
                            )""",
                            (room_id, check_in, check_out)
                        )
                        
                        if not is_available:
                            st.error(f"Room {room_id} is not available for these dates!")
                        else:
                            try:
                                run_query(
                                    "INSERT INTO Booking (Guest_ID, Room_ID, Check_In_Date, Check_Out_Date, Payment_Method) "
                                    "VALUES (%s, %s, %s, %s, %s)",
                                    (guest_id, room_id, check_in, check_out, payment_method),
                                    fetch=False
                                )
                                st.success(f"Room {room_id} booked successfully!")
                                st.rerun()  # Refresh data
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
        
        with col2:
            st.subheader("Current Status")
            
            st.write("**Available Rooms**")
            rooms = run_query("""
                SELECT r.Room_ID, r.Room_Type, r.Price 
                FROM Room r
                WHERE r.Status = 'Available'
                AND r.Room_ID NOT IN (
                    SELECT Room_ID FROM Booking 
                    WHERE Check_Out_Date > CURDATE()
                )
            """)
            st.dataframe(pd.DataFrame(rooms), use_container_width=True)
            
            st.write("**Active Bookings**")
            bookings = run_query("""
                SELECT b.Booking_ID, g.Name, r.Room_ID, r.Room_Type, 
                       b.Check_In_Date, b.Check_Out_Date, b.Payment_Method
                FROM Booking b
                JOIN Guest g ON b.Guest_ID = g.Guest_ID
                JOIN Room r ON b.Room_ID = r.Room_ID
                WHERE b.Check_Out_Date > CURDATE()
                ORDER BY b.Check_In_Date
            """)
            st.dataframe(pd.DataFrame(bookings), use_container_width=True)
    
    # TAB 3: Staff Management
    with tab3:
        st.header("Staff Management")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("staff_form", clear_on_submit=True):
                st.subheader("Add Staff Member")
                name = st.text_input("Name*")
                role = st.selectbox("Role*", ["Receptionist", "Manager", "Housekeeping"])
                contact = st.text_input("Phone*", max_chars=10)
                
                if st.form_submit_button("Add Staff"):
                    if not all([name, contact]):
                        st.error("Required fields missing!")
                    elif len(contact) != 10:
                        st.error("Phone must be 10 digits")
                    else:
                        run_query(
                            "INSERT INTO Staff (Name, Role, Contact) VALUES (%s, %s, %s)",
                            (name, role, contact),
                            fetch=False
                        )
                        st.success("Staff added successfully!")
        
        with col2:
            st.subheader("All Staff")
            staff = run_query("SELECT * FROM Staff ORDER BY Staff_ID DESC")
            st.dataframe(pd.DataFrame(staff), use_container_width=True)
    
    # TAB 4: CRM View
    with tab4:
        st.header("Customer Loyalty Program")
        crm_data = run_query("""
            SELECT g.Guest_ID, g.Name, g.Email, c.Loyalty_Points
            FROM CRM c
            JOIN Guest g ON c.Guest_ID = g.Guest_ID
            ORDER BY c.Loyalty_Points DESC
        """)
        st.dataframe(pd.DataFrame(crm_data), use_container_width=True)

if __name__ == "__main__":
    main()

import streamlit as st
from db_utils import run_query
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import tempfile
import os
from dotenv import load_dotenv
from datetime import datetime

# --- Minimal PDF & Email Configuration ---
load_dotenv("config.env")

HOTEL_NAME="Farn Hotel & Resorts"

def generate_secure_receipt(booking_id):
    """Minimal PDF generator with essential booking data"""
    booking = run_query("""
        SELECT b.Booking_ID, g.Name, g.Email, r.Room_Type, 
               b.Check_In_Date, b.Check_Out_Date, b.Total_Amount
        FROM Booking b
        JOIN Guest g ON b.Guest_ID = g.Guest_ID
        JOIN Room r ON b.Room_ID = r.Room_ID
        WHERE b.Booking_ID = %s
    """, (booking_id,))
    
    if not booking:
        return None, None
    
    booking = booking[0]
    
    # Basic PDF with security
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Content with minimal styling
    pdf.cell(0, 10, "Booking Receipt", 0, 1, 'C')
    pdf.ln(8)
    
    details = [
        ("Booking ID:", booking['Booking_ID']),
        ("Guest:", booking['Name']),
        ("Room:", booking['Room_Type']),
        ("Check-In:", str(booking['Check_In_Date'])),
        ("Check-Out:", str(booking['Check_Out_Date'])),
        ("Total:", f"₹{booking['Total_Amount']}")
    ]
    
    for label, value in details:
        pdf.cell(40, 10, label, 0, 0)
        pdf.cell(0, 10, str(value), 0, 1)
    
    # Secure temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name, booking['Email']

def send_secure_email(to_email, pdf_path):
    """Minimal email with TLS security + temp file cleanup"""
    msg = MIMEMultipart()
    msg['Subject'] = "Your Booking Confirmation"
    msg['From'] = os.getenv("EMAIL_ADDRESS")  
    msg['To'] = to_email

    msg.attach(MIMEText(
        "Please find your booking receipt attached.\n\n"
        "Thank you for choosing our hotel!\n\n"
        "This is an automated message.",
        'plain'
    ))

    try:
        # Attach PDF
        with open(pdf_path, 'rb') as f:
            pdf_attach = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attach.add_header(
                'Content-Disposition',
                'attachment',
                filename="Booking_Receipt.pdf"
            )
            msg.attach(pdf_attach)

        # Send Email
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(
                os.getenv("EMAIL_ADDRESS"),   # ✅ make sure this matches config.env
                os.getenv("EMAIL_PASSWORD")
            )
            server.send_message(msg)

    finally:
        # ✅ Delete temp PDF after sending
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


# --- Main Application ---
def main():
    # Page Configuration
    st.set_page_config(
        layout="wide", 
        page_title=f"{HOTEL_NAME} Management System",
        page_icon="🏨",
        menu_items={
            'About': f"### {HOTEL_NAME}\nManagement System v1.0"
        }
    )
    
    # Custom CSS
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: #f9f9f9;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 5px;
            padding: 5px;
            background: #f0f2f6;
            border-radius: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 8px 20px;
            background: white;
            border-radius: 5px 5px 0 0;
            border: 1px solid #e0e0e0;
        }}
        .stTabs [aria-selected="true"] {{
            background: #0d6efd;
            color: white;
            border-color: #0d6efd;
        }}
        .receipt-card {{
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metric-card {{
            background: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 Guest Registration", 
        "🛎️ Room Booking", 
        "👨‍💼 Staff Management", 
        "📊 Reports"
    ])
    
    # TAB 1: Guest Registration
    with tab1:
        st.header("Guest Management")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("guest_form", clear_on_submit=True):
                st.subheader("Register New Guest")
                
                name = st.text_input("Full Name*", placeholder="John Doe")
                email = st.text_input("Email*", placeholder="john@example.com")
                phone = st.text_input("Phone*", max_chars=10, placeholder="9876543210")
                address = st.text_area("Address", placeholder="Street, City, State")
                
                submitted = st.form_submit_button("Register Guest")
                if submitted:
                    if not all([name, email, phone]):
                        st.error("Please fill all required fields (*)")
                    elif len(phone) != 10 or not phone.isdigit():
                        st.error("Phone must be 10 digits")
                    else:
                        try:
                            run_query(
                                """INSERT INTO Guest 
                                (Name, Email, Phone, Address) 
                                VALUES (%s, %s, %s, %s)""",
                                (name, email, phone, address),
                                fetch=False
                            )
                            st.success(f"✅ Guest {name} registered successfully!")
                            st.balloons()
                        except Exception as e:
                            if "Duplicate entry" in str(e):
                                st.error("❌ Email already registered")
                            else:
                                st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.subheader("Guest Directory")
            
            # Search functionality
            search_col1, search_col2 = st.columns(2)
            with search_col1:
                search_term = st.text_input("Search by name or email")
            
            # Query with search
            query = "SELECT * FROM Guest"
            params = []
            if search_term:
                query += " WHERE Name LIKE %s OR Email LIKE %s"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            query += " ORDER BY Guest_ID DESC"
            
            guests = run_query(query, params or None)
            
            if guests:
                df = pd.DataFrame(guests)
                
                # Enhanced dataframe display
                st.dataframe(
                    df.style.highlight_max(subset=['Guest_ID'], color='#d4edda'),
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )
                
                # Export option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Export as CSV",
                    data=csv,
                    file_name="guests.csv",
                    mime="text/csv"
                )
            else:
                st.info("No guests found")

    # TAB 2: Room Booking
    with tab2:
        st.header("Room Reservations")
        
        # Step 1: Guest Verification
        st.markdown("### Step 1: Find Guest")
        guest_col1, guest_col2 = st.columns(2)
        with guest_col1:
            guest_email = st.text_input("Search by Email", key="guest_email")
        with guest_col2:
            guest_phone = st.text_input("Search by Phone", max_chars=10, key="guest_phone")
        
        guest_id = None
        if guest_email or guest_phone:
            query = "SELECT * FROM Guest WHERE "
            params = []
            if guest_email:
                query += "Email = %s"
                params.append(guest_email)
            if guest_phone:
                if guest_email:
                    query += " OR "
                query += "Phone = %s"
                params.append(guest_phone)
            
            guests = run_query(query, params)
            
            if guests:
                guest = guests[0]
                guest_id = guest['Guest_ID']
                
                st.success(f"""
                **Guest Found:**  
                🆔 {guest['Guest_ID']}  
                👤 {guest['Name']}  
                📧 {guest['Email']}  
                📞 {guest['Phone']}
                """)
            else:
                st.warning("No matching guest found")
                st.stop()
        else:
            st.info("Please search for an existing guest")
            st.stop()
        
        # Step 2: Room Selection
        st.markdown("### Step 2: Booking Details")
        with st.form("booking_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                room_id = st.number_input("Room Number*", min_value=1, step=1)
                check_in = st.date_input("Check-In*", min_value=datetime.now().date())
                
            with col2:
                check_out = st.date_input("Check-Out*", min_value=check_in + pd.Timedelta(days=1))
                payment_method = st.selectbox(
                    "Payment Method*",
                    ["Pending", "Credit Card", "UPI", "Cash", "Bank Transfer"]
                )
            
            special_requests = st.text_area("Special Requests")
            
            submitted = st.form_submit_button("Confirm Booking", type="primary")
            if submitted:
                # Validate dates
                if check_out <= check_in:
                    st.error("Check-out date must be after check-in date")
                    st.stop()
                
                # Check room availability
                available = run_query("""
                    SELECT r.Room_ID, r.Room_Type, r.Price 
                    FROM Room r
                    WHERE r.Room_ID = %s
                    AND r.Status = 'Available'
                    AND NOT EXISTS (
                        SELECT 1 FROM Booking 
                        WHERE Room_ID = r.Room_ID
                        AND Check_Out_Date > %s
                        AND Check_In_Date < %s
                    )
                """, (room_id, check_in, check_out))
                
                if not available:
                    st.error("❌ Selected room is not available for these dates")
                    st.stop()
                
                try:
                    # Create booking
                    run_query(
                        """INSERT INTO Booking 
                        (Guest_ID, Room_ID, Check_In_Date, Check_Out_Date, Payment_Method, Special_Requests)
                        VALUES (%s, %s, %s, %s, %s, %s)""",
                        (guest_id, room_id, check_in, check_out, payment_method, special_requests),
                        fetch=False
                    )
                    
                    # Get the new booking ID
                    new_booking = run_query("SELECT LAST_INSERT_ID() AS id")[0]['id']
                    
                    # Generate receipt
                    receipt_path, guest_email = generate_secure_receipt(new_booking)
                    
                    # Show success UI
                    st.success("🎉 Booking confirmed!")
                    st.balloons()
                    
                    # Create receipt download card
                    with st.expander("Booking Receipt", expanded=True):
                        st.markdown(f"""
                        <div class='receipt-card'>
                            <h3 style='color: #0d6efd;'>{HOTEL_NAME}</h3>
                            <p>Booking ID: <strong>{new_booking}</strong></p>
                            <p>Guest: <strong>{guest_name}</strong></p>
                            <p>Room: <strong>{available[0]['Room_Type']}</strong></p>
                            <p>Dates: <strong>{check_in} to {check_out}</strong></p>
                            <p>Payment: <strong>{payment_method}</strong></p>
                            
                            <div style='margin-top: 20px;'>
                                <a href='data:application/pdf;base64,{open(receipt_path, "rb").read().encode("base64").decode()}' 
                                   download='{HOTEL_NAME}_Booking_{new_booking}.pdf'>
                                   <button style='background-color: #0d6efd; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;'>
                                   Download Receipt
                                   </button>
                                </a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Send email receipt
                    with st.spinner("Sending email confirmation..."):
                        try:
                            if send_secure_email(guest_email, receipt_path):
                                st.success("📧 Email receipt sent to guest")
                        except Exception as e:
                            st.warning(f"⚠️ Email could not be sent: {str(e)}")
                    
                except Exception as e:
                    st.error(f"❌ Booking failed: {str(e)}")
        
        # Current Status Section
        st.markdown("---")
        st.subheader("Current Hotel Status")
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            occupied = run_query("SELECT COUNT(*) FROM Booking WHERE Check_Out_Date > CURDATE()")[0]['COUNT(*)']
            total_rooms = run_query("SELECT COUNT(*) FROM Room")[0]['COUNT(*)']
            st.metric("Occupancy", f"{occupied}/{total_rooms} Rooms", delta=f"{round(occupied/total_rooms*100)}%")
        
        with col2:
            arrivals = run_query("""
                SELECT COUNT(*) FROM Booking 
                WHERE Check_In_Date = CURDATE()
            """)[0]['COUNT(*)']
            st.metric("Today's Arrivals", arrivals)
        
        with col3:
            departures = run_query("""
                SELECT COUNT(*) FROM Booking 
                WHERE Check_Out_Date = CURDATE()
            """)[0]['COUNT(*)']
            st.metric("Today's Departures", departures)
        
        # Room Availability
        st.markdown("#### Room Availability")
        rooms = run_query("""
            SELECT 
                r.Room_ID,
                r.Room_Type,
                r.Price,
                r.Status,
                CASE 
                    WHEN b.Booking_ID IS NOT NULL THEN CONCAT(g.Name, ' (', b.Check_In_Date, ' to ', b.Check_Out_Date, ')')
                    ELSE 'Available'
                END AS Status_Detail
            FROM Room r
            LEFT JOIN Booking b ON r.Room_ID = b.Room_ID AND b.Check_Out_Date > CURDATE()
            LEFT JOIN Guest g ON b.Guest_ID = g.Guest_ID
            ORDER BY r.Room_ID
        """)
        
        if rooms:
            st.dataframe(
                pd.DataFrame(rooms).style.applymap(
                    lambda x: 'background-color: #d4edda' if x == 'Available' else 'background-color: #f8d7da',
                    subset=['Status']
                ),
                use_container_width=True,
                height=400
            )
        else:
            st.info("No room data available")

    # TAB 3: Staff Management
    with tab3:
        st.header("Staff Administration")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("staff_form", clear_on_submit=True):
                st.subheader("Add Staff Member")
                
                name = st.text_input("Full Name*")
                role = st.selectbox(
                    "Position*",
                    ["Receptionist", "Manager", "Housekeeping", "Chef", "Maintenance"]
                )
                contact = st.text_input("Phone*", max_chars=10)
                salary = st.number_input("Monthly Salary (₹)", min_value=0, step=1000)
                
                submitted = st.form_submit_button("Add Staff")
                if submitted:
                    if not all([name, contact, role]):
                        st.error("Please fill all required fields")
                    elif len(contact) != 10 or not contact.isdigit():
                        st.error("Phone must be 10 digits")
                    else:
                        try:
                            run_query(
                                """INSERT INTO Staff 
                                (Name, Role, Contact, Salary) 
                                VALUES (%s, %s, %s, %s)""",
                                (name, role, contact, salary),
                                fetch=False
                            )
                            st.success(f"✅ {role} {name} added successfully!")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        with col2:
            st.subheader("Staff Directory")
            
            # Staff search
            search_term = st.text_input("Search staff by name or role")
            
            query = "SELECT * FROM Staff"
            params = []
            if search_term:
                query += " WHERE Name LIKE %s OR Role LIKE %s"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            query += " ORDER BY Staff_ID DESC"
            
            staff = run_query(query, params or None)
            
            if staff:
                df = pd.DataFrame(staff)
                
                # Enhanced display
                st.dataframe(
                    df.style.bar(subset=['Salary'], color='#5fba7d'),
                    use_container_width=True,
                    height=500,
                    hide_index=True
                )
                
                # Staff actions
                selected = st.multiselect(
                    "Select staff for actions",
                    options=[f"{s['Name']} ({s['Role']})" for s in staff]
                )
                
                if selected and st.button("Remove Selected", type="secondary"):
                    names = [s.split(" (")[0] for s in selected]
                    for name in names:
                        run_query(
                            "DELETE FROM Staff WHERE Name = %s",
                            (name,),
                            fetch=False
                        )
                    st.success(f"Removed {len(selected)} staff members")
                    st.rerun()
            else:
                st.info("No staff records found")

    # TAB 4: Reports
    with tab4:
        st.header("Business Analytics")
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", datetime.now().replace(day=1).date())
        with col2:
            end_date = st.date_input("To Date", datetime.now().date())
        
        # Key Metrics
        st.subheader("Performance Metrics")
        metrics = run_query("""
            SELECT 
                COUNT(*) AS total_bookings,
                SUM(Total_Amount) AS total_revenue,
                AVG(Total_Amount) AS avg_booking_value,
                COUNT(DISTINCT Guest_ID) AS unique_guests
            FROM Booking
            WHERE Check_In_Date BETWEEN %s AND %s
            AND Payment_Method != 'Pending'
        """, (start_date, end_date))
        
        if metrics and metrics[0]['total_bookings'] > 0:
            m = metrics[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Bookings", m['total_bookings'])
            with col2:
                st.metric("Total Revenue", f"₹{m['total_revenue']:,.2f}")
            with col3:
                st.metric("Avg Booking", f"₹{m['avg_booking_value']:,.2f}")
            with col4:
                st.metric("Unique Guests", m['unique_guests'])
        else:
            st.warning("No booking data for selected period")
        
        # Revenue by Room Type
        st.subheader("Revenue by Room Type")
        revenue_data = run_query("""
            SELECT 
                r.Room_Type,
                COUNT(b.Booking_ID) AS bookings,
                SUM(b.Total_Amount) AS revenue,
                AVG(b.Total_Amount) AS avg_revenue
            FROM Booking b
            JOIN Room r ON b.Room_ID = r.Room_ID
            WHERE b.Check_In_Date BETWEEN %s AND %s
            AND b.Payment_Method != 'Pending'
            GROUP BY r.Room_Type
            ORDER BY revenue DESC
        """, (start_date, end_date))
        
        if revenue_data:
            st.bar_chart(
                pd.DataFrame(revenue_data).set_index('Room_Type')['revenue'],
                use_container_width=True
            )
        else:
            st.info("No revenue data available")
        
        # Guest Loyalty Report
        st.subheader("Top Guests by Visits")
        top_guests = run_query("""
            SELECT 
                g.Guest_ID,
                g.Name,
                g.Email,
                COUNT(b.Booking_ID) AS visits,
                SUM(b.Total_Amount) AS total_spend,
                c.Loyalty_Points
            FROM Booking b
            JOIN Guest g ON b.Guest_ID = g.Guest_ID
            JOIN CRM c ON g.Guest_ID = c.Guest_ID
            WHERE b.Check_In_Date BETWEEN %s AND %s
            GROUP BY g.Guest_ID
            ORDER BY visits DESC, total_spend DESC
            LIMIT 10
        """, (start_date, end_date))
        
        if top_guests:
            st.dataframe(
                pd.DataFrame(top_guests).style.background_gradient(
                    subset=['visits', 'total_spend'], 
                    cmap='Blues'
                ),
                use_container_width=True,
                height=400
            )
        else:
            st.info("No guest data available")

if __name__ == "__main__":
    main()

if st.sidebar.button("🛠️ Run Email Diagnostics"):
        with st.sidebar:
            st.write("Running tests...")
            diagnose_email_issue()
            st.success("Check terminal for results!")

def diagnose_email_issue():
    """Run this to test all email components"""
    print("\n=== Email System Diagnostics ===")
    
    # 1. Test SMTP Connection
    try:
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            print("✅ SMTP Connection Successful")
    except Exception as e:
        print(f"❌ SMTP Failed: {type(e).__name__} - {str(e)}")
        return

    # 2. Test PDF Generation
    try:
        test_path = "diagnostic.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "TEST PDF", 0, 1, 'C')
        pdf.output(test_path)
        print(f"✅ PDF Generated: {os.path.abspath(test_path)} ({os.path.getsize(test_path)} bytes)")
    except Exception as e:
        print(f"❌ PDF Generation Failed: {str(e)}")
        return

    # 3. Test Email Sending
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv("EMAIL_ADDRESS")
        msg['To'] = os.getenv("EMAIL_ADDRESS")  # Send to yourself
        msg['Subject'] = "Diagnostic Test"
        
        msg.attach(MIMEText("This is a test email body", 'plain'))
        
        with open(test_path, 'rb') as f:
            part = MIMEApplication(f.read(), _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment', filename="test.pdf")
            msg.attach(part)

        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            print("✅ Email Sent with Attachment - Check your inbox/spam")
    except Exception as e:
        print(f"❌ Email Failed: {type(e).__name__} - {str(e)}")
    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

# Run diagnostics when needed (add this temporarily)
if st.sidebar.button("Run Email Diagnostics"):
    diagnose_email_issue()