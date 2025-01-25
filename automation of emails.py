import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Path to ChromeDriver (replace with your local path if necessary)
driver_path = r'C:\Users\Hussain\Downloads\ChromeDriver\chromedriver.exe'

# Set up the Service object
service = Service(driver_path)

# Set up Chrome options
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Headless mode can be used if you don't want the browser window to pop up

# Load saved account details from JSON file
def load_account_details():
    try:
        with open("accounts.json", "r") as file:
            accounts = json.load(file)
        return accounts[-1]  # Assuming you want the last saved account
    except (FileNotFoundError, json.JSONDecodeError):
        print("No saved accounts found.")
        return None

# Get account details from the JSON file
account = load_account_details()
if account:
    email = account["email"]
    password = account["password"]
else:
    print("No account found to log in.")
    exit()

# Set up the Chrome WebDriver
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open the website
driver.get("https://stackblitz.com/sign_in")

try:
    # Wait for the login form to load
    wait = WebDriverWait(driver, 15)

    # Locate the email and password fields using more generic selectors
    email_field = wait.until(EC.presence_of_element_located((By.NAME, "login")))

    password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))

    # Fill out the login form using the credentials from the JSON file
    email_field.send_keys(email)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)
    print(f"Login credentials entered and submitted for {email}!")

    time.sleep(1)

    # Skip any further interactions and directly go to the link after login
    driver.get("https://bolt.new/?utm_campaign=stackblitz-on-page&utm_source=web-app&utm_medium=nav-button")
    print("Opened the Bolt link!")

    time.sleep(1)

    # Check and click the sign-in button if available
    try:
        sign_in_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.flex.rounded-md.items-center.justify-center"))
        )
        print("Sign-in button found and ready to click.")
        sign_in_button.click()
    except Exception as e:
        print(f"Button click failed or issue: {e}")

    time.sleep(2.5)

    textarea = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.w-full.pl-4.pt-4.pr-16"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", textarea)

    textarea.send_keys("make website with hello world")
    textarea.send_keys(Keys.RETURN)
    print("Message sent successfully!")

    time.sleep(1)

    time.sleep(5)

    try:
        export_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="radix-:r1k:"]'))
        )
        print("Export button found and ready to click.")
        export_button.click()
    except Exception as e:
        print(f"Error with export button: {e}")


    try:
        download_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:download-simple.size-4\\.5"))
        )
        print("Download button found and ready to click.")
        download_button.click()
        print("Download started!")
    except Exception as e:
        print(f"Error with download button: {e}")

    time.sleep(10)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    time.sleep(35)

    driver.quit()
