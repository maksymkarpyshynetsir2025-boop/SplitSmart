# SplitSmart - Authentication service

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.13 | Programming language |
| FastAPI | Backend web framework |
| SQLAlchemy 2.0 | ORM and database operations |
| PostgreSQL 16 | Relational database |
| AsyncPG | Asynchronous PostgreSQL driver |
| Alembic | Database migrations |
| Pydantic | Data validation and settings |
| JWT (PyJWT) | Token-based authentication |
| Passlib / Argon2 / Bcrypt | Password hashing |
| Docker | Application containerization |
| Docker Compose | Running application and database containers |
| uv | Python dependency management |
| Uvicorn | ASGI server |

## Authentication Features

The Auth Service provides the following functionality:

- User registration.
- User login.
- Password hashing.
- JWT token generation.
- Separate `access` and `refresh` token type claims.
- User authentication.
- User account management.
- API-key-protected internal user lookup for trusted services.

## API Endpoints

The API is available under the following base URL:

`http://localhost:8001`

### 1. User Registration

**Endpoint:**

`POST /auth/api/v1/auth/register`

Registers a new user.

**Request Body:**

```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string"
}
```


Example:

```json
{
  "username": "natalie",
  "email": "natalie@example.com",
  "password": "MyPassword123!"
}
```

### 2. User Login

**Endpoint:**

`POST /auth/api/v1/auth/login`

Authenticates an existing user.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

Example:

```json
{
  "email": "natalie@example.com",
  "password": "MyPassword123!"
}
```

**Note:** Use the same email and password that were provided during registration.

Access tokens contain `type: "access"` and refresh tokens contain
`type: "refresh"`; both retain the integer user ID in `sub`.

### Internal user lookup

`GET /api/v1/internal/users/{user_id}` returns the user's ID and email for
trusted backend services. It requires the `X-Internal-Api-Key` header and is
disabled until `INTERNAL_API_KEY` is configured. Keep this key private and
share it only with trusted services such as Group Management. The same
protection applies to `GET /api/v1/internal/users/by-email/{email}`.

## Running the Project with Docker

Docker Compose allows you to start the Auth Service and PostgreSQL database without installing Python dependencies locally.

### Prerequisites

- Docker Desktop
- Docker Compose

### Step 1. Clone the repository

```bash
git clone <repository-url>
cd SplitSmart
```

### Step 2. Configure environment variables

Create a `.env` file in:

`backend/services/auth_service/`

Configure the database connection string:

```env
DATABASE_URL=postgresql+asyncpg://authuser:authpass@auth_db:5432/authdb
```

Make sure the variable names match the application configuration in `app/core/config.py` (or the corresponding settings module).

### Step 3. Build and start containers

From the project root directory, run:

```bash
docker compose up --build -d
```

This command:
- Builds the Auth Service Docker image.
- Starts the PostgreSQL container.
- Waits for the database health check.
- Runs Alembic migrations.
- Starts the FastAPI application.

### Step 4. Check running containers

```bash
docker compose ps
```

### Step 5. View application logs

```bash
docker compose logs -f auth_service
```

To view database logs:

```bash
docker compose logs -f auth_db
```

### Step 6. Access the API

Once the service is running, open:

**Swagger UI:**

http://localhost:8001/docs

**ReDoc:**

http://localhost:8001/redoc

You can use Swagger UI to test registration and login endpoints.

### Useful Docker Commands

| Command | Description |
|---|---|
| `docker compose up -d` | Start containers |
| `docker compose up --build -d` | Build and start containers |
| `docker compose down` | Stop and remove containers |
| `docker compose restart auth_service` | Restart Auth Service |
| `docker compose logs -f auth_service` | View service logs |
| `docker compose ps` | Check container status |
| `docker compose down -v` | Remove containers and database volumes |

**Warning:** `docker compose down -v` deletes the PostgreSQL volume and all database data stored in it.

## Running the Project Locally

You can also run the Auth Service directly on your machine without building its application container. PostgreSQL is still required.

### Prerequisites

- Python 3.13
- uv
- PostgreSQL 16
- Git

### Step 1. Clone the repository

```bash
git clone <repository-url>
cd SplitSmart/backend/services/auth_service
```

### Step 2. Install dependencies

Install uv if it is not already installed:

```bash
pip install uv
```

Install project dependencies:

```bash
uv sync --all-groups
```

### Step 3. Configure environment variables

Create a `.env` file in the Auth Service directory.

For a locally running PostgreSQL instance, configure:

```env
DATABASE_URL=postgresql+asyncpg://authuser:authpass@localhost:5432/authdb
```

Ensure that PostgreSQL is running, and that the database, username, and password exist and match your configuration.

### Step 4. Run database migrations

```bash
uv run alembic upgrade head
```

This creates or updates the database schema.

### Step 5. Start the application

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:

http://localhost:8000

**Swagger UI:**

http://localhost:8000/docs

**ReDoc:**

http://localhost:8000/redoc

### Alternative: Run PostgreSQL with Docker and the application locally

If you do not have PostgreSQL installed, you can start only the database using Docker Compose:

```bash
docker compose up -d auth_db
```

Then configure your local `.env`:

```env
DATABASE_URL=postgresql+asyncpg://authuser:authpass@localhost:5432/authdb
```

Run migrations and start FastAPI locally:

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Project Structure

```text
auth_service/
│
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       └── router.py
│   │
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── db/
│   │
│   └── main.py
│
├── alembic/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── .env.example
```

## API Documentation

The API documentation is automatically generated by FastAPI.

After starting the application, you can explore and test the available endpoints using:

- Swagger UI: `/docs`
- ReDoc: `/redoc`

These interfaces provide information about request parameters, request bodies, response schemas, and available API operations.

## Notes

- Never commit `.env` files containing real credentials to Git.
- Use `.env.example` to document the required environment variables.
- Passwords should never be stored as plain text.
- Database migrations are managed using Alembic.
- Each microservice should own and manage its own database.
- Services communicate through APIs rather than accessing each other's databases directly.