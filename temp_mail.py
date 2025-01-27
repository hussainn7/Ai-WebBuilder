import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import hashlib
from bs4 import BeautifulSoup
import json
import os

# Temp Mail API settings
API_KEY = "7e3bfe9144msh9f122e5631c0f45p142244jsn448f2b50a171"
BASE_URL = "https://privatix-temp-mail-v1.p.rapidapi.com/request/"
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "privatix-temp-mail-v1.p.rapidapi.com"
}

# Path to ChromeDriver
DRIVER_PATH = './driver'

def save_account_details(email, username, password):
    try:
        # Load existing data if it exists
        try:
            with open("accounts.json", "r") as file:
                accounts = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            accounts = []

        # Add new account to the list
        accounts.append({"email": email, "username": username, "password": password})

        # Save the updated list to the JSON file
        with open("accounts.json", "w") as file:
            json.dump(accounts, file, indent=4)

        print("Account details saved successfully.")
    except Exception as e:
        print(f"Error saving account details: {e}")

# Function to generate a temporary email
def get_temp_email():
    url = f"{BASE_URL}mail/id/"
    response = requests.get(f"{BASE_URL}domains/", headers=HEADERS)
    if response.status_code == 200:
        domains = response.json()
        if domains:
            email = f"user{int(time.time())}{domains[0]}"  # Generate a unique email
            print(f"Generated Temporary Email Address: {email}")
            return email
    print("Failed to fetch email domains.")
    return None

def get_md5_hash(email_address):
    return hashlib.md5(email_address.encode()).hexdigest()

def extract_confirmation_link(content):
    try:
        soup = BeautifulSoup(content, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if "confirmation_token" in href:
                return href
    except Exception as e:
        print(f"Error parsing content: {e}")
    match = re.search(r'(https?://[^\s]+)', content)
    return match.group(0) if match else None

def wait_for_email(email_address):
    email_hash = get_md5_hash(email_address)
    url = f"{BASE_URL}mail/id/{email_hash}/"
    print("Waiting for email...")
    for _ in range(3):
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            try:
                inbox = response.json()
                if isinstance(inbox, list) and len(inbox) > 0:
                    email_content = inbox[0]
                    potential_fields = ['mail_text_only', 'mail_html', 'mail_preview']
                    for field in potential_fields:
                        body = email_content.get(field, '')
                        if body:
                            confirmation_link = extract_confirmation_link(body)
                            if confirmation_link:
                                return confirmation_link
            except Exception as e:
                print(f"Error parsing response: {e}")
        time.sleep(6)
    return None

def init_chrome_options():
    chrome_options = Options()
    # Always use headless for production
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    if os.environ.get('FLASK_ENV') == 'production':
        chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
    
    return chrome_options

def init_chrome_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            chrome_options = init_chrome_options()
            service = Service(DRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)

def perform_registration_and_verify(email):
    try:
        driver = init_chrome_with_retry()
        try:
            # Open registration page
            driver.get("https://stackblitz.com/register")

            wait = WebDriverWait(driver, 15)
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))

            username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))

            password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))

            password_confirm_field = wait.until(EC.presence_of_element_located((By.NAME, "password-confirm")))

            sign_up_button = wait.until(EC.presence_of_element_located(
                (By.XPATH, "/html/body/div/div/div[2]/div/div/div/main/div[2]/div/div/form/button")))

            username = "user" + str(int(time.time()))  # Generate a unique username
            password = "Parol786!"

            email_field.send_keys(email)
            username_field.send_keys(username)
            password_field.send_keys(password)
            password_confirm_field.send_keys(password)
            sign_up_button.click()
            print(f"Registration submitted with Email: {email}, Username: {username}, and Password: {password}")

            # Wait for email verification link
            confirmation_link = wait_for_email(email)
            if confirmation_link:
                print(f"Confirmation link found: {confirmation_link}")
                print("Opening confirmation link in the same browser window...")

                driver.get(confirmation_link)  # Open the confirmation link in the same window
                print("Confirmation link opened successfully.")

                # Save account details after successful confirmation
                save_account_details(email, username, password)

            else:
                print("Failed to find the confirmation link in the email.")
        except Exception as e:
            print(f"An error occurred: {e}")
    except Exception as e:
        print(f"Error initializing Chrome options: {e}")
    finally:
        driver.quit()

def main():
    temp_email = get_temp_email()
    if temp_email:
        perform_registration_and_verify(temp_email)
    else:
        print("Failed to generate a temporary email. Aborting.")

def cleanup_driver(driver):
    if driver:
        try:
            driver.quit()
            print("✓ Driver closed successfully")
        except Exception as e:
            print(f"× Error closing driver: {e}")

def validate_chrome_setup():
    if not os.path.exists(DRIVER_PATH):
        raise Exception("ChromeDriver not found. Please install ChromeDriver first.")
    
    if not os.access(DRIVER_PATH, os.X_OK):
        try:
            os.chmod(DRIVER_PATH, 0o755)
        except Exception as e:
            raise Exception(f"Cannot set ChromeDriver permissions: {e}")

if __name__ == "__main__":
    main()
