import streamlit as st
from db_utils import run_query,get_db
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
import time 

# --- Minimal Config ---
load_dotenv("config.env")
HOTEL_NAME = "Farn Hotel & Resorts"


# --- Minimal PDF/Email Functions ---
def generate_secure_receipt(booking_id, max_retries=3, delay=1):
    """Enhanced with retry logic for database consistency"""
    for attempt in range(max_retries):
        try:
            booking = run_query("""
                SELECT b.Booking_ID, g.Name, g.Email, r.Room_Type, 
                       b.Check_In_Date, b.Check_Out_Date, b.Total_Amount
                FROM Booking b
                JOIN Guest g ON b.Guest_ID = g.Guest_ID
                JOIN Room r ON b.Room_ID = r.Room_ID
                WHERE b.Booking_ID = %s
            """, (booking_id,))
            
            if not booking:
                if attempt == max_retries - 1:
                    raise ValueError(f"Booking {booking_id} not found after {max_retries} attempts")
                time.sleep(delay)  # This is where we needed the time import
                continue
                
            booking = booking[0]
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, "Booking Receipt", 0, 1, 'C')
            
            # Add receipt content
            for label, value in [
                ("Booking ID:", booking['Booking_ID']),
                ("Guest:", booking['Name']),
                ("Room:", booking['Room_Type']),
                ("Check-In:", str(booking['Check_In_Date'])),
                ("Check-Out:", str(booking['Check_Out_Date'])),
                ("Total:", f"Rs.{booking['Total_Amount']}")
            ]:
                pdf.cell(40, 10, label, 0, 0)
                pdf.cell(0, 10, str(value), 0, 1)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            pdf.output(temp_file.name)
            return temp_file.name, booking['Email']
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Receipt generation failed after {max_retries} attempts: {str(e)}")
            time.sleep(delay)  # Also needed here

def send_secure_email(to_email, pdf_path):
    """Final battle-tested version with every safeguard"""
    try:
        # Validate inputs
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
        if not '@' in to_email:
            raise ValueError(f"Invalid email: {to_email}")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = os.getenv("EMAIL_ADDRESS")
        msg['To'] = to_email
        msg['Subject'] = f"{HOTEL_NAME} Booking Confirmation"
        
        # Simple text body
        msg.attach(MIMEText(
            "Please find your booking receipt attached.\n\n"
            "Thank you for your reservation!",
            'plain'
        ))

        # Attach PDF with explicit encoding
        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(
                f.read(),
                _subtype='pdf',
                Name="Receipt.pdf"
            )
        part.add_header(
            'Content-Disposition',
            'attachment',
            filename="Booking_Receipt.pdf"
        )
        msg.attach(part)

        # Print raw email headers for debugging
        print("\n=== EMAIL HEADERS ===")
        print(msg.as_string()[:500])  # First 500 characters
        print("====================")

        # Send with timeout
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT")), timeout=10) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            response = server.send_message(msg)
            print(f"SMTP Response: {response}")
            return True

    except Exception as e:
        print(f"❌ FULL ERROR TRACE:\n{type(e).__name__}: {str(e)}\n")
        return False
    finally:
        # Guaranteed cleanup
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                print(f"Temporary file {pdf_path} deleted")
        except Exception as e:
            print(f"Cleanup warning: {str(e)}")

