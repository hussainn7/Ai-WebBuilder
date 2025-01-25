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

    # Fill out the login form
    email_field.send_keys("lisije6766@dfesc.com")
    password_field.send_keys("Parol786!")
    password_field.send_keys(Keys.RETURN)
    print("Login credentials entered and submitted!")

    time.sleep(2)

    # Skip any further interactions and directly go to the link after login
    driver.get("https://bolt.new/?utm_campaign=stackblitz-on-page&utm_source=web-app&utm_medium=nav-button")
    print("Opened the Bolt link!")

    time.sleep(2)

    # Check and click the sign-in button if available
    try:
        sign_in_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.flex.rounded-md.items-center.justify-center"))
        )
        print("Sign-in button found and ready to click.")
        sign_in_button.click()
    except Exception as e:
        print(f"Button click failed or issue: {e}")

    time.sleep(5)

    textarea = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.w-full.pl-4.pt-4.pr-16"))
    )
    # Scroll into view if necessary
    driver.execute_script("arguments[0].scrollIntoView(true);", textarea)

    # Type into the textarea
    textarea.send_keys(".")
    textarea.send_keys(Keys.RETURN)
    print("Message sent successfully!")

    time.sleep(3)

    ready_message = wait.until(
        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'ready in')]"))
    )
    print("Terminal is ready! Proceeding with export and download...")

    # Export button
    try:
        export_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:export.text-lg"))
        )
        print("Export button found and ready to click.")
        export_button.click()
    except Exception as e:
        print(f"Error with export button: {e}")

    # Wait for the Download button to be clickable
    try:
        download_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:download-simple.size-4\\.5"))
        )
        print("Download button found and ready to click.")
        download_button.click()
        print("Download started!")
    except Exception as e:
        print(f"Error with download button: {e}")

    # Wait for the download to complete (you might want to adjust the sleep time based on file size)
    time.sleep(10)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Optional delay to observe the browser
    time.sleep(35)

    # Gracefully close the browser
    driver.quit()
