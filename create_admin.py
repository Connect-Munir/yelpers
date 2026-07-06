"""
Create a new admin, or promote an existing user to admin.

Admins are never created through the public signup form — you make them here.
Run from the project root (same folder as scraper.py):

    # Promote an existing account to admin:
    python create_admin.py --email you@example.com --promote

    # Create a brand-new admin account:
    python create_admin.py --email boss@example.com --name "Boss" --password "StrongPass123"

    # List current admins:
    python create_admin.py --list
"""
import argparse
import getpass
import sys

from backend.database import SessionLocal, init_db
from backend.models import ROLE_ADMIN, User
from backend.auth import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument("--email", help="Email of the admin account")
    parser.add_argument("--name", help="Name (only when creating a new account)")
    parser.add_argument("--password", help="Password (only when creating; omit to be prompted)")
    parser.add_argument("--promote", action="store_true",
                        help="Promote an existing user with this email to admin")
    parser.add_argument("--list", action="store_true", help="List all current admins")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.list:
            admins = db.query(User).filter(User.role == ROLE_ADMIN).all()
            if not admins:
                print("No admins yet.")
            for a in admins:
                state = "active" if a.is_active else "inactive"
                print(f"  #{a.id}  {a.email}  ({a.name}) - {state}")
            return

        if not args.email:
            parser.error("--email is required (unless using --list)")

        existing = db.query(User).filter(User.email == args.email).first()

        if args.promote or existing:
            if not existing:
                print(f"No user found with email {args.email}. "
                      f"Drop --promote to create a new admin instead.")
                sys.exit(1)
            existing.role = ROLE_ADMIN
            db.commit()
            print(f"[OK] {existing.email} is now an admin.")
            return

        # Create a new admin account
        name = args.name or input("Name: ").strip()
        password = args.password or getpass.getpass("Password: ")
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            sys.exit(1)

        admin = User(
            name=name,
            email=args.email,
            hashed_password=hash_password(password),
            role=ROLE_ADMIN,
        )
        db.add(admin)
        db.commit()
        print(f"[OK] Admin created: {admin.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
