
from getpass import getpass

from sqlmodel import Session, select

from app.database import engine
from app.models import User
from app.security import hash_password

username = "management@college.edu"

new_password = getpass("Enter new Management password: ")
confirm_password = getpass("Confirm new password: ")

if len(new_password) < 8:
    print("Password must contain at least 8 characters.")

elif new_password != confirm_password:
    print("Passwords do not match.")

else:
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()

        if not user:
            print("Management account not found.")

        elif user.role.value != "management":
            print("This account is not a Management account.")

        else:
            user.password_hash = hash_password(new_password)
            user.must_change_password = False

            session.add(user)
            session.commit()

            print("Management password updated successfully!")
