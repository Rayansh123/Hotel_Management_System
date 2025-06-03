-- Create Guest Table
CREATE TABLE Guest (
    Guest_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(100) UNIQUE,
    Phone CHAR(10),
    Address TEXT,
    CONSTRAINT chk_phone CHECK (LENGTH(Phone) = 10)
);

-- Create Room Table
CREATE TABLE Room (
    Room_ID INT AUTO_INCREMENT PRIMARY KEY,
    Room_Type ENUM('Standard', 'Deluxe', 'Suite') NOT NULL,
    Price DECIMAL(10,2) NOT NULL,
    Status ENUM('Available', 'Booked', 'Under Maintenance') DEFAULT 'Available',
    CONSTRAINT chk_price CHECK (Price > 0)
);

-- Create Staff Table
CREATE TABLE Staff (
    Staff_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Role ENUM('Receptionist', 'Manager', 'Housekeeping') NOT NULL,
    Contact CHAR(10) NOT NULL,
    CONSTRAINT chk_staff_contact CHECK (LENGTH(Contact) = 10)
);

-- Create Booking Table
CREATE TABLE Booking (
    Booking_ID INT AUTO_INCREMENT PRIMARY KEY,
    Guest_ID INT NOT NULL,
    Room_ID INT NOT NULL,
    Check_In_Date DATE NOT NULL,
    Check_Out_Date DATE NOT NULL,
    Total_Amount DECIMAL(10,2) NOT NULL,
    Payment_Method ENUM('Credit Card', 'Cash', 'UPI', 'Pending') DEFAULT 'Pending',
    CONSTRAINT fk_guest FOREIGN KEY (Guest_ID) REFERENCES Guest(Guest_ID),
    CONSTRAINT fk_room FOREIGN KEY (Room_ID) REFERENCES Room(Room_ID),
    CONSTRAINT chk_dates CHECK (Check_Out_Date > Check_In_Date),
    CONSTRAINT chk_amount CHECK (Total_Amount >= 0)
);

-- Create CRM Table (Simplified without feedback columns)
CREATE TABLE CRM (
    CRM_ID INT AUTO_INCREMENT PRIMARY KEY,
    Guest_ID INT NOT NULL,
    Loyalty_Points INT DEFAULT 0,
    CONSTRAINT fk_crm_guest FOREIGN KEY (Guest_ID) REFERENCES Guest(Guest_ID),
    CONSTRAINT chk_points CHECK (Loyalty_Points >= 0)
);

--Triggers & Procedures
DELIMITER //
CREATE TRIGGER add_loyalty_points_after_stays
AFTER INSERT ON Booking
FOR EACH ROW
BEGIN
    DECLARE paid_stays INT;
    
    -- Count completed stays (where Payment_Method is not 'Pending')
    SELECT COUNT(*) INTO paid_stays 
    FROM Booking 
    WHERE Guest_ID = NEW.Guest_ID 
    AND Payment_Method IN ('Credit Card', 'Cash', 'UPI');
    
    -- Add 100 points after every 2 paid stays (2nd, 4th, 6th etc.)
    IF paid_stays % 2 = 0 AND paid_stays > 0 THEN
        UPDATE CRM 
        SET Loyalty_Points = 100 
        WHERE Guest_ID = NEW.Guest_ID;
    END IF;
END //
DELIMITER ;

