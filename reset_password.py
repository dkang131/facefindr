#!/usr/bin/env python3
"""
Utility script to reset passwords for existing users in the database.
This is needed when migrating from passlib to direct bcrypt implementation.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from models import Admin
from extensions import hash_password

def reset_user_password(email: str, new_password: str):
    """
    Reset the password for a specific user.
    """
    db_generator = get_db()
    db = next(db_generator)
    
    try:
        # Find the user
        user = db.query(Admin).filter(Admin.email == email).first()
        if not user:
            print(f"User with email {email} not found.")
            return False
        
        # Hash the new password
        hashed_password = hash_password(new_password)
        
        # Update the user's password
        user.password = hashed_password
        db.commit()
        
        print(f"Password successfully reset for user {email}")
        return True
    except Exception as e:
        print(f"Error resetting password for {email}: {e}")
        db.rollback()
        return False
    finally:
        # Close the database connection
        try:
            next(db_generator)
        except StopIteration:
            pass

def list_users():
    """
    List all users in the database.
    """
    db_generator = get_db()
    db = next(db_generator)
    
    try:
        users = db.query(Admin).all()
        if not users:
            print("No users found in the database.")
            return
        
        print("Users in the database:")
        for user in users:
            print(f"- {user.email} (ID: {user.id}, Role: {user.role})")
    except Exception as e:
        print(f"Error listing users: {e}")
    finally:
        # Close the database connection
        try:
            next(db_generator)
        except StopIteration:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python reset_password.py list                    - List all users")
        print("  python reset_password.py reset <email> <password> - Reset password for a user")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_users()
    elif command == "reset" and len(sys.argv) >= 4:
        email = sys.argv[2]
        password = sys.argv[3]
        reset_user_password(email, password)
    else:
        print("Invalid command or missing arguments.")
        print("Usage:")
        print("  python reset_password.py list                    - List all users")
        print("  python reset_password.py reset <email> <password> - Reset password for a user")
        sys.exit(1)