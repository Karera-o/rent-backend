# House Rental Backend API

This is the backend API for the House Rental Management System, built with Django and Django Ninja.

## Features

- User Management with role-based access control (Admin, Agent, Tenant)
- Property Management system with approval workflow
- Booking System for reservations and stay management
- Payment Integration using Stripe
- Communication System for notifications and inquiries
- Image upload and management
- Caching for improved performance
- Rate limiting for API security
- Comprehensive logging
- Optimized database queries

## Technology Stack

- Django 5.0+ - Core framework
- Django Ninja-extra, django-ninja-jwt - API development
- PostgreSQL/SQLite - Database options
- Pytest - Testing framework
- JWT Authentication - Security
- Redis (optional) - Caching

## Architecture

The application follows a clean architecture pattern with separation of concerns:

- **Models**: Database layer (Django ORM)
- **Repositories**: Data access layer
- **Services**: Business logic layer
- **API Controllers**: Presentation layer
- **Schemas**: Data validation and transformation

## Setup and Installation

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)
- PostgreSQL (optional, SQLite is used by default)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create a `.env` file in the backend directory with the following variables:
   ```
   DJANGO_SECRET_KEY=your_secret_key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Uncomment for PostgreSQL
   # DB_ENGINE=django.db.backends.postgresql
   # DB_NAME=house_rental
   # DB_USER=postgres
   # DB_PASSWORD=postgres
   # DB_HOST=localhost
   # DB_PORT=5432
   
   # JWT settings
   JWT_ACCESS_TOKEN_LIFETIME_HOURS=1
   JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
   ```
6. Run migrations:
   ```bash
   python manage.py migrate
   ```
7. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
8. Run the development server:
   ```bash
   python manage.py runserver
   ```

## API Documentation

Once the server is running, you can access the API documentation at:
- http://localhost:8000/api/docs

## Testing

Run the tests with:
```bash
python manage.py test
```

## Security Features

- JWT authentication with secure cookie settings
- Password hashing
- Role-based access control
- Rate limiting for API protection
- CSRF protection
- Input validation with Pydantic schemas
- Environment variables for sensitive information

## Performance Optimizations

- Database query optimization with prefetch_related
- Caching for frequently accessed data
- Pagination for list endpoints
- Connection pooling for database connections
- Optimized image handling

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DJANGO_SECRET_KEY | Secret key for Django | None |
| DEBUG | Debug mode | True |
| ALLOWED_HOSTS | Comma-separated list of allowed hosts | localhost,127.0.0.1 |
| DB_ENGINE | Database engine | django.db.backends.sqlite3 |
| DB_NAME | Database name | db.sqlite3 |
| DB_USER | Database user | None |
| DB_PASSWORD | Database password | None |
| DB_HOST | Database host | None |
| DB_PORT | Database port | None |
| JWT_ACCESS_TOKEN_LIFETIME_HOURS | JWT access token lifetime in hours | 1 |
| JWT_REFRESH_TOKEN_LIFETIME_DAYS | JWT refresh token lifetime in days | 7 |
| REDIS_URL | Redis URL for caching | None |

## Authentication

The API uses JWT authentication. To authenticate:

1. Get a token by sending a POST request to `/api/token/` with your username and password
2. Include the token in the Authorization header of your requests: `Authorization: Bearer <token>`
3. Refresh tokens by sending a POST request to `/api/token/refresh/`

## API Endpoints

### Authentication Endpoints
- POST `/api/token/` - Get JWT tokens
- POST `/api/token/refresh/` - Refresh JWT token
- POST `/api/token/verify/` - Verify JWT token

### Users
- POST `/api/users/register` - Register a new user
- GET `/api/users/profile` - Get current user profile
- PUT `/api/users/profile` - Update current user profile
- POST `/api/users/change-password` - Change password
- GET `/api/users/agents` - Get all agents/landlords

### Properties
- GET `/api/properties/` - List properties with filters and pagination
- POST `/api/properties/` - Create a new property
- GET `/api/properties/{id}` - Get property details
- PUT `/api/properties/{id}` - Update a property
- DELETE `/api/properties/{id}` - Delete a property
- POST `/api/properties/{id}/images` - Add an image to a property
- GET `/api/properties/my-properties` - Get properties owned by the current user

## Recent Improvements

- Added environment variables for sensitive information
- Implemented caching for frequently accessed data
- Added rate limiting for API security
- Optimized database queries with prefetch_related
- Added pagination for list endpoints
- Implemented comprehensive logging
- Added proper exception handling
- Created test cases for API endpoints