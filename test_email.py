import smtplib

username = "af2373001@smtp-brevo.com"
password = "xsmtpsib-8c1584a0b59c5196b31a14b736669d84827ac460a044202802674c3e2cb51993-vonUWfu7gOM70hf7"

try:
    server = smtplib.SMTP("smtp-relay.brevo.com", 587)
    server.starttls()
    server.login(username, password)
    print("SUCCESS: Logged in to Brevo!")
    server.quit()
except Exception as e:
    print(f"FAILED: {e}")
