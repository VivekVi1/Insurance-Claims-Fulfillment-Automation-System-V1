# 🏥 AI Insurance Claims Fulfillment Automation System

A comprehensive microservices-based system for automated insurance claim processing using AI/LLM technology, email monitoring, and cloud storage integration.

## 🌟 Overview

This system automates the entire insurance claim submission and processing workflow:
- **Email Monitoring**: Automatically monitors Gmail for new claim submissions
- **User Validation**: Validates users against registered policy database
- **AI Assessment**: Uses AWS Bedrock LLM to assess claim completeness
- **Document Processing**: Handles attachments and extracts relevant information
- **Cloud Storage**: Uploads completed claims to AWS S3 with automatic local cleanup
- **Automated Communication**: Sends follow-up emails for incomplete claims

## 🏗️ Architecture

### Microservices Design
```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   Mail Monitor  │    │  User Validator  │    │  Fulfillment API  │
│   (Port: N/A)   │◄──►│   (Port: 8000)   │    │   (Port: 8002)    │
└─────────────────┘    └──────────────────┘    └───────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ Fulfillment     │    │   Mail Service   │    │    AWS Services   │
│ Processor       │◄──►│   (Port: 8001)   │    │  (S3 + Bedrock)   │
└─────────────────┘    └──────────────────┘    └───────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│   S3 Uploader   │    │    RDS MySQL     │    │ Local Attachments │
│                 │    │   (Database)     │    │   (Temporary)     │
└─────────────────┘    └──────────────────┘    └───────────────────┘
```

## ✨ Features

### 🤖 AI-Powered Processing
- **LLM Integration**: AWS Bedrock ( Amazon Nova Pro) for intelligent claim assessment
- **Requirement Validation**: Automatic verification of claim completeness
- **Smart Email Generation**: AI-generated follow-up emails for missing information

### 📧 Email Management
- **IMAP Monitoring**: Real-time Gmail monitoring with queue management
- **Attachment Processing**: Automatic download and processing of claim documents
- **SMTP Integration**: Automated email responses via Gmail

### ☁️ Cloud Integration
- **AWS S3**: Secure document storage with signed URLs
- **AWS Bedrock**: LLM services for AI processing
- **RDS MySQL**: Persistent data storage

### 🔄 Queue Management
- **Thread-Safe Processing**: Concurrent email processing with locks
- **Real-time Monitoring**: Queue size tracking and progress display
- **Error Handling**: Robust error recovery and logging

### 🛡️ Security
- **Environment Variables**: Secure credential management
- **Database Security**: Parameterized queries preventing SQL injection
- **Access Control**: API-based microservices architecture

## 🚀 Quick Start

### Prerequisites
- **Python 3.13 or higher**
- **MySQL Database** (AWS RDS recommended)
- **Gmail Account** with App Password
- **AWS Account** with S3 and Bedrock access

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "AI Insurance Claim Automation"
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   # OR using uv
   uv sync
   ```

3. **Set up environment**
   Create a `.env` file in the project root with the following configuration:
   ```bash
   # Copy the environment variables from the Configuration section below
   # Edit with your credentials
   ```

4. **Initialize database**
   ```sql
   -- Run the SQL scripts in your MySQL database
   -- See Database Setup section below
   ```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:

```bash
# Database Configuration
RDS_HOST=your-rds-endpoint.region.rds.amazonaws.com
RDS_USER=your-db-username
RDS_PASSWORD=your-db-password
RDS_DATABASE=your-database-name
RDS_PORT=3306

# Email Configuration
EMAIL_USERNAME=your-email@gmail.com
EMAIL_APP_PASSWORD=your-gmail-app-password

# AWS Configuration
AWS_REGION=us-east-1
# Default model: Amazon Nova Pro 
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
# For Claude: BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0
S3_BUCKET_NAME=your-s3-bucket-name
S3_PREFIX=AI_insurance_claim

