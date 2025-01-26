from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from models import db, User, Chat, Message
import os
import time
from temp_mail import get_temp_email, perform_registration_and_verify  # Import from your existing script
from pathlib import Path
import platform
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Environment and system configuration
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production'
SYSTEM_TYPE = platform.system().lower()

# Flask application setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Kwork'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

current_driver = None

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        app.logger.info("User already authenticated")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            app.logger.info(f"Login attempt for username: {username}")
            
            user = User.query.filter_by(username=username).first()
            app.logger.info(f"User found: {user is not None}")
            
            if user:
                app.logger.info("User found, checking password.")
                if user.check_password(password):
                    app.logger.info("Password check passed.")
                    login_user(user)
                    return redirect(url_for('index'))
                else:
                    app.logger.warning("Invalid password.")
            else:
                app.logger.warning("User not found.")
            
            error = 'Invalid username or password'
            return render_template('login.html', error=error)
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}", exc_info=True)
            return render_template('login.html', error=f'Login error: {str(e)}')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if User.query.filter_by(username=username).first():
                return render_template('register.html', error='Username already exists')
            
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error='An error occurred during registration')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Chat routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/chat')
@login_required
def index():
    chats = Chat.query.filter_by(user_id=current_user.id)\
        .order_by(Chat.created_at.desc())\
        .limit(20)\
        .all()
    return render_template('index.html', 
                         chats=chats,
                         current_chat=None,
                         current_chat_id=None,
                         messages=[])

@app.route('/chat/<int:chat_id>')
@login_required
def view_chat(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    messages = Message.query.filter_by(chat_id=chat_id).all()
    return render_template('chat.html', chat=chat, messages=messages)

# Initialize driver path and options
driver_path = '/usr/local/bin/chromedriver'  # Update this to your actual path
service = Service(driver_path)

def init_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Create downloads directory if it doesn't exist
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'website_downloads')
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    # Add download preferences with more permissions
    chrome_options.add_experimental_option(
        'prefs', {
            'download.default_directory': download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True,
            'profile.default_content_settings.popups': 0,
            'profile.default_content_setting_values.automatic_downloads': 1,
            'profile.content_settings.exceptions.automatic_downloads.*.setting': 1
        }
    )
    
    # Add additional permissions
    chrome_options.add_argument('--allow-file-access-from-files')
    chrome_options.add_argument('--allow-file-access')
    chrome_options.add_argument('--allow-cross-origin-auth-prompt')
    
    return chrome_options

chrome_options = init_chrome_options()  # Initialize options

def load_account_details():
    try:
        with open("accounts.json", "r") as file:
            accounts = json.load(file)
        return accounts[-1]  # Assuming you want the last saved account
    except (FileNotFoundError, json.JSONDecodeError):
        print("No saved accounts found.")
        return None

def automate_task(user_message):
    account = load_account_details()
    if not account:
        print("No account found to log in.")
        return

    email = account["email"]
    password = account["password"]

    chrome_options = init_chrome_options()
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        logging.error(f"Failed to initialize WebDriver: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to initialize WebDriver"})
    driver.get("https://stackblitz.com/sign_in")
    print('on link')
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

        # Store the driver instance globally or in a session to reuse it
        global current_driver
        current_driver = driver

        textarea = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.w-full.pl-4.pt-4.pr-16"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", textarea)

        textarea.send_keys(user_message)
        textarea.send_keys(Keys.RETURN)
        print("Message sent successfully!")

        time.sleep(5)  # Reduced wait time since we're keeping the chat open

        return {"status": "success", "message": "Message sent successfully!"}

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}

@app.route('/start_task', methods=['POST'])
def start_task():
    user_message = request.form['user_message']

    # Run the automation in a separate thread
    thread = Thread(target=automate_task, args=(user_message,))
    thread.start()

    return jsonify({
        "status": "success", 
        "message": "Automation task started!",
        "ai_response": "Hello! I'm setting up the environment and getting ready to help you. This will take about 30 seconds..."
    })

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    user_message = request.form.get('user_message')
    chat_id = request.form.get('chat_id')

    logging.info(f"Received User Message: {user_message}, Chat ID: {chat_id}")  # Log received data

    if not user_message or not chat_id:
        logging.error("Missing message or chat ID")
        return jsonify({"status": "error", "message": "Missing message or chat ID"})

    # Save the message to the database
    message = Message(content=user_message, is_user=True, chat_id=chat_id)
    db.session.add(message)
    db.session.commit()

    logging.info("Message sent successfully!")
    return jsonify({"status": "success", "message": "Message sent!"})