# --- Main Application ---
def main():
    st.set_page_config(layout="wide", page_title="Hotel Management System")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Guest Registration", 
        "Room Booking", 
        "Staff Management", 
        "CRM View"
    ])
    
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
                        st.error("Please fill all required fields (*)")
                    elif len(phone) != 10 or not phone.isdigit():
                        st.error("Phone must be 10 digits")
                    else:
                        try:
                            run_query(
                                "INSERT INTO Guest (Name, Email, Phone, Address) VALUES (%s, %s, %s, %s)",
                                (name, email, phone, address),
                                fetch=False
                            )
                            st.success(f"Guest {name} registered successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        with col2:
            st.subheader("Guest Directory")
            guests = run_query("SELECT * FROM Guest ORDER BY Guest_ID DESC")
            
            if guests:
                df = pd.DataFrame(guests)
                df['Select'] = False
                
                # Display editable dataframe with checkboxes
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select to Delete"),
                        "Guest_ID": "ID",
                        "Name": "Name",
                        "Email": "Email",
                        "Phone": "Phone",
                        "Address": "Address"
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=["Guest_ID", "Name", "Email", "Phone", "Address"]
                )
                
                # Delete selected guests
                if st.button("Delete Selected Guests", type="primary"):
                    selected_ids = edited_df[edited_df['Select']]['Guest_ID'].tolist()
                    if selected_ids:
                        for guest_id in selected_ids:
                            run_query(
                                "DELETE FROM Guest WHERE Guest_ID = %s",
                                (guest_id,),
                                fetch=False
                            )
                        st.success(f"Deleted {len(selected_ids)} guest(s)")
                        st.rerun()
                    else:
                        st.warning("No guests selected for deletion")
            else:
                st.info("No guests found in database")

    # TAB 2: Room Booking
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
                  index=0
                )
        
                if st.form_submit_button("Confirm Booking"):
                    try:
                        # 1. Validate guest exists
                        guest_exists = run_query(
                            "SELECT 1 FROM Guest WHERE Guest_ID = %s",
                            (guest_id,)
                        )
                        if not guest_exists:
                            st.error("Guest ID does not exist!")
                            return

                        # 2. Create booking (returns the new booking ID)
                        booking_id = run_query(
                            """INSERT INTO Booking 
                            (Guest_ID, Room_ID, Check_In_Date, Check_Out_Date, Payment_Method)
                            VALUES (%s, %s, %s, %s, %s)""",
                            (guest_id, room_id, check_in, check_out, payment_method),
                            fetch=False
                        )

                        # 3. Generate receipt with retries
                        receipt_path, guest_email = generate_secure_receipt(booking_id)
                        
                        if not receipt_path:
                            st.error("Receipt generation failed!")
                            return

                        # 4. Send email
                        email_sent = False
                        if guest_email and '@' in guest_email:
                            email_sent = send_secure_email(guest_email, receipt_path)

                        # 5. User feedback
                        if email_sent:
                            st.success(f"""
                            ✅ Booking #{booking_id} Confirmed!
                            📧 Receipt sent to {guest_email}
                            """)
                        else:
                            st.warning(f"""
                            ✅ Booking #{booking_id} Confirmed!
                            ⚠️ Email not sent - download your receipt below
                            """)
                            # PDF download fallback
                            with open(receipt_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Receipt",
                                    data=f,
                                    file_name=f"{HOTEL_NAME}_Booking_{booking_id}.pdf",
                                    mime="application/pdf"
                                )

                        st.balloons()

                    except Exception as e:
                        st.error(f"❌ Booking failed: {str(e)}")

        with col2:
            st.subheader("Available Rooms")
            available_rooms = run_query("""
                SELECT r.Room_ID, r.Room_Type, r.Price 
                FROM Room r
                WHERE r.Status = 'Available'
                AND r.Room_ID NOT IN (
                    SELECT Room_ID FROM Booking 
                    WHERE Check_Out_Date > CURDATE()
                )
                ORDER BY r.Room_ID
            """)
            st.dataframe(pd.DataFrame(available_rooms), use_container_width=True)
            
            st.subheader("Active Bookings")
            active_bookings = run_query("""
                SELECT b.Booking_ID, g.Name, r.Room_ID, r.Room_Type, 
                       b.Check_In_Date, b.Check_Out_Date, b.Payment_Method
                FROM Booking b
                JOIN Guest g ON b.Guest_ID = g.Guest_ID
                JOIN Room r ON b.Room_ID = r.Room_ID
                WHERE b.Check_Out_Date > CURDATE()
                ORDER BY b.Check_In_Date
            """)
            
            if active_bookings:
                df = pd.DataFrame(active_bookings)
                df['Select'] = False
                
                edited_bookings = st.data_editor(
                    df,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select to Cancel"),
                        "Booking_ID": "Booking ID",
                        "Name": "Guest Name",
                        "Room_ID": "Room ID",
                        "Room_Type": "Room Type",
                        "Check_In_Date": "Check-In",
                        "Check_Out_Date": "Check-Out",
                        "Payment_Method": "Payment"
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=["Booking_ID", "Name", "Room_ID", "Room_Type", 
                             "Check_In_Date", "Check_Out_Date", "Payment_Method"]
                )
                
                if st.button("Cancel Selected Bookings", type="primary"):
                    selected_bookings = edited_bookings[edited_bookings['Select']]['Booking_ID'].tolist()
                    if selected_bookings:
                        for booking_id in selected_bookings:
                            run_query(
                                "DELETE FROM Booking WHERE Booking_ID = %s",
                                (booking_id,),
                                fetch=False
                            )
                        st.success(f"Cancelled {len(selected_bookings)} booking(s)")
                        st.rerun()
                    else:
                        st.warning("No bookings selected for cancellation")
            else:
                st.info("No active bookings found")

    # TAB 3: Staff Management
    with tab3:
        st.header("Staff Management")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            with st.form("staff_form", clear_on_submit=True):
                st.subheader("Add Staff Member")
                name = st.text_input("Name*")
                role = st.selectbox(
                    "Role*",
                    ["Receptionist", "Manager", "Housekeeping", "Chef", "Maintenance"]
                )
                contact = st.text_input("Phone*", max_chars=10)
                
                if st.form_submit_button("Add Staff"):
                    if not all([name, contact]):
                        st.error("Please fill all required fields (*)")
                    elif len(contact) != 10 or not contact.isdigit():
                        st.error("Phone must be 10 digits")
                    else:
                        try:
                            run_query(
                                "INSERT INTO Staff (Name, Role, Contact) VALUES (%s, %s, %s)",
                                (name, role, contact),
                                fetch=False
                            )
                            st.success(f"Staff {name} added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        with col2:
            st.subheader("Staff Directory")
            staff = run_query("SELECT * FROM Staff ORDER BY Staff_ID DESC")
            
            if staff:
                df = pd.DataFrame(staff)
                df['Select'] = False
                
                edited_staff = st.data_editor(
                    df,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select to Delete"),
                        "Staff_ID": "ID",
                        "Name": "Name",
                        "Role": "Role",
                        "Contact": "Phone"
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=["Staff_ID", "Name", "Role", "Contact"]
                )
                
                if st.button("Delete Selected Staff", type="primary"):
                    selected_ids = edited_staff[edited_staff['Select']]['Staff_ID'].tolist()
                    if selected_ids:
                        for staff_id in selected_ids:
                            run_query(
                                "DELETE FROM Staff WHERE Staff_ID = %s",
                                (staff_id,),
                                fetch=False
                            )
                        st.success(f"Deleted {len(selected_ids)} staff member(s)")
                        st.rerun()
                    else:
                        st.warning("No staff selected for deletion")
            else:
                st.info("No staff found in database")

    # TAB 4: CRM View
    with tab4:
        st.header("Customer Loyalty Program")
        crm_data = run_query("""
            SELECT g.Guest_ID, g.Name, g.Email, c.Loyalty_Points
            FROM CRM c
            JOIN Guest g ON c.Guest_ID = g.Guest_ID
            ORDER BY c.Loyalty_Points DESC
        """)
        
        if crm_data:
            st.dataframe(
                pd.DataFrame(crm_data),
                column_config={
                    "Guest_ID": "Guest ID",
                    "Name": "Name",
                    "Email": "Email",
                    "Loyalty_Points": "Loyalty Points"
                },
                use_container_width=True
            )
        else:
            st.info("No CRM data available")

if __name__ == "__main__":
    main()