# API Endpoints
FASTAPI_BASE_URL=http://localhost:8000
MAIL_SERVICE_URL=http://localhost:8001
FULFILLMENT_API_URL=http://localhost:8002
```

### Database Setup

```sql
-- User Details Table
CREATE TABLE user_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mail_id VARCHAR(255) NOT NULL UNIQUE,
    policy_issued_date DATE NOT NULL,
    policy_type VARCHAR(100) NOT NULL
);

-- Mail Tracking Table
CREATE TABLE last_mail_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mail_count INT NOT NULL,
    last_connection_time DATETIME NOT NULL
);

-- Fulfillment Table
CREATE TABLE fulfillment (
    fulfillment_id VARCHAR(50) PRIMARY KEY,
    user_mail VARCHAR(255) NOT NULL,
    claim_id VARCHAR(100) NOT NULL,
    mail_content TEXT,
    mail_content_s3_url TEXT,
    attachment_count INT DEFAULT 0,
    attachment_s3_urls JSON,
    local_attachment_paths JSON,
    fulfillment_status ENUM('pending', 'completed') NOT NULL,
    missing_items TEXT,
    s3_upload_timestamp DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_mail (user_mail),
    INDEX idx_claim_id (claim_id),
    INDEX idx_fulfillment_status (fulfillment_status)
);
```

## 🎯 Usage

### Running the System

#### Option 1: Automated Startup (Recommended)
```bash
# Start all services with one command
python start_system.py
```
This will:
- Check all prerequisites
- Start all API services in the correct order
- Monitor service health
- Start the mail monitor
- Handle graceful shutdown on exit

#### Option 2: Manual Startup
1. **Start all APIs** (in separate terminals):
```bash
# Terminal 1: User Validator
python apis/user_validator.py
 
# Terminal 2: Mail Service  
python apis/mail_service.py
 
# Terminal 3: Fulfillment API
python apis/fulfillment_api.py
```

2. **Start the main monitor**:
```bash
# Terminal 4: Mail Monitor
python mail_monitor.py
```

### Streamlit Dashboard

A minimalist dashboard for system monitoring is included.

```bash
# Ensure dependencies are installed
uv sync  # or: pip install -e .

# Start backend services first
python start_system.py

