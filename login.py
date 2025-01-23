from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Path to ChromeDriver (replace with your local path if necessary)
driver_path = r'C:\Users\Hussain\Downloads\ChromeDriver\chromedriver.exe'

service = Service(driver_path)

driver = webdriver.Chrome(service=service)

driver.get("https://stackblitz.com/sign_in")

try:
    wait = WebDriverWait(driver, 15)

    email_field = wait.until(EC.presence_of_element_located((By.NAME, "login")))
    password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))

    email_field.send_keys("lisije6766@dfesc.com")
    password_field.send_keys("Parol786!")
    password_field.send_keys(Keys.RETURN)
    print("Login credentials entered and submitted!")

    time.sleep(2)

    driver.get("https://bolt.new/?utm_campaign=stackblitz-on-page&utm_source=web-app&utm_medium=nav-button")
    print("Opened the Bolt link!")

    time.sleep(2)

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
    driver.execute_script("arguments[0].scrollIntoView(true);", textarea)

    textarea.send_keys("This is a test message to check typing into the textarea.")
    print("Message typed successfully!")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    time.sleep(5)

    driver.quit()