DELIMITER //
CREATE TRIGGER booking_calculation_and_discount
BEFORE INSERT ON Booking
FOR EACH ROW
BEGIN
    DECLARE room_price DECIMAL(10,2);
    DECLARE stay_duration INT;
    DECLARE paid_stays INT;
    DECLARE current_points INT;
    
    -- 1. FIRST: Calculate base amount (replaces calculate_booking_total)
    SELECT Price INTO room_price FROM Room WHERE Room_ID = NEW.Room_ID;
    SET stay_duration = DATEDIFF(NEW.Check_Out_Date, NEW.Check_In_Date);
    SET NEW.Total_Amount = room_price * stay_duration;
    
    -- 2. THEN: Apply loyalty discount if eligible
    SELECT COUNT(*) INTO paid_stays 
    FROM Booking 
    WHERE Guest_ID = NEW.Guest_ID 
    AND Payment_Method IN ('Credit Card', 'Cash', 'UPI');
    
    SELECT Loyalty_Points INTO current_points
    FROM CRM WHERE Guest_ID = NEW.Guest_ID;
    
    IF (paid_stays + 1) % 2 = 1 AND current_points = 100 THEN
        SET NEW.Total_Amount = NEW.Total_Amount - 100;
        UPDATE CRM SET Loyalty_Points = 0 WHERE Guest_ID = NEW.Guest_ID;
    END IF;
END //
DELIMITER ;

DELIMITER //
CREATE TRIGGER update_room_status
AFTER INSERT ON Booking
FOR EACH ROW
BEGIN
    -- Mark room as booked when a booking is created
    UPDATE Room 
    SET Status = 'Booked' 
    WHERE Room_ID = NEW.Room_ID;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE free_expired_rooms()
BEGIN
    -- Free all rooms with expired bookings
    UPDATE Room r
    JOIN Booking b ON r.Room_ID = b.Room_ID
    SET r.Status = 'Available'
    WHERE b.Check_Out_Date <= CURDATE()
    AND r.Status = 'Booked';
    
    SELECT CONCAT(ROW_COUNT(), ' rooms freed') AS Result;
END //
DELIMITER ;

DELIMITER //
CREATE EVENT daily_room_cleanup
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO BEGIN
    CALL free_expired_rooms(); -- Frees all rooms with expired bookings
END //
DELIMITER ;

SET GLOBAL event_scheduler = ON;-- need to run this if the server is rebooted

DELIMITER //
CREATE TRIGGER free_room_on_booking_delete
AFTER DELETE ON Booking
FOR EACH ROW
BEGIN
    -- Only free if booking was for future dates
    IF OLD.Check_Out_Date > CURDATE() THEN
        UPDATE Room 
        SET Status = 'Available'
        WHERE Room_ID = OLD.Room_ID
        AND Status = 'Booked'; -- Prevent unnecessary updates
    END IF;
END //
DELIMITER ;

DELIMITER //
CREATE TRIGGER free_rooms_on_guest_delete 
BEFORE DELETE ON Guest
FOR EACH ROW
BEGIN
    -- Free all rooms from guest's future bookings(additional safety net)
    UPDATE Room r
    JOIN Booking b ON r.Room_ID = b.Room_ID
    SET r.Status = 'Available'
    WHERE b.Guest_ID = OLD.Guest_ID
    AND b.Check_Out_Date > CURDATE();
END //
DELIMITER ;

DELIMITER //
CREATE TRIGGER prevent_overlapping_bookings
BEFORE INSERT ON Booking
FOR EACH ROW
BEGIN
    -- Check if the room has existing bookings with date overlap
    IF EXISTS (
        SELECT 1 FROM Booking 
        WHERE Room_ID = NEW.Room_ID
        AND Check_Out_Date >= NEW.Check_In_Date 
        AND Check_In_Date <= NEW.Check_Out_Date
    ) THEN
        -- Cancel the insertion if conflict exists
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Room already booked for these dates';
    END IF;
END //booking
DELIMITER ;

DELIMITER //
CREATE TRIGGER add_crm_on_guest_insert
AFTER INSERT ON Guest
FOR EACH ROW
BEGIN
    -- Automatically create a CRM record for new guests
    INSERT INTO CRM (Guest_ID, Loyalty_Points)
    VALUES (NEW.Guest_ID, 0); -- Start with 0 loyalty points
END //
DELIMITER ;

DELIMITER //
CREATE TRIGGER remove_crm_on_guest_delete
BEFORE DELETE ON Guest
FOR EACH ROW
BEGIN
    -- First delete the CRM record to maintain referential integrity
    DELETE FROM CRM WHERE Guest_ID = OLD.Guest_ID;
END //
DELIMITER ;
