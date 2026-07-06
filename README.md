# Yelp Business Scraper

A full-stack web application for scraping business listings from Yelp. Features a Python + Selenium backend for web scraping, FastAPI REST API, and a modern web frontend for easy interaction.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Frontend Usage](#frontend-usage)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### Data Extraction
Collects comprehensive business information from Yelp searches:
- **Business Niche** — the search term used (e.g., "restaurants", "plumbers")
- **Company Name** — business name
- **Location: USA** — full address (street, city, state, zip)
- **Phone Number** — contact number
- **Yelp URL** — link to Yelp business page
- **Website URL** — external business website

### Smart Features
- **De-duplication & Append Mode** — merge results into existing CSV, keyed on Yelp URL
- **CAPTCHA Handling** — automatic warm-up with manual one-time solve for DataDome protection
- **Realistic Browsing** — randomized delays and undetected-chromedriver to avoid detection
- **Graceful Stopping** — saves collected results when interrupted
- **Pagination** — automatically collects results across multiple pages until max limit reached

### Frontend Features
- Web-based dashboard for easy operation
- Real-time scraping progress monitoring
- Job history and result management
- Admin panel for user management
- Responsive design for desktop and mobile

### Backend Features
- RESTful API for scraper control
- Job queue system for async scraping
- User authentication and authorization
- Database persistence for results and history
- Comprehensive error handling and logging

## 🏗️ Architecture

### Tech Stack
- **Backend**: FastAPI, SQLite/PostgreSQL, Pydantic
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Scraping**: Selenium 4, undetected-chromedriver
- **Server**: Uvicorn (ASGI application server)

### Project Structure
```
.
├── backend/                    # FastAPI backend
│   ├── main.py                # Application entry point
│   ├── routes.py              # API endpoints
│   ├── auth_routes.py         # Authentication endpoints
│   ├── models.py              # Database models
│   ├── schemas.py             # Pydantic schemas
│   ├── crud.py                # Database operations
│   ├── database.py            # Database configuration
│   ├── auth.py                # Authentication logic
│   ├── config.py              # Backend settings
│   ├── jobs.py                # Job queue system
│   └── _jobs/                 # Job execution logs
├── web/                       # Frontend (static files)
│   ├── index.html             # Main dashboard
│   ├── admin.html             # Admin panel
│   ├── dashboard.html         # Results view
│   ├── css/                   # Stylesheets
│   └── js/                    # JavaScript modules
├── scraper.py                 # Selenium-based Yelp scraper
├── gui.py                     # Desktop GUI (tkinter)
├── config.json                # Scraper configuration
├── CLAUDE.md                  # Project documentation
└── README.md                  # This file
```

## 💻 System Requirements

- **Python**: 3.10 or higher
- **OS**: Windows, macOS, or Linux
- **Browser**: Google Chrome (latest stable version)
- **RAM**: 2GB minimum recommended
- **Storage**: ~500MB for dependencies and cache

### Dependencies
- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `sqlalchemy` — ORM for database
- `pydantic` — Data validation
- `selenium` — Browser automation
- `undetected-chromedriver` — Anti-detection for web scraping
- `python-jose` — JWT authentication
- `passlib` — Password hashing

## 📦 Installation

### 1. Clone or Download the Project
```bash
cd "C:\Users\Dell\Desktop\Scraper Manual Tool v12"
```

### 2. Create a Virtual Environment
```powershell
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Initialize Database
```bash
# Create admin user and initialize schema
python create_admin.py
```

### 4. Environment Configuration
Create or update `.env` file with your settings:
```env
DATABASE_URL=sqlite:///./scraper.db
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
HEADLESS=false
```

## 🚀 Running the Application

### Backend Server
Start the FastAPI server on port 8000:
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

**Parameters explained:**
- `backend.main:app` — module path to the FastAPI application instance
- `--reload` — auto-restart on code changes (development only; remove for production)
- `--port 8000` — serve on localhost:8000

**Access the backend:**
- **API Base URL**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc (ReDoc)

### Frontend Server
Open the web interface in your browser:
```bash
# Option 1: Serve from backend (recommended)
# Frontend is automatically served at http://localhost:8000/

# Option 2: Open directly
open web/index.html
# or in Windows
start web\index.html
```

### Desktop GUI (Legacy)
For the tkinter-based GUI:
```bash
python gui.py
```

## 📡 API Documentation

### Authentication
All API endpoints (except `/auth/login`) require Bearer token authentication.

**Login to get token:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {"id": 1, "username": "admin"}
}
```

**Use token in requests:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/jobs
```

### Core Endpoints

#### Start Scraping Job
```bash
POST /api/jobs/start
Authorization: Bearer <token>

{
  "search_term": "restaurants",
  "location": "San Francisco, CA",
  "max_results": 50,
  "headless": false,
  "append": true
}
```

Response:
```json
{
  "id": "job_123abc",
  "status": "running",
  "search_term": "restaurants",
  "location": "San Francisco, CA",
  "created_at": "2026-07-01T12:00:00Z",
  "progress": 0
}
```

#### Get Job Status
```bash
GET /api/jobs/{job_id}
Authorization: Bearer <token>
```

Response:
```json
{
  "id": "job_123abc",
  "status": "completed",
  "search_term": "restaurants",
  "location": "San Francisco, CA",
  "created_at": "2026-07-01T12:00:00Z",
  "completed_at": "2026-07-01T12:15:30Z",
  "progress": 100,
  "results_count": 45
}
```

#### List All Jobs
```bash
GET /api/jobs
Authorization: Bearer <token>

Query params:
  ?limit=10
  ?offset=0
  ?status=completed
```

#### Get Scraped Results
```bash
GET /api/results?job_id={job_id}
Authorization: Bearer <token>

Response: CSV download or JSON array
```

#### Stop Running Job
```bash
POST /api/jobs/{job_id}/stop
Authorization: Bearer <token>
```

For complete API documentation, visit http://localhost:8000/docs after starting the server.

## 🖥️ Frontend Usage

### Dashboard
1. Navigate to http://localhost:8000/
2. Login with your credentials
3. Enter search parameters:
   - **Search Term**: What to search for (e.g., "plumbers", "restaurants")
   - **Location**: City and state (e.g., "Austin, TX")
   - **Max Results**: Number of results to collect (1-1000)
4. Click **"Start Scraping"** to begin
5. Monitor progress in real-time
6. Download results as CSV when complete

### Admin Panel
Access admin features at http://localhost:8000/admin.html

**Capabilities:**
- Manage user accounts
- View system logs
- Configure scraper settings
- Monitor active jobs
- Review scraping history

### Results Management
- **Download**: Export results to CSV with proper UTF-8 encoding
- **Filter**: Search by date, location, or status
- **Review**: Inspect individual results before export
- **Append Mode**: Automatically merge with existing data

## ⚙️ Configuration

### config.json
Main scraper configuration file:
```json
{
  "search_term": "restaurants",
  "location": "San Francisco, CA",
  "max_results": 10,
  "headless": false,
  "output_csv": "output.csv",
  "append": true,
  "page_load_timeout": 30,
  "delay_min": 12.0,
  "delay_max": 15.0,
  "page_settle_delay": 10.0
}
```

**Parameters:**
- `search_term` — Default search query
- `location` — Default location
- `max_results` — Maximum businesses to collect per search
- `headless` — Run without visible Chrome window (false recommended; can't solve CAPTCHA in headless mode)
- `append` — Merge with existing CSV (true) or overwrite (false)
- `page_load_timeout` — Seconds to wait for page load
- `delay_min/delay_max` — Random pause between requests (raise if getting blocked)
- `page_settle_delay` — Time to wait for dynamic content to load

### Backend Environment (.env)
```env
# Database
DATABASE_URL=sqlite:///./scraper.db

# Security
SECRET_KEY=your-very-long-random-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Scraper behavior
HEADLESS=false
CHROME_PROFILE_PATH=.chrome-profile
```

## 🎯 Best Practices

### Development
1. **Use virtual environment** — isolate dependencies
2. **Enable reload mode** — faster iteration
3. **Check API docs** — visit `/docs` endpoint
4. **Monitor logs** — watch backend console output
5. **Test endpoints** — use Swagger UI or Postman

### Production Deployment
1. **Disable reload** — remove `--reload` flag
2. **Set workers** — `uvicorn backend.main:app --workers 4 --port 8000`
3. **Use strong SECRET_KEY** — `openssl rand -hex 32`
4. **Enable HTTPS** — deploy behind reverse proxy (nginx/Caddy)
5. **Database** — migrate from SQLite to PostgreSQL
6. **Logging** — configure structured logging
7. **Monitoring** — set up health checks and alerts

### Scraper Usage
1. **Respect ToS** — Yelp prohibits automated scraping; keep volumes low
2. **Handle CAPTCHA** — solve manually when prompted (non-headless mode only)
3. **Adjust delays** — increase `delay_min/delay_max` if getting blocked
4. **Use append mode** — avoid duplicate requests and reduce load
5. **Persistent profile** — Chrome profile in `.chrome-profile/` stores clearance cookies

### Security
1. **Change default password** — update admin credentials
2. **Rotate secrets** — update SECRET_KEY periodically
3. **Rate limiting** — implement in production
4. **CORS configuration** — restrict frontend origin
5. **Input validation** — trust Pydantic schemas
6. **SQL injection** — use SQLAlchemy ORM (not raw queries)

## 🔧 Troubleshooting

### CAPTCHA Blocking
**Issue**: "Verify you are a human" challenge appears.

**Solution**:
- Run in non-headless mode (`headless: false`)
- Solve CAPTCHA manually in the Chrome window
- Clearance cookie is saved in `.chrome-profile/` for reuse
- The scraper will continue automatically after solving

### Connection Refused
**Issue**: Cannot connect to `http://localhost:8000`.

**Solution**:
```bash
# Verify backend is running
python -m uvicorn backend.main:app --reload --port 8000

# Check if port is in use
netstat -an | find ":8000"

# Use different port if needed
python -m uvicorn backend.main:app --reload --port 8001
```

### Database Locked
**Issue**: SQLite database locked error.

**Solution**:
```bash
# Migrate to PostgreSQL for production
# Or ensure single uvicorn process (no workers in dev mode)

# For SQLite, remove workers flag:
python -m uvicorn backend.main:app --reload --port 8000
```

### Being Blocked by Yelp
**Issue**: Getting blocked on searches (empty results or CAPTCHA spam).

**Solution**:
1. Increase delays in `config.json`:
   ```json
   {
     "delay_min": 20.0,
     "delay_max": 30.0
   }
   ```
2. Use proxy rotation (not included; requires external service)
3. Reduce max_results per search
4. Wait 24 hours before retrying
5. Check compliance with Yelp ToS

### Chrome Driver Issues
**Issue**: WebDriver or Chrome version mismatch.

**Solution**:
```bash
# Selenium Manager handles this automatically
# If it fails, try updating:
pip install --upgrade selenium

# Or specify Chrome path explicitly in config:
CHROME_PATH=/path/to/chrome
```

### Memory Usage High
**Issue**: Scraper consuming too much memory.

**Solution**:
- Reduce `max_results` per search
- Stop background Chrome processes: `taskkill /F /IM chrome.exe`
- Reduce number of concurrent jobs
- Use headless mode (saves resources)

### Frontend Not Loading
**Issue**: Blank page or 404 errors.

**Solution**:
- Verify backend is running: `http://localhost:8000/docs`
- Check browser console for errors (F12)
- Clear browser cache: Ctrl+Shift+Delete
- Verify `web/` directory exists with HTML files
- Check CORS configuration in backend settings

## 📚 Additional Resources

- **Yelp ToS**: https://www.yelp.com/terms
- **Selenium Docs**: https://www.selenium.dev/documentation/
- **FastAPI Guide**: https://fastapi.tiangolo.com/
- **Uvicorn Guide**: https://www.uvicorn.org/
- **SQLAlchemy ORM**: https://docs.sqlalchemy.org/

## 📝 API Examples

### Example: Complete Scraping Workflow

```bash
# 1. Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access_token')

# 2. Start a scraping job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/jobs/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "search_term":"restaurants",
    "location":"Austin, TX",
    "max_results":30,
    "headless":false,
    "append":true
  }' | jq -r '.id')

# 3. Poll job status
for i in {1..60}; do
  curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/jobs/$JOB_ID \
    | jq '.status, .progress'
  sleep 5
done

# 4. Download results when complete
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/results?job_id=$JOB_ID" \
  -o results.csv
```

## 🤝 Support & Feedback

For issues, suggestions, or questions:
- Check troubleshooting section above
- Review CLAUDE.md for project-specific details
- Examine API documentation at `/docs` endpoint
- Check backend logs for detailed error messages

## 📄 License

This project is provided as-is. Note that web scraping Yelp may violate their Terms of Service.

---

**Last Updated**: 2026-07-01  
**Version**: 1.0.0
