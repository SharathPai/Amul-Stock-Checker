from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import shutil

# ------------------ CONFIG ------------------
URL = "https://shop.amul.com/en/browse/protein"
PINCODE = "411047"
#SENDER_EMAIL = os.getenv("EMAIL_USER")
#SENDER_PASSWORD = os.getenv("EMAIL_PASS")  # Use app password
#RECIPIENT_EMAIL = os.getenv("EMAIL_USER")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("SENDER_EMAIL")
firefox_path = shutil.which("firefox")

# Products of interest
TARGET_PRODUCTS = [
    "Amul High Protein Plain Lassi, 200 mL | Pack of 30"
    #,"Amul High Protein Buttermilk, 200 mL | Pack of 30"
    ,"Amul High Protein Rose Lassi, 200 mL | Pack of 30"
    ,"Amul Chocolate Whey Protein, 34 g | Pack of 30 sachets"
    #,"Amul High Protein Blueberry Shake, 200 mL | Pack of 30"
]
# --------------------------------------------

def scrape_products():
    options = Options()
    #options.add_argument("--start-maximized")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")     # good practice in CI
    options.add_argument("--disable-dev-shm-usage")
    #options.binary_location = firefox_path
    options.binary_location = "/usr/bin/firefox"
    #service = Service(GeckoDriverManager().install())
    #driver = webdriver.Firefox(service=Service(), options=options)
    # Geckodriver will be found automatically if installed in /usr/local/bin
    driver = webdriver.Firefox(options=options)
    driver.get(URL)

    wait = WebDriverWait(driver, 15)

    # Enter pincode
    pincode_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
    time.sleep(2)
    pincode_box.send_keys(PINCODE)
    time.sleep(2)
    pincode_box.send_keys(Keys.RETURN)

    time.sleep(5)

    # Scroll to bottom to load all products
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    # Collect products
    products = driver.find_elements(By.CSS_SELECTOR, ".product-grid-item")
    results = []
    for p in products:
        try:
            name = p.find_element(By.CSS_SELECTOR, ".product-grid-name a").text.strip()
        except:
            name = "Unknown"

        try:
            price = p.find_element(By.CSS_SELECTOR, ".product-grid-price").text.strip()
        except:
            price = "N/A"

        try:
            add_btn = p.find_element(By.CSS_SELECTOR, ".mobile-btn span").text.strip()
            in_stock = "In Stock" if add_btn == "ADD" else "Out of Stock"
        except:
            in_stock = "Unknown"

        results.append({
            "name": name,
            "price": price,
            "stock": in_stock
        })

    driver.quit()
    return results

def filter_target_products(products):
    filtered = []
    for t in TARGET_PRODUCTS:
        match = next((p for p in products if t.lower() in p["name"].lower()), None)
        if match:
            filtered.append(match)
        else:
            filtered.append({"name": t, "price": "N/A", "stock": "Not Found"})
    return filtered

def send_email(filtered_products):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Amul Protein Availability Alert 🚨"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    html = "<h2>Stock Status for Selected Products</h2><ul>"
    for p in filtered_products:
        html += f"<li>{p['name']} | {p['price']} | <b>{p['stock']}</b></li>"
    html += "</ul>"

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    print("✅ Email sent successfully!")

if __name__ == "__main__":
    products = scrape_products()
    filtered = filter_target_products(products)

    # Print to console for debugging
    print("\nStock Status:")
    for p in filtered:
        print(f"{p['name']} | {p['price']} | {p['stock']}")

    # Only send mail if at least one target product is in stock
    if any(p["stock"] == "In Stock" for p in filtered):
        send_email(filtered)
    else:
        print("ℹ️ No target products in stock. Email not sent.")













