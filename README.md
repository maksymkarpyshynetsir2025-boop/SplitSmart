# SplitSmart

**SplitSmart** is a web application designed to simplify the management and splitting of shared expenses between friends, roommates, families, and travel groups.

The application aims to help users track shared expenses, calculate individual balances, and determine who owes money to whom.

## Project Overview

The project is developed using a microservices-oriented architecture. The backend is built with Python and FastAPI, while the frontend is developed using React.

Currently, this repository includes the **Authentication Service (Auth Service)**, which handles user registration, login, and authentication.

## Technology Stack

### Backend
- Python 3.13
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- JWT Authentication
- uv


## Auth Service Documentation

For detailed information about the Authentication Service, including:

- Service architecture and responsibilities
- Registration and login request formats
- API endpoints and required input data
- Environment configuration
- Docker setup
- Local development setup

See the dedicated documentation:

**[Auth Service — README.md](backend/services/auth_service/README.md)**

## Development Workflow

1. Clone the repository.
2. Configure your local environment.
3. Start the required services using Docker Compose or run the application locally.
4. Implement and test your changes.
5. Commit and push your changes to the repository.

```bash
git add .
git commit -m "Describe your changes"
git push
```

---

**SplitSmart** — Making shared expenses easier to manage.


# SplitSmart

**SplitSmart** is a web application designed to simplify the management and splitting of shared expenses between friends, roommates, families, and travel groups.

The application aims to help users track shared expenses, calculate individual balances, and determine who owes money to whom.

## Project Overview

The project is developed using a microservices-oriented architecture. The backend is built with Python and FastAPI, while the frontend is developed using React.

Currently, this repository includes the **Authentication Service (Auth Service)**, which handles user registration, login, and authentication.

## Technology Stack

### Backend
- Python 3.13
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- JWT Authentication
- uv

### Frontend
- React
- Tailwind CSS
- Axios

### Infrastructure
- Docker
- Docker Compose
- RabbitMQ
- Kubernetes
- Helm
- Minikube

## Repository Structure

```text
SplitSmart/
│
├── backend/
│   ├── services/
│   │   └── auth_service/
│   │       ├── app/
│   │       ├── tests/
│   │       ├── alembic/
│   │       ├── Dockerfile
│   │       ├── pyproject.toml
│   │       ├── uv.lock
│   │       └── README.md
│   │
│   └── requirements.txt
│
├── frontend/
│
├── docker-compose.yaml
└── README.md
```

## Getting Started

### Prerequisites

Make sure you have the following tools installed:

- Git
- Python 3.13
- Docker Desktop
- Docker Compose
- uv (for local development)
- Node.js and npm (for frontend development)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd SplitSmart
```

### 2. Run with Docker

The recommended way to start the Auth Service is using Docker Compose.

From the project root directory, run:

```bash
docker compose up --build -d
```

This command builds the Auth Service image, starts the PostgreSQL database, applies database migrations, and starts the FastAPI application.

Check running containers:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f auth_service
```

Stop the containers:

```bash
docker compose down
```

### 3. Run Locally

For local development, navigate to the Auth Service directory:

```bash
cd backend/services/auth_service
```

Install dependencies:

```bash
uv sync --all-groups
```

Configure the environment variables in a `.env` file based on `.env.example`.

Make sure PostgreSQL is running and the database connection settings are configured correctly.

Run database migrations:

```bash
uv run alembic upgrade head
```

Start the development server:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Run the Frontend Locally

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend development URL depends on the configuration of the React project. Check the terminal output after starting the server.

## API Documentation

Once the Auth Service is running, its interactive API documentation is available at:

- **Swagger UI:** http://localhost:8001/docs (Docker)
- **Swagger UI:** http://localhost:8000/docs (Local)

Use Swagger UI to explore and test the registration and login endpoints.

## Auth Service Documentation

For detailed information about the Authentication Service, including:

- Service architecture and responsibilities
- Registration and login request formats
- API endpoints and required input data
- Environment configuration
- Docker setup
- Local development setup

See the dedicated documentation:

**[Auth Service — README.md](backend/services/auth_service/README.md)**

## Useful Links

### Backend
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Documentation](https://docs.python.org/3/)

### Frontend
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Axios Documentation](https://axios-http.com/docs/intro)

### DevOps and Infrastructure
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.

### Version Control
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Documentation](https://docs.github.com/)

## Contributing

Contributors should follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification when creating commit messages.

Examples:

```text
feat: add user registration
fix: resolve authentication error
docs: update README
refactor: improve authentication logic
test: add registration tests
```

Before submitting changes, make sure your code follows the project structure and existing coding conventions.

---
