from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import time

def handle_project_download(driver, wait):
    try:
        # Click export button
        export_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="radix-:r1k:"]'))
        )
        print("Export button found, clicking...")
        export_button.click()
        
        # Click download button
        download_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:download-simple.size-4\\.5"))
        )
        print("Download button found, clicking...")
        download_button.click()
        
        # Wait for download to complete
        time.sleep(5)
        
        # Get the latest downloaded file
        downloads_path = os.path.expanduser("~/Downloads")
        files = os.listdir(downloads_path)
        files = [os.path.join(downloads_path, f) for f in files if f.endswith('.zip')]
        if files:
            latest_file = max(files, key=os.path.getctime)
            return latest_file
            
        return None
        
    except Exception as e:
        print(f"Error during download: {e}")
        return None 
