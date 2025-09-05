#!/usr/bin/env python3
"""
Database migration script for the Silhouette Card Maker API.
Run this script to initialize or update the database schema.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User, TokenBlacklist, APILog


def init_database():
    """Initialize the database with tables and default data"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully")
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("Creating default admin user...")
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='admin123',  # Change this in production!
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Default admin user created: admin/admin123")
            print("⚠️  WARNING: Change the default admin password in production!")
        else:
            print("✓ Admin user already exists")
        
        # Create a test user if in development
        if app.config.get('FLASK_ENV') == 'development':
            test_user = User.query.filter_by(username='testuser').first()
            if not test_user:
                print("Creating test user...")
                test_user = User(
                    username='testuser',
                    email='test@example.com',
                    password='test123',
                    is_admin=False
                )
                db.session.add(test_user)
                db.session.commit()
                print("✓ Test user created: testuser/test123")
            else:
                print("✓ Test user already exists")
        
        print("\nDatabase initialization complete!")
        print(f"Database file: {app.config.get('SQLALCHEMY_DATABASE_URI')}")


def reset_database():
    """Reset the database (WARNING: This will delete all data!)"""
    app = create_app()
    
    with app.app_context():
        print("⚠️  WARNING: This will delete all data in the database!")
        confirm = input("Are you sure you want to continue? (yes/no): ")
        
        if confirm.lower() == 'yes':
            print("Dropping all tables...")
            db.drop_all()
            print("✓ All tables dropped")
            
            print("Recreating tables...")
            db.create_all()
            print("✓ Tables recreated")
            
            print("Creating default admin user...")
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password='admin123',
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Default admin user created: admin/admin123")
            
            print("\nDatabase reset complete!")
        else:
            print("Database reset cancelled.")


def show_users():
    """Show all users in the database"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"\nFound {len(users)} user(s):")
        print("-" * 80)
        print(f"{'ID':<5} {'Username':<15} {'Email':<25} {'Admin':<8} {'Active':<8} {'Created':<20}")
        print("-" * 80)
        
        for user in users:
            print(f"{user.id:<5} {user.username:<15} {user.email:<25} "
                  f"{'Yes' if user.is_admin else 'No':<8} "
                  f"{'Yes' if user.is_active else 'No':<8} "
                  f"{user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A':<20}")


def create_user():
    """Create a new user interactively"""
    app = create_app()
    
    with app.app_context():
        print("\nCreate a new user:")
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        is_admin = input("Is admin? (y/n): ").strip().lower() == 'y'
        
        if not username or not email or not password:
            print("Error: All fields are required.")
            return
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            print(f"Error: Username '{username}' already exists.")
            return
        
        if User.query.filter_by(email=email).first():
            print(f"Error: Email '{email}' already exists.")
            return
        
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                is_admin=is_admin
            )
            db.session.add(user)
            db.session.commit()
            print(f"✓ User '{username}' created successfully!")
        except Exception as e:
            print(f"Error creating user: {e}")
            db.session.rollback()


def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [init|reset|users|create-user]")
        print("\nCommands:")
        print("  init        - Initialize database with tables and default data")
        print("  reset       - Reset database (WARNING: deletes all data)")
        print("  users       - Show all users in the database")
        print("  create-user - Create a new user interactively")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'init':
        init_database()
    elif command == 'reset':
        reset_database()
    elif command == 'users':
        show_users()
    elif command == 'create-user':
        create_user()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: init, reset, users, create-user")


if __name__ == '__main__':
    main()
