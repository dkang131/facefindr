# Secure Admin Registration

This document explains how to use the secure admin registration system.

## How It Works

The system has two registration endpoints:
1. Public registration endpoint (`/auth/register`) - for initial setup
2. Secure registration endpoint (`/auth/register-admin`) - protected with a master token

## Setup Instructions

1. First, set the master admin token as an environment variable:
   ```
   export MASTER_ADMIN_TOKEN="your-super-secret-master-token"
   ```

2. For development, you can also modify the default in `auth/app.py`:
   ```python
   MASTER_ADMIN_TOKEN = os.getenv("MASTER_ADMIN_TOKEN", "your-super-secret-master-token")
   ```

## Using the Secure Registration Page

1. Navigate to `/auth/register` in your browser
2. Enter your master token (set as described above)
3. Enter the new admin's email and password
4. Confirm the password
5. Click "Register Admin"

## API Usage

You can also use the secure registration endpoint directly:

```bash
curl -X POST "http://localhost:7219/auth/register-admin" \
  -H "Authorization: Bearer your-super-secret-master-token" \
  -H "Content-Type: application/json" \
  -d '{"email": "newadmin@example.com", "password": "securepassword"}'
```

## Security Notes

- Change the default master token in production
- Store the master token securely (environment variables, secret management system)
- The master token should be complex and unguessable
- Only share the master token with trusted administrators