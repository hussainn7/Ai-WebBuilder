from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
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
from temp_mail import get_temp_email, perform_registration_and_verify, cleanup_driver  # Import from your existing script
from pathlib import Path
import subprocess
import sys

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
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
    if chat.user_id != current_user.id:
        return redirect(url_for('index'))
    
    messages = Message.query.filter_by(chat_id=chat_id)\
        .order_by(Message.timestamp.desc())\
        .limit(50)\
        .all()
    
    chats = Chat.query.filter_by(user_id=current_user.id)\
        .order_by(Chat.created_at.desc())\
        .limit(20)\
        .all()
    
    return render_template('index.html', 
                         current_chat=chat, 
                         current_chat_id=chat_id,
                         messages=messages[::-1],
                         chats=chats)

# Initialize driver path and options
driver_path = 'driver'
service = Service(driver_path)
chrome_options = Options()

def init_chrome_options():
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Create downloads directory if it doesn't exist
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'website_downloads')
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    # Modified download preferences to prompt for download location
    chrome_options.add_experimental_option(
        'prefs', {
            'download.prompt_for_download': True,  # Changed to True to show the prompt
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True,
            'profile.default_content_settings.popups': 0,
            'profile.default_content_setting_values.automatic_downloads': 1
        }
    )
    
    # Add additional permissions
    chrome_options.add_argument('--allow-file-access-from-files')
    chrome_options.add_argument('--allow-file-access')
    chrome_options.add_argument('--allow-cross-origin-auth-prompt')
    
    return chrome_options

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
    driver = webdriver.Chrome(service=service, options=chrome_options)
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
        print("Going in")

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
    global current_driver
    user_message = request.form['user_message']
    chat_id = request.form.get('chat_id')
    
    try:
        if not current_driver:
            print("Initializing new Chrome driver...")
            # Initialize Chrome driver without headless for download support
            chrome_options = init_chrome_options()
            service = Service('./driver')
            current_driver = webdriver.Chrome(service=service, options=chrome_options)
            current_driver.get("https://stackblitz.com/sign_in")
            print("On login page")
            
            # Login process
            wait = WebDriverWait(current_driver, 15)
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "login")))
            password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            
            # Load credentials from accounts.json
            account = load_account_details()
            if not account:
                return jsonify({"status": "error", "message": "No account credentials found"})
            
            print("Entering credentials...")
            email_field.send_keys(account["email"])
            password_field.send_keys(account["password"])
            password_field.send_keys(Keys.RETURN)
            time.sleep(2)  # Increased wait time
            
            print("Navigating to Bolt...")
            # Navigate to Bolt
            current_driver.get("https://bolt.new/?utm_campaign=stackblitz-on-page&utm_source=web-app&utm_medium=nav-button")
            time.sleep(2)  # Increased wait time

            print("Looking for sign-in button...")
            # Click the sign-in button if available
            try:
                sign_in_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.flex.rounded-md.items-center.justify-center"))
                )
                print("Sign-in button found and ready to click.")
                sign_in_button.click()
                print("Sign-in button clicked")
            except Exception as e:
                print(f"Button click failed or issue: {e}")

            time.sleep(3)  # Increased wait time

        print("Looking for textarea...")
        # First check if textarea is interactable
        wait = WebDriverWait(current_driver, 15)
        try:
            textarea = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.w-full.pl-4.pt-4.pr-16"))
            )
            
            # If textarea exists but is disabled, it means no prompts
            if not textarea.is_enabled():
                print("Textarea is disabled - no prompts available")
                return jsonify({
                    "status": "error",
                    "message": "No prompts available",
                    "ai_response": "Not working right now, wait a bit or create a new account"
                })
            
            print("Sending message...")
            # If we get here, textarea is enabled and we can send the message
            textarea.clear()
            textarea.send_keys(user_message)
            textarea.send_keys(Keys.RETURN)
            print("Message sent successfully!")
            
            # Save user message
            message = Message(content=user_message, is_user=True, chat_id=chat_id)
            db.session.add(message)
            db.session.commit()
            
            # Look for the last message in the chat
            messages = current_driver.find_elements(By.CSS_SELECTOR, ".message-list .message")
            if messages:
                ai_response = messages[-1].text  # Get the last message
                print(f"AI response received: {ai_response}")
            else:
                ai_response = "Message sent successfully! Your website will be ready in about 40 seconds. Please wait..."
                print("No AI response found, using default message")
            
            # Save AI response
            ai_message = Message(content=ai_response, is_user=False, chat_id=chat_id)
            db.session.add(ai_message)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "message": "Message sent!",
                "ai_response": ai_response,
                "start_timer": True  # Add this flag to start the timer
            })
            
        except Exception as e:
            print(f"Textarea interaction error: {e}")
            error_message = str(e)
            # If the error is about element not being interactable, it might be a timing issue
            if "element not interactable" in error_message.lower():
                return jsonify({
                    "status": "error",
                    "message": "Please wait a moment and try again",
                    "ai_response": "The chat is still loading. Please wait a few seconds and try again."
                })
            return jsonify({
                "status": "error",
                "message": "Error sending message",
                "ai_response": error_message
            })
        
    except Exception as e:
        print(f"Error in send_message: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "ai_response": "An error occurred while processing your request. Please try again."
        })

