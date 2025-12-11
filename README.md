# FaceFindr - AI-Powered Image Search

FaceFindr is an advanced image search application that uses facial recognition technology to help users find and organize their photos.

## Getting Started

### Prerequisites
- Python 3.13+
- PostgreSQL database (or SQLite for development)
- uv package manager

### Installation
1. Clone the repository
2. Install dependencies:
   ```
   uv sync
   ```

### Database Setup
1. Make sure your database is running
2. Run migrations:
   ```
   alembic upgrade head
   ```

### Running the Application
```
uv run python main.py
```

## Password Migration

If you're upgrading from an older version, you may need to reset passwords due to bcrypt implementation changes:

1. List existing users:
   ```
   python reset_password.py list
   ```

2. Reset a user's password:
   ```
   python reset_password.py reset user@example.com newpassword
   ```

## Features
- Facial recognition powered by Facenet and PyTorch
- Admin dashboard for managing events and media
- Secure authentication with master token protection
- GPU-accelerated inference (CUDA support)
- MinIO integration for image storage

## Security
- Admin registration requires a master token
- Passwords are securely hashed using bcrypt
- JWT tokens for session management