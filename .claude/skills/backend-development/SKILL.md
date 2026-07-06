---
name: backend-development
description: Build production-grade backend APIs with Python and FastAPI, following industry best practices for architecture, security, testing, and performance. Use this skill when writing FastAPI services, building REST APIs, designing database schemas, implementing authentication/authorization, or designing backend systems (examples include API endpoints, middleware, services, database integration, async workers, or any backend logic).
license: Complete terms in LICENSE.txt
---

This skill guides the creation of production-grade backend systems using Python and FastAPI, emphasizing clean architecture, security, testability, and maintainability.

The user provides backend requirements: an API endpoint, a service, a data model, middleware, worker logic, or an entire system. They may include context about performance needs, scale, or integration points.

## Architecture Thinking

Before coding, understand the context and commit to a clear architectural direction:

- **Scope**: Is this a single endpoint, a service, or a full system? What integrations are needed (DB, cache, queues, external APIs)?
- **Scale & Performance**: Expected QPS? Latency requirements? Should this be sync or async? Is caching needed?
- **Data Model**: What entities exist? What are the relationships? Do you need a relational DB, document store, or cache layer?
- **Auth & Authorization**: Who calls this? Do you need API keys, JWT, OAuth? What roles/permissions exist?
- **Error Handling**: What can fail? How should failures be communicated (HTTP status, structured errors, logging)?
- **Testing Strategy**: Unit tests? Integration tests? Fixture strategy? Mocking approach?

**CRITICAL**: Choose a clear architectural direction and execute it with precision. Avoid over-engineering for hypothetical scale, but don't leave obvious gaps (missing error handling, no input validation, no tests).

Then implement working code (FastAPI routes, services, models) that is:

- Production-grade and fully functional
- Well-tested with appropriate coverage
- Secure by default (input validation, auth checks, SQL injection prevention)
- Observable (structured logging, error tracking, metrics)
- Maintainable with clear separation of concerns
- Properly documented (docstrings, OpenAPI schemas, README)

## FastAPI Project Structure

Follow this structure for clarity and scalability:

```
project/
├── main.py                 # Entry point, app setup
├── config.py               # Configuration, environment variables
├── requirements.txt        # Python dependencies
├── tests/
│   ├── conftest.py        # Pytest fixtures
│   ├── test_routes.py     # Route/endpoint tests
│   ├── test_services.py   # Business logic tests
│   └── test_models.py     # Model/schema tests
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py      # API endpoint handlers
│   │   └── deps.py        # Dependency injection (get_db, get_current_user)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── db.py          # SQLAlchemy ORM models
│   │   └── schema.py      # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   └── business.py    # Business logic, domain services
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── error_handler.py # Exception handlers, logging
│   └── database.py        # DB session, connection pooling
└── docs/
    └── API.md             # API documentation
```

## API Design Best Practices

### Routes & Handlers

- **Explicit routes**: Use clear HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`). Avoid RPC-style endpoints.
- **Idempotency**: `POST` for creation, `PUT` for full replacement, `PATCH` for partial updates. Always idempotent for `GET`, `PUT`, `DELETE`.
- **Status codes**: Return correct HTTP status (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Server Error`).
- **Consistent response format**: All responses (success and error) follow the same structure:
  ```python
  {
    "success": true|false,
    "data": {...} or null,
    "error": {"code": "...", "message": "...", "details": {...}} or null
  }
  ```
- **Pagination**: For list endpoints, always support `limit`, `offset` (or cursor). Default to reasonable limits (e.g., 20-100 items).
- **Filtering & Sorting**: Accept query params for filtering (`?status=active`) and sorting (`?sort=-created_at`). Document supported fields.
- **Async by default**: Use `async def` for route handlers and services to handle concurrent requests efficiently. Never block the event loop with sync I/O.

### Request/Response Schemas (Pydantic)

```python
from pydantic import BaseModel, Field, EmailStr, validator

class BusinessBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
    website: str | None = Field(None, max_length=2048)
    
    @validator('website')
    def validate_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Website must start with http:// or https://')
        return v

class BusinessCreate(BusinessBase):
    pass

class Business(BusinessBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # ORM mode for SQLAlchemy integration
```