# In a new terminal, run the dashboard
streamlit run dashboard.py
```

The dashboard (available at http://localhost:8501) provides:
- **Overview**: Core metrics and recent claims
- **Claims**: View and filter claim data
- **Users**: View registered users
- **System**: API and email status

For detailed instructions, see `RUN_INSTRUCTIONS.md`.


### System Workflow

1. **📧 Email Arrives**: System detects new emails in Gmail
2. **👤 User Validation**: Checks if sender is registered user
3. **📄 Document Processing**: Downloads and processes attachments
4. **🤖 AI Assessment**: LLM evaluates claim completeness
5. **✅ Complete Claims**: 
   - Uploads to S3
   - Saves to database
   - Cleans up local files
6. **⏳ Incomplete Claims**:
   - Generates follow-up email
   - Saves pending status
   - Requests missing information

## 📚 API Documentation

### User Validator API (Port 8000)
```http
GET /user/{email}
```
**Response**: User details or not found status

### Mail Service API (Port 8001)  
```http
GET /                    # Health check
POST /send-mail         # Send email
```
**Body**: `{"mail_id": "user@example.com", "subject": "...", "mail_content": "..."}`

### Fulfillment API (Port 8002)
```http
GET /                    # Database connection test
POST /add-fulfillment   # Save fulfillment data
```
**Body**: Fulfillment request with claim details and S3 URLs

## 📁 Project Structure

```
AI Insurance Claim Automation/
├── 📁 apis/                    # FastAPI microservices
│   ├── user_validator.py       # User lookup service
│   ├── mail_service.py         # Email sending service
│   └── fulfillment_api.py      # Database operations service
├── 📁 prompts/                 # AI prompts and email templates
│   ├── fulfillment_system_prompt.txt
│   ├── fulfillment_requirements.txt
│   ├── fulfillment_pending_email.txt
│   ├── user_not_found_email.txt
│   └── user_not_found_fallback.txt
├── 📁 attachments/             # Temporary file storage
├── 📁 assests/                 # Sample files for testing
├── mail_monitor.py             # Main email monitoring service
├── fulfillment_processor.py    # AI processing and orchestration
├── s3_uploader.py              # AWS S3 integration
├── start_system.py             # Automated startup script
├── pyproject.toml              # Project dependencies
└── README.md                   # This file
```

## 🔧 Key Components

### Mail Monitor (`mail_monitor.py`)
- **IMAP Connection**: Connects to Gmail via IMAP
- **Queue Management**: Thread-safe email queue with size tracking
- **Real-time Processing**: Continuous monitoring every 30 seconds
- **User Validation Integration**: API calls to user validator

### Fulfillment Processor (`fulfillment_processor.py`)
- **LLM Integration**: AWS Bedrock integration (Amazon Nova Pro)
- **Requirement Analysis**: Validates claim completeness
- **Email Generation**: Creates follow-up emails for incomplete claims
- **S3 Integration**: Uploads completed claims to cloud storage

### S3 Uploader (`s3_uploader.py`)
- **Document Upload**: Handles mail content and attachments
- **Signed URLs**: Generates secure access URLs
- **Metadata Management**: Tracks upload timestamps and file info

### API Services (`apis/`)
- **Microservices Architecture**: Independent, scalable services
- **Database Abstraction**: Centralized data operations
- **Clean Interfaces**: RESTful API design

## 🛠️ Development

### Testing
```bash
# Test individual APIs
curl http://localhost:8000/user/test@example.com
curl http://localhost:8001/
curl http://localhost:8002/
```

### Debugging
- **Queue Monitoring**: Real-time queue size display in logs
- **Detailed Logging**: Comprehensive error and status messages
- **API Health Checks**: Individual service status monitoring

### Adding New Features
1. **New Prompts**: Add `.txt` files to `prompts/` folder
2. **API Extensions**: Extend services in `apis/` folder
3. **LLM Modifications**: Update `fulfillment_processor.py`

## 🔐 Security Considerations

- **Environment Variables**: Never commit `.env` files
- **Database Security**: Use parameterized queries only
- **API Security**: Consider adding authentication for production
- **AWS Credentials**: Use IAM roles and temporary credentials
- **Email Security**: Use app passwords, not account passwords

## 📊 Monitoring & Metrics

- **Queue Size Tracking**: Real-time processing queue monitoring
- **Email Processing Stats**: Success/failure rate tracking  
- **S3 Upload Metrics**: Storage usage and upload success rates
- **Database Operations**: Transaction logging and error tracking

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check RDS endpoint and credentials
   - Verify security group settings
   - Test database connectivity

2. **Email Authentication Failed**
   - Ensure Gmail App Password is used
   - Check 2FA settings
   - Verify IMAP is enabled

3. **AWS Services Not Working**
   - Check AWS credentials and permissions
   - Verify S3 bucket exists and is accessible
   - Ensure Bedrock model access is enabled

4. **Queue Processing Stuck**
   - Monitor queue size in logs
   - Check for API service availability
   - Verify fulfillment processor status

## 📈 Performance Optimization

- **Concurrent Processing**: Queue-based email processing
- **API Caching**: Consider Redis for frequently accessed data
- **S3 Optimization**: Batch uploads for better performance
- **Database Indexing**: Optimized queries with proper indexes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request with detailed description

## 📝 License

[Add your license information here]

## 🙋‍♂️ Support

For issues and questions:
- Check troubleshooting section above
- Review logs for detailed error messages
- Ensure all environment variables are properly configured

---

**Built with ❤️ using Python, FastAPI, AWS Bedrock, and modern microservices architecture.** 