@app.route('/download_website', methods=['POST'])
@login_required
def download_website():
    global current_driver
    
    print("\n=== Starting Download Process ===")
    
    if not current_driver:
        return jsonify({"status": "error", "message": "No active session"})
    
    try:
        wait = WebDriverWait(current_driver, 15)
        
        # Set up download directory
        user_home = os.path.expanduser('~')
        download_dir = os.path.join(user_home, 'Downloads', 'website_downloads')
        os.makedirs(download_dir, exist_ok=True)
        print(f"Download directory: {download_dir}")

        # Set Chrome download preferences
        current_driver.execute_cdp_cmd('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': download_dir
        })
        
        print("Step 1: Looking for Export button...")
        export_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:export.text-lg"))
        )
        export_button.find_element(By.XPATH, "..").click()
        print("✓ Export button clicked")
        
        time.sleep(2)
        
        print("Step 2: Looking for Download button...")
        download_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.i-ph\\:download-simple.size-4\\.5"))
        )
        download_button.find_element(By.XPATH, "..").click()
        print("✓ Download button clicked")
        
        # Wait for download to complete
        time.sleep(10)  # Increased wait time
        
        # Find the downloaded file
        files = os.listdir(download_dir)
        zip_files = [f for f in files if f.endswith('.zip')]
        
        if not zip_files:
            print(f"Contents of {download_dir}:")
            print(os.listdir(download_dir))
            raise Exception("No zip file found in download directory")
            
        # Get the most recent zip file
        latest_zip = max([os.path.join(download_dir, f) for f in zip_files], 
                        key=os.path.getctime)
        
        print(f"Found zip file: {latest_zip}")
        
        return jsonify({
            "status": "success",
            "file_path": latest_zip,
            "message": "File ready for download"
        })
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to download: {str(e)}"
        })

@app.route('/get_website_file', methods=['GET'])
@login_required
def get_website_file():
    file_path = request.args.get('file_path')
    print(f"Attempting to send file: {file_path}")
    
    if not file_path or not os.path.exists(file_path):
        print(f"File not found at path: {file_path}")
        return jsonify({
            "status": "error",
            "message": "File not found"
        })
    
    try:
        # Send file to client
        response = send_file(
            file_path,
            as_attachment=True,
            download_name='website-project.zip',
            mimetype='application/zip'
        )
        
        print(f"File sent successfully: {file_path}")
        return response
        
    except Exception as e:
        print(f"Error sending file: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to send file"
        })
    finally:
        # Clean up after successful transfer
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
        except Exception as e:
            print(f"Cleanup error: {e}")

@app.route('/create_new_account', methods=['POST'])
@login_required
def create_new_account():
    global current_driver
    try:
        # Close any existing driver
        if current_driver:
            cleanup_driver(current_driver)
            current_driver = None

        # Check if accounts.json exists and is valid
        try:
            with open("accounts.json", "r") as file:
                existing_accounts = json.load(file)
                if len(existing_accounts) >= 10:  # Limit number of accounts
                    return jsonify({
                        "status": "error",
                        "message": "Maximum number of accounts reached. Please delete some old accounts."
                    })
        except (FileNotFoundError, json.JSONDecodeError):
            existing_accounts = []

        # Execute temp_mail.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, 'temp_mail.py')
        
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise Exception(f"Script failed with error: {result.stderr}")

        # Verify account creation
        with open("accounts.json", "r") as file:
            new_accounts = json.load(file)
            if len(new_accounts) > len(existing_accounts):
                return jsonify({
                    "status": "success",
                    "message": "New account created successfully!"
                })
            
        raise Exception("Account creation verification failed")
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "message": "Account creation timed out. Please try again."
        })
    except Exception as e:
        print(f"Error creating account: {e}")
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

@app.route('/download_project/<path:filename>')
@login_required
def download_project(filename):
    try:
        # Ensure the file exists
        if not os.path.exists(filename):
            return jsonify({
                "status": "error",
                "message": "Project file not found"
            })
            
        # Send file to user with download prompt
        return send_file(
            filename,
            as_attachment=True,
            download_name='website-project.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"Error sending file: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to download project"
        })
    finally:
        # Cleanup temporary file after sending
        try:
            os.remove(filename)
        except:
            pass

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()  # Initialize database tables
    app.run(debug=True)