- **Separate schemas**: Use `BaseModel`, `Create`, `Update`, and `Response` variants to enforce field requirements at each layer.
- **Validation**: Use Pydantic validators for business logic validation (email format, phone format, URL structure).
- **Documentation**: Add `Field(description="...")` for OpenAPI/Swagger docs.

## Database & ORM

### SQLAlchemy Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "postgresql://user:pass@localhost/dbname"
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Model Design

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False, unique=True)
    website = Column(String(2048), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Best Practices:**
- **Indexes**: Add `index=True` on columns you filter by (`name`, `phone`, `created_at`).
- **Timestamps**: Always include `created_at` and `updated_at` for audit trails.
- **Constraints**: Use `nullable=False` for required fields, `unique=True` for de-dupe keys.
- **Relationships**: Use SQLAlchemy `relationship()` for eager/lazy loading, document the loading strategy.
- **Soft deletes**: Add `deleted_at` if you need audit trails instead of hard deletes.

### Query Patterns

```python
async def get_businesses(db: Session, skip: int = 0, limit: int = 20) -> list[Business]:
    return db.query(Business).offset(skip).limit(limit).all()

async def get_business_by_id(db: Session, business_id: int) -> Business | None:
    return db.query(Business).filter(Business.id == business_id).first()

async def create_business(db: Session, business: BusinessCreate) -> Business:
    db_obj = Business(**business.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

async def update_business(db: Session, business_id: int, business: BusinessUpdate) -> Business | None:
    db_obj = db.query(Business).filter(Business.id == business_id).first()
    if not db_obj:
        return None
    for key, value in business.dict(exclude_unset=True).items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

async def delete_business(db: Session, business_id: int) -> bool:
    db_obj = db.query(Business).filter(Business.id == business_id).first()
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True
```

## Authentication & Authorization

### JWT Strategy

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(user_id: int, expires_delta: timedelta | None = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm="HS256")
```

**Best Practices:**
- **Secrets**: Store `SECRET_KEY`, database URLs, and API keys in environment variables, never in code.
- **Token expiry**: Use short-lived access tokens (1-24 hours) and refresh tokens for long-lived sessions.
- **Scope/Permissions**: Add a `scope` field to tokens and check permissions in handlers.
- **HTTPS only**: Require HTTPS in production; set `secure=True` on auth cookies.

## Error Handling & Validation

### Custom Exception Handlers

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

class BusinessNotFound(Exception):
    def __init__(self, business_id: int):
        self.business_id = business_id

@app.exception_handler(BusinessNotFound)
async def business_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "BUSINESS_NOT_FOUND",
                "message": f"Business {exc.business_id} not found",
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # Log the error, return a generic response in production
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            }
        }
    )
```

### Input Validation

```python
from pydantic import validator, ValidationError

class BusinessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v or len(v.replace('+', '').replace('-', '').replace(' ', '')) < 10:
            raise ValueError('Phone must be at least 10 digits')
        return v
```

**Best Practices:**
- **Validate early**: Use Pydantic to validate at the endpoint boundary.
- **Specific errors**: Return structured error responses with codes so clients can handle them programmatically.
- **Log failures**: Log validation/auth failures for security audits.

## Testing Strategy

### Unit Tests

```python
import pytest
from app.services.business import get_business_by_id
from app.models.schema import Business

@pytest.mark.asyncio
async def test_get_business_by_id(db_session):
    # Arrange
    business = Business(id=1, name="Test Spa", phone="512-555-0100")
    db_session.add(business)
    db_session.commit()
    
    # Act
    result = await get_business_by_id(db_session, business_id=1)
    
    # Assert
    assert result.id == 1
    assert result.name == "Test Spa"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_create_business_endpoint(client):
    # Arrange
    payload = {"name": "New Spa", "phone": "512-555-0100", "website": "newspa.com"}
    
    # Act
    response = client.post("/api/businesses", json=payload)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["data"]["id"] is not None
```

### Fixtures

```python
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

**Best Practices:**
- **Test behavior, not implementation**: Test what the API returns, not how it works internally.
- **Use fixtures**: Avoid duplication; create reusable test data with pytest fixtures.
- **Mock external calls**: Mock HTTP calls to external APIs and Yelp to avoid flakiness and cost.
- **Test edge cases**: Empty results, invalid input, auth failures, database errors.

## Performance & Optimization

### Async/Await

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/businesses")
async def list_businesses(db: Session = Depends(get_db)):
    # Async handlers allow FastAPI to handle many concurrent requests
    businesses = db.query(Business).limit(20).all()
    return businesses
```

**Never use synchronous I/O in async handlers.** Use `asyncio` libraries (aiohttp, asyncpg, motor).

### Caching

```python
from functools import lru_cache
from fastapi import BackgroundTasks

@app.get("/businesses/{business_id}")
async def get_business(business_id: int, db: Session = Depends(get_db)):
    # Check cache first
    cached = await cache.get(f"business:{business_id}")
    if cached:
        return cached
    
    # Fetch from DB
    business = db.query(Business).filter(Business.id == business_id).first()
    
    # Cache for 1 hour
    await cache.set(f"business:{business_id}", business, expire=3600)
    return business
```

### Query Optimization

```python
# Use eager loading to avoid N+1 queries
businesses = db.query(Business).options(
    joinedload(Business.reviews)
).all()

# Use `select()` for specific columns to reduce memory
results = db.query(Business.id, Business.name).all()

# Paginate large result sets
page = request.query_params.get("page", 1)
limit = request.query_params.get("limit", 20)
offset = (page - 1) * limit
```

## Logging & Observability

```python
import logging
from pythonjsonlogger import jsonlogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

@app.get("/businesses")
async def list_businesses(db: Session = Depends(get_db)):
    logger.info("Fetching businesses", extra={"limit": 20, "user_id": current_user_id})
    businesses = db.query(Business).limit(20).all()
    logger.info("Retrieved businesses", extra={"count": len(businesses)})
    return businesses
```

**Best Practices:**
- **Structured logging**: Use JSON logging for easy parsing and aggregation.
- **Log levels**: `INFO` for happy-path events, `WARNING` for retries, `ERROR` for failures.
- **Include context**: User ID, request ID, operation name, duration.

## Security Checklist

- ✅ **Input validation**: All user input validated with Pydantic.
- ✅ **SQL injection prevention**: Use parameterized queries (SQLAlchemy ORM handles this).
- ✅ **XSS prevention**: FastAPI returns JSON by default; only return HTML if explicitly needed (use `response_class=HTMLResponse`).
- ✅ **CORS**: Restrict to known origins in production.
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],
      allow_credentials=True,
      allow_methods=["GET", "POST"],
      allow_headers=["Authorization"],
  )
  ```
- ✅ **Rate limiting**: Use `slowapi` or `limits` to prevent brute force.
- ✅ **Secret management**: Never commit `.env` files; use environment variables.
- ✅ **HTTPS**: Enforce in production.
- ✅ **Dependency injection**: Use FastAPI's `Depends()` for auth and DB session injection.

## Documentation & API Schema

FastAPI auto-generates OpenAPI (Swagger) documentation:

```python
from fastapi import FastAPI

app = FastAPI(
    title="Lead Scraper API",
    description="REST API for Yelp lead scraping and management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.get("/businesses/{business_id}", response_model=Business)
async def get_business(
    business_id: int = Field(..., description="The unique business ID"),
    db: Session = Depends(get_db),
):
    """Retrieve a business by ID."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business
```

Visit `/docs` for interactive Swagger UI, `/redoc` for ReDoc documentation.

## Deployment Best Practices

```bash
# Use Gunicorn + Uvicorn for production
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use Docker
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "main:app", "--worker-class", "uvicorn.workers.UvicornWorker"]
```

**Best Practices:**
- **Environment config**: Use environment variables for database URLs, secrets, API keys.
- **Health checks**: Implement `/health` endpoint for load balancers.
- **Graceful shutdown**: Handle `SIGTERM` to finish in-flight requests before exiting.
- **Database migrations**: Use Alembic for schema versioning.
- **Monitoring**: Export Prometheus metrics, track error rates, latency, and throughput.

## Summary

Build with intention: validate input, handle errors explicitly, test thoroughly, log observably, secure by default. FastAPI's type hints and auto-documentation make correctness and clarity natural. Async/await and dependency injection keep the codebase lean and testable. Ship it.