@app.route('/download_website', methods=['POST'])
def download_website():
    global current_driver
    
    print("\n=== Starting Download Process ===")
    print("Download button clicked in frontend")
    
    if not current_driver:
        return jsonify({"status": "error", "message": "No active session. Please start a new automation."})
    
    try:
        wait = WebDriverWait(current_driver, 15)
        
        print(f"Current URL: {current_driver.current_url}")
        print("Driver session is active")
        
        # Click Export button using class selector
        print("\nStep 1: Looking for Export button...")
        try:
            export_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:export.text-lg"))
            )
            print("✓ Export button found")
            print("Attempting to click export button's parent...")
            parent = export_button.find_element(By.XPATH, "..")
            parent.click()
            print("✓ Export button clicked successfully")
        except Exception as e:
            print(f"Export button error: {str(e)}")
            raise
        
        time.sleep(2)  # Wait for download menu to appear
        print("\nStep 2: Waiting for download menu...")
        
        # Click Download button using class selector
        print("Looking for Download button...")
        try:
            download_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:download-simple.size-4\\.5"))
            )
            print("✓ Download button found")
            print("Attempting to click download button's parent...")
            parent = download_button.find_element(By.XPATH, "..")
            parent.click()
            print("✓ Download button clicked successfully")
            
            # Wait for download to start
            time.sleep(5)  # Increased wait time
            
            # Check if download directory exists and has write permissions
            download_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'website_downloads')
            if not os.access(download_dir, os.W_OK):
                raise Exception(f"No write permission for directory: {download_dir}")
                
        except Exception as e:
            print(f"Download button error: {str(e)}")
            raise
        
        print("\nStep 3: Download initiated...")
        
        return jsonify({
            "status": "success",
            "message": "Website download started! Check your downloads/website_downloads folder."
        })
        
    except Exception as e:
        print("\n!!! Download Process Failed !!!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Taking error screenshot...")
        
        try:
            screenshot_path = "download_error.png"
            current_driver.save_screenshot(screenshot_path)
            print(f"✓ Error screenshot saved to {screenshot_path}")
        except Exception as screenshot_error:
            print(f"× Failed to save error screenshot: {screenshot_error}")
        
        print("=== Download Process Failed ===\n")
            
        return jsonify({
            "status": "error",
            "message": f"Failed to download: {str(e)}"
        })

@app.route('/create_new_account', methods=['POST'])
@login_required
def create_new_account():
    global current_driver
    try:
        # Close current Selenium session if exists
        if current_driver:
            try:
                current_driver.quit()
            except:
                pass
            current_driver = None

        # Create new account using your existing script
        temp_email = get_temp_email()
        if temp_email:
            perform_registration_and_verify(temp_email)
            return jsonify({
                "status": "success",
                "message": "New account created successfully!"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to generate temporary email"
            })
    except Exception as e:
        print(f"Error creating new account: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to create account: {str(e)}"
        })

@app.route('/check_download_status')
def check_download_status():
    global current_driver
    
    if not current_driver:
        return jsonify({"status": "error"})
        
    try:
        # Check if download dialog is still open
        download_elements = current_driver.find_elements(By.CSS_SELECTOR, "[aria-label='Download']")
        if not download_elements:
            return jsonify({"status": "completed"})
        return jsonify({"status": "in_progress"})
    except:
        return jsonify({"status": "error"})

@app.route('/check_website_status', methods=['GET'])
def check_website_status():
    global current_driver
    
    if not current_driver:
        return jsonify({"status": "error", "message": "No active session"})
        
    try:
        # Look for the port number element
        port_elements = current_driver.find_elements(By.CSS_SELECTOR, "div.text-xs")
        for element in port_elements:
            if element.text.isdigit():  # Check if the text is a number (like "5173")
                print(f"Port number found: {element.text}")
                return jsonify({
                    "status": "ready",
                    "message": "Website is ready!"
                })
        
        return jsonify({
            "status": "in_progress",
            "message": "Website still generating..."
        })
    except Exception as e:
        print(f"Error checking website status: {e}")
        return jsonify({"status": "error", "message": str(e)})

# Create database tables
with app.app_context():
    db.create_all()  # This should be called when the app starts

if __name__ == '__main__':
    app.run(debug=True)