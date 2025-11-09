import os
import imaplib
import email
import ssl
import time
import pymysql
import uuid
import requests
from datetime import datetime
from queue import Queue
from threading import Lock
from email.header import decode_header
from dotenv import load_dotenv
from fulfillment_processor import FulfillmentProcessor

load_dotenv()

class MailMonitor:
    def __init__(self):
        self.username = os.getenv("EMAIL_USERNAME")
        self.app_password = os.getenv("EMAIL_APP_PASSWORD")
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.mail_connection = None
        self.db_connection = None
        self.email_queue = Queue()
        self.queue_lock = Lock()
        self.fulfillment_processor = FulfillmentProcessor()
        
        # API endpoints
        self.fastapi_base_url = os.getenv('FASTAPI_BASE_URL', 'http://localhost:8000')
        self.mail_service_url = os.getenv('MAIL_SERVICE_URL', 'http://localhost:8001')
        
        # Prompts folder
        self.prompts_folder = os.path.join(os.path.dirname(__file__), 'prompts')
        
    def load_prompt_file(self, filename):
        """Load content from prompt file"""
        try:
            file_path = os.path.join(self.prompts_folder, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"[ERROR] Error loading prompt file {filename}: {e}")
            return None
        
    def connect_to_database(self):
        """Connect to RDS database"""
        try:
            self.db_connection = pymysql.connect(
                host=os.getenv('RDS_HOST'),
                port=int(os.getenv('RDS_PORT', 3306)),
                user=os.getenv('RDS_USER'),
                password=os.getenv('RDS_PASSWORD'),
                database=os.getenv('RDS_DATABASE'),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("[OK] Database connection established")
            return True
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
    
    def connect_to_mail_server(self):
        """Connect to Gmail IMAP server"""
        try:
            context = ssl.create_default_context()
            self.mail_connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, ssl_context=context)
            self.mail_connection.login(self.username, self.app_password)
            
            status, messages = self.mail_connection.select("inbox")
            if status != 'OK':
                print("[ERROR] Failed to select inbox")
                return False
            
            print("[OK] Mail server connection established")
            return True
        except Exception as e:
            print(f"[ERROR] Mail server connection failed: {e}")
            return False
    
    def check_user_registration(self, email_address):
        """Check if user is registered using FastAPI endpoint"""
        try:
            print(f"[INFO] Checking user registration for: {email_address}")
            
            # Call FastAPI endpoint
            response = requests.get(f"{self.fastapi_base_url}/user/{email_address}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') == True:
                    user_data = data.get('data', {})
                    print(f"[OK] User registered - ID: {user_data.get('id')}, Policy: {user_data.get('policy_type')}")
                    return True, user_data
                else:
                    print(f"[ERROR] User not registered: {data.get('message', 'User not found')}")
                    return False, None
            else:
                print(f"[ERROR] API call failed with status {response.status_code}")
                return False, None
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error calling user registration API: {e}")
            return False, None
        except Exception as e:
            print(f"[ERROR] Unexpected error during user check: {e}")
            return False, None
    
    def send_unregistered_user_email_via_service(self, to_email, claim_id):
        """Send email to unregistered user via mail service"""
        try:
            # Load email template from file
            email_template = self.load_prompt_file('user_not_found_email.txt')
            
            if not email_template:
                # Try fallback template
                email_template = self.load_prompt_file('user_not_found_fallback.txt')
            
            if email_template:
                # Parse subject and content from template
                lines = email_template.split('\n')
                subject = lines[0].replace('Subject: ', '') if lines[0].startswith('Subject: ') else "Insurance Claim - Registration Required"
                
                # Get content after subject line and empty line
                content_start = 2 if len(lines) > 1 and lines[1] == '' else 1
                email_content = '\n'.join(lines[content_start:])
                
                # Format template with variables
                email_content = email_content.format(claim_id=claim_id, user_email=to_email)
            else:
                # Last resort: minimal fallback
                subject = "Insurance Claim - Registration Required"
                email_content = f"Dear Customer,\n\nYour email {to_email} is not registered in our system.\n\nClaim Reference: {claim_id}\n\nPlease contact customer service.\n\nBest regards,\nInsurance Claims Team"
            
            print(f"[EMAIL] Sending unregistered user email via mail service to: {to_email}")
            
            mail_request = {
                "mail_id": to_email,
                "subject": subject,
                "mail_content": email_content
            }
            
            response = requests.post(
                f"{self.mail_service_url}/send-mail",
                json=mail_request,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"[OK] Unregistered user notification sent via mail service to {to_email}")
                return True
            else:
                print(f"[ERROR] Mail service failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error calling mail service: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Error sending unregistered user email: {e}")
            return False
    
    def get_current_mail_count(self):
        """Get current mail count from mail server"""
        try:
            status, messages = self.mail_connection.select("inbox")
            if status == 'OK':
                mail_count = int(messages[0])
                print(f"[EMAIL] Current mail count: {mail_count}")
                return mail_count
            return 0
        except Exception as e:
            print(f"[ERROR] Error getting mail count: {e}")
            return 0
    
    def get_stored_mail_details(self):
        """Get last mail count and connection time from database"""
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute("SELECT mail_count, last_connection_time FROM last_mail_details_vv ORDER BY id DESC LIMIT 1")
                result = cursor.fetchone()
                
                if result:
                    print(f"[DATA] Stored mail details - Count: {result['mail_count']}, Last connection: {result['last_connection_time']}")
                    return result['mail_count'], result['last_connection_time']
                else:
                    print("[DATA] No previous mail details found in database")
                    return 0, None
        except Exception as e:
            print(f"[ERROR] Error getting stored mail details: {e}")
            return 0, None
    
    def update_mail_details(self, mail_count):
        """Update mail count and connection time in database"""
        try:
            current_time = datetime.now()
            with self.db_connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO last_mail_details_vv (mail_count, last_connection_time) VALUES (%s, %s)",
                    (mail_count, current_time)
                )
                self.db_connection.commit()
                print(f"[OK] Updated database - Mail count: {mail_count}, Time: {current_time}")
                return True
        except Exception as e:
            print(f"[ERROR] Error updating mail details: {e}")
            return False
    
    def process_email_attachments(self, msg, claim_id):
        """Extract and save email attachments"""
        attachment_paths = []
        save_path = os.getenv('LOCAL_ATTACHMENTS_FOLDER', 'attachments')
        
        # Create claim-specific folder
        claim_folder = os.path.join(save_path, claim_id)
        if not os.path.exists(claim_folder):
            os.makedirs(claim_folder)
            print(f"[FILE] Created folder: {claim_folder}")
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get('Content-Disposition'))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        try:
                            # Decode filename if encoded
                            decoded_filename, charset = decode_header(filename)[0]
                            if charset:
                                filename = decoded_filename.decode(charset)
                            else:
                                filename = str(decoded_filename)
                            
                            # Create unique filename with timestamp
                            timestamp = str(int(time.time() * 1000))
                            unique_filename = f"{timestamp}_{filename}"
                            file_path = os.path.join(claim_folder, unique_filename)
                            
                            # Save attachment
                            with open(file_path, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            
                            attachment_paths.append(file_path)
                            print(f"[FILE] Saved attachment: {unique_filename}")
                            
                        except Exception as e:
                            print(f"[ERROR] Error saving attachment {filename}: {e}")
        
        return attachment_paths
    
    def extract_email_content(self, msg):
        """Extract email content from message"""
        email_content = "No content found"
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        email_content = payload.decode('utf-8', errors='ignore')
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                email_content = payload.decode('utf-8', errors='ignore')
        
        return email_content
    
    def fetch_new_mails_to_queue(self, stored_count, current_count):
        """Fetch new mails and add to queue"""
        try:
            new_mail_count = current_count - stored_count
            print(f"[EMAIL] Processing {new_mail_count} new mails")
            
            # Get the UIDs of new mails (last N mails)
            status, email_ids = self.mail_connection.search(None, "ALL")
            if status != 'OK':
                print("[ERROR] Failed to search emails")
                return False
            
            email_id_list = email_ids[0].split() if email_ids[0] else []
            
            # Get only the new mails (last N mails)
            new_mail_ids = email_id_list[-new_mail_count:] if new_mail_count > 0 else []
            
            for email_id_bytes in new_mail_ids:
                email_id_str = email_id_bytes.decode('utf-8')
                
                try:
                    # Fetch email details
                    status, data = self.mail_connection.fetch(email_id_str, "(RFC822)")
                    if status != 'OK':
                        continue
                    
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extract email details
                    subject_header = msg.get("Subject", "No Subject")
                    subject, _ = decode_header(subject_header)[0]
                    subject = subject.decode('utf-8', errors='ignore') if isinstance(subject, bytes) else str(subject)
                    
                    from_header = msg.get("From", "Unknown Sender")
                    sender, _ = decode_header(from_header)[0]
                    sender = sender.decode('utf-8', errors='ignore') if isinstance(sender, bytes) else str(sender)
                    sender_email = email.utils.parseaddr(sender)[1]
                    
                    # Generate claim ID for this email
                    unique_id = str(uuid.uuid4()).replace('-', '').upper()[:8]
                    date_str = datetime.now().strftime("%Y%m%d")
                    claim_id = f"CLAIM_{unique_id}_{date_str}"
                    
                    # Extract email content
                    email_content = self.extract_email_content(msg)
                    
                    # Process attachments
                    attachment_paths = self.process_email_attachments(msg, claim_id)
                    
                    # Add to queue
                    email_data = {
                        'email_id': email_id_str,
                        'sender_email': sender_email,
                        'subject': subject,
                        'content': email_content,
                        'claim_id': claim_id,
                        'attachment_paths': attachment_paths,
                        'attachment_count': len(attachment_paths),
                        'timestamp': datetime.now()
                    }
                    
                    with self.queue_lock:
                        self.email_queue.put(email_data)
                        queue_size = self.email_queue.qsize()
                    
                    print(f"[EMAIL] Added email to queue - From: {sender_email}, Subject: {subject[:30]}..., Attachments: {len(attachment_paths)} | Queue Size: {queue_size}")
                    
                except Exception as e:
                    print(f"[ERROR] Error processing email {email_id_str}: {e}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error fetching new mails: {e}")
            return False
    
    def process_email_queue(self):
        """Process emails from queue with user validation and fulfillment processor"""
        processed_count = 0
        
        print(f"[QUEUE] Starting queue processing - Queue Size: {self.email_queue.qsize()}")
        
        while not self.email_queue.empty():
            try:
                with self.queue_lock:
                    email_data = self.email_queue.get_nowait()
                    remaining_queue_size = self.email_queue.qsize()
                
                print("\n" + "="*60)
                print(f"[PROCESS] PROCESSING EMAIL #{processed_count + 1} | Remaining in Queue: {remaining_queue_size}")
                print("="*60)
                print(f"[EMAIL] Email ID: {email_data['email_id']}")
                print(f"[EMAIL] Sender Email: {email_data['sender_email']}")
                print(f"[EMAIL] Subject: {email_data['subject']}")
                print(f"[EMAIL] Claim ID: {email_data['claim_id']}")
                print(f"[EMAIL] Attachment Count: {email_data['attachment_count']}")
                print("="*60)
                
                # Step 1: Check user registration via FastAPI
                is_registered, user_data = self.check_user_registration(email_data['sender_email'])
                
                if not is_registered:
                    print(f"[ERROR] User not registered - sending rejection email via mail service")
                    
                    # Send unregistered user email via mail service
                    email_sent = self.send_unregistered_user_email_via_service(
                        email_data['sender_email'], 
                        email_data['claim_id']
                    )
                    
                    if email_sent:
                        print(f"[OK] Rejection email sent to unregistered user: {email_data['sender_email']}")
                        processed_count += 1
                    else:
                        print(f"[ERROR] Failed to send rejection email to {email_data['sender_email']}")
                    
                    # Skip LLM processing for unregistered users
                    continue
                
                # Step 2: User is registered - proceed with LLM fulfillment processing
                print(f"[OK] User registered - proceeding with fulfillment assessment")
                print(f"[INFO] User Info: {user_data.get('policy_type', 'N/A')} policy issued on {user_data.get('policy_issued_date', 'N/A')}")
                
                success = self.fulfillment_processor.process_email_fulfillment(email_data)
                
                if success:
                    print(f"[OK] Email {processed_count + 1} processed successfully through fulfillment assessment")
                else:
                    print(f"[ERROR] Failed to process email {processed_count + 1} in fulfillment assessment")
                
                processed_count += 1
                
                # Add delay between processing
                time.sleep(1)
                
            except Exception as e:
                print(f"[ERROR] Error processing email from queue: {e}")
                break
        
        final_queue_size = self.email_queue.qsize()
        if processed_count > 0:
            print(f"\n[OK] Processed {processed_count} emails with user validation and fulfillment assessment | Final Queue Size: {final_queue_size}")
        else:
            print(f"\n[EMAIL] No emails to process in queue | Queue Size: {final_queue_size}")
    
    def monitor_mails(self):
        """Main monitoring loop"""
        print("[START] Starting Mail Monitor with User Validation + Fulfillment Assessment")
        print("="*70)
        
        # Connect to database and mail server
        if not self.connect_to_database():
            return False
        
        if not self.connect_to_mail_server():
            return False
        
        try:
            while True:
                print(f"\n[CHECK] Checking for new mails at {datetime.now()} | Current Queue Size: {self.email_queue.qsize()}")
                
                # Get current mail count from server
                current_mail_count = self.get_current_mail_count()
                
                # Get stored mail count from database
                stored_mail_count, last_connection_time = self.get_stored_mail_details()
                
                print(f"[DATA] Comparison - Stored: {stored_mail_count}, Current: {current_mail_count}")
                
                # Check if this is the first run (database is empty)
                if last_connection_time is None:
                    print("[NEW] First run detected - initializing mail count without processing existing emails")
                    self.update_mail_details(current_mail_count)
                    print(f"[OK] Initialized database with current mail count: {current_mail_count}")
                    print("[EMAIL] Will start monitoring for new emails from next check onwards")
                    
                # Check if there are new mails
                elif current_mail_count > stored_mail_count:
                    print(f"[NEW] Found {current_mail_count - stored_mail_count} new mails!")
                    
                    # Fetch new mails and add to queue
                    if self.fetch_new_mails_to_queue(stored_mail_count, current_mail_count):
                        # Update database with new count
                        self.update_mail_details(current_mail_count)
                        
                        # Process emails from queue with user validation + fulfillment assessment
                        print(f"[PROCESS] Starting user validation and fulfillment assessment for {self.email_queue.qsize()} emails")
                        self.process_email_queue()
                    
                else:
                    print("[EMAIL] No new mails found")
                
                print("[WAIT] Waiting 30 seconds before next check...")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\n[STOP] Mail monitoring stopped by user")
            return True
        except Exception as e:
            print(f"[ERROR] Monitoring error: {e}")
            return False
        finally:
            # Close connections
            if self.mail_connection:
                try:
                    self.mail_connection.close()
                    self.mail_connection.logout()
                except:
                    pass
            
            if self.db_connection:
                self.db_connection.close()
            
            print("[CLOSE] All connections closed")

if __name__ == "__main__":
    monitor = MailMonitor()
    monitor.monitor_mails() 