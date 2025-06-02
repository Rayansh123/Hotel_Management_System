import smtplib
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login("rayanshukla@gmail.com", "fggtitsygefdlytz")
server.sendmail("rayanshukla@gmail.com", "rayanshukla@gmail.com", "Subject: Test\n\nBody")
server.quit()