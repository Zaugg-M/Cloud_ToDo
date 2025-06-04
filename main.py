import os
import sys
import datetime
import hashlib
import firebase_admin
from firebase_admin import credentials, firestore


# CONFIGURATION / INITIALIZATION
# The service account JSON file downloaded from Firebase Console.
SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"

# Ensure the service account key file exists; otherwise exit with an error.
if not os.path.exists(SERVICE_ACCOUNT_PATH):
    print(f"ERROR: could not find {SERVICE_ACCOUNT_PATH}.")
    print("Make sure you downloaded your Firebase service account JSON and named it exactly:", SERVICE_ACCOUNT_PATH)
    sys.exit(1)

# Initialize the Firebase Admin SDK with the service account credentials.
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)

# Create a Firestore client for database interactions.
db = firestore.client()



# AUTHENTICATION HELPERS
def hash_password(password: str) -> str:
    """
    Return a hex-encoded SHA-256 hash of the given password.
    We store only the hash in Firestore, not the plaintext.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_user_document(username: str):
    """
    Return a DocumentReference for the Firestore document at users/<username>.
    This is where we store that user's hashed password and metadata.
    """
    return db.collection("users").document(username)


def user_exists(username: str) -> bool:
    """
    Check if a user document exists in Firestore (i.e., if the username is already taken).
    Returns True if the document exists, False otherwise.
    """
    return get_user_document(username).get().exists


def register_user(username: str):
    """
    Register a new user by prompting for a password twice, hashing it,
    and storing the hash along with a server timestamp under users/<username>.
    """
    doc_ref = get_user_document(username)
    print("=== Register New User ===")
    while True:
        # Prompt for password entry (visible as typed)
        pw1 = input("Enter a password: ").strip()
        pw2 = input("Confirm password: ").strip()

        if not pw1:
            print("Password cannot be empty.\n")
            continue
        if pw1 != pw2:
            print("Passwords do not match. Try again.\n")
            continue
        break

    # Hash the password and set the user document in Firestore
    pw_hash = hash_password(pw1)
    doc_ref.set({
        "password_hash": pw_hash,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    print("Registration successful.\n")


def login_user() -> str:
    """
    Prompt the user for a username and password (shown as typed).
    If credentials match the stored hash, return the username.
    Otherwise, print an error message and return None.
    """
    print("=== Login ===")

    # Ask for the username
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.\n")
        return None

    # Retrieve the Firestore document for that username
    doc_ref = get_user_document(username)
    doc = doc_ref.get()
    if not doc.exists:
        # No such user in the database
        print("Error: No such user.\n")
        return None

    # Extract the stored password hash
    stored_hash = doc.to_dict().get("password_hash", "")

    # Prompt for the password (visible as typed)
    pw = input("Password: ").strip()
    if hash_password(pw) != stored_hash:
        # Provided password does not match stored hash
        print("Error: Incorrect password.\n")
        return None

    # Successful login
    print(f"Login successful. Welcome, {username}!\n")
    return username



# TASK CRUD FUNCTIONS
def ensure_user_tasks_collection(username: str):
    """
    Ensures that the user document exists. 
    (In our flow, registration already created it, so no action is required here.)
    """
    pass  # Placeholder in case we want to enforce preconditions later


def create_task(username: str, title: str, description: str) -> str:
    """
    Create a new task document under users/<username>/tasks with an auto-generated ID.
    The task fields include title, description, created_at timestamp, and completed flag.
    Returns the Firestore document ID of the new task.
    """
    # Reference the tasks subcollection under the given user's document
    tasks_col = get_user_document(username).collection("tasks")
    # Obtain a new DocumentReference with a randomly generated ID
    doc_ref = tasks_col.document()
    new_task = {
        "title": title,
        "description": description,
        "created_at": firestore.SERVER_TIMESTAMP,
        "completed": False
    }
    # Write the task data to Firestore
    doc_ref.set(new_task)
    return doc_ref.id


def list_tasks(username: str):
    """
    Retrieve all tasks in users/<username>/tasks, ordered by creation timestamp.
    Returns a list of tuples: (task_document_id, task_data_dict).
    Each task_data_dict contains title, description, created_at_str, completed, etc.
    """
    tasks_col = get_user_document(username).collection("tasks")
    # Query tasks sorted by 'created_at'
    docs = tasks_col.order_by("created_at").stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        created = data.get("created_at")

        # Convert Firestore timestamp to a human-readable string if possible
        if isinstance(created, firestore.SERVER_TIMESTAMP.__class__):
            created_str = "<pending timestamp>"
        elif isinstance(created, datetime.datetime):
            created_str = created.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_str = "N/A"

        data["created_at_str"] = created_str
        result.append((doc.id, data))
    return result


def update_task(username: str, task_id: str, new_title: str = None, new_description: str = None,
                mark_complete: bool = None) -> bool:
    """
    Update the specified fields of a task document at users/<username>/tasks/<task_id>.
    - new_title: if provided, update the 'title' field
    - new_description: if provided, update the 'description' field
    - mark_complete: if provided (True/False), update the 'completed' field
    Returns True if any update was applied, False otherwise.
    """
    task_ref = get_user_document(username).collection("tasks").document(task_id)
    updates = {}
    if new_title is not None:
        updates["title"] = new_title
    if new_description is not None:
        updates["description"] = new_description
    if mark_complete is not None:
        updates["completed"] = mark_complete

    if not updates:
        # Nothing to update
        return False

    task_ref.update(updates)
    return True


def delete_task(username: str, task_id: str):
    """
    Delete the task document at users/<username>/tasks/<task_id>.
    """
    task_ref = get_user_document(username).collection("tasks").document(task_id)
    task_ref.delete()



# DISPLAY HELPERS
def print_task_indexed(index: int, title: str, data: dict):
    """
    Print a single task with:
    - index (1-based for user convenience)
    - title
    - status (Done/Not done)
    - description
    - human-readable created_at timestamp
    """
    status = "Done" if data.get("completed", False) else "Not done"
    print(f"{index + 1}) {title}  [{status}]")
    print(f"     Description: {data.get('description', '')}")
    print(f"     Created at: {data.get('created_at_str', '<unknown>')}")
    print("")



# MENU LOOPS
def task_menu(username: str):
    """
    After a successful login, present the user with the to-do menu until they log out.
    Offers options to list, add, update, delete, or toggle tasks for users/<username>.
    """
    ensure_user_tasks_collection(username)
    while True:
        # Fetch all tasks once per loop to display fresh data
        all_tasks = list_tasks(username)

        # Clear the console screen (Linux/macOS).
        # On Windows, replace "clear" with "cls" if desired.
        os.system("clear")
        print(f"=== {username}'s To-Do Menu ===")
        print("1) List tasks")
        print("2) Add a task")
        print("3) Update a task")
        print("4) Delete a task")
        print("5) Toggle task complete/incomplete")
        print("6) Logout")
        choice = input("Choose [1-6]: ").strip()

        if choice == "1":
            # LIST TASKS
            if not all_tasks:
                print("No tasks yet.")
            else:
                for idx, (_, data) in enumerate(all_tasks):
                    print_task_indexed(idx, data["title"], data)
            input("Press Enter to continue...")

        elif choice == "2":
            # ADD A TASK
            title = input("Title: ").strip()
            description = input("Description: ").strip()
            if not title:
                print("Title cannot be empty.")
            else:
                create_task(username, title, description)
                print("Task added.")
            input("Press Enter to continue...")

        elif choice == "3":
            # UPDATE A TASK
            if not all_tasks:
                print("No tasks to update.")
                input("Press Enter to continue...")
                continue

            # Display task titles with indices for selection
            print("Select task number to update:")
            for idx, (_, data) in enumerate(all_tasks):
                print(f"{idx + 1}) {data['title']}")

            idx_str = input("Task number: ").strip()
            if not idx_str.isdigit():
                print("Invalid input.")
                input("Press Enter to continue...")
                continue

            idx = int(idx_str) - 1
            if idx < 0 or idx >= len(all_tasks):
                print("Out of range.")
                input("Press Enter to continue...")
                continue

            # Retrieve the document ID and data for the selected task
            task_id, old_data = all_tasks[idx]
            print(f"Updating \"{old_data['title']}\"")
            new_title = input("New title (leave blank to keep current): ").strip()
            new_description = input("New description (leave blank to keep current): ").strip()
            updated = update_task(
                username,
                task_id,
                new_title if new_title else None,
                new_description if new_description else None,
                mark_complete=None
            )
            if updated:
                print("Task updated.")
            else:
                print("No changes made.")
            input("Press Enter to continue...")

        elif choice == "4":
            # DELETE A TASK
            if not all_tasks:
                print("No tasks to delete.")
                input("Press Enter to continue...")
                continue

            # Display task titles with indices
            print("Select task number to delete:")
            for idx, (_, data) in enumerate(all_tasks):
                print(f"{idx + 1}) {data['title']}")

            idx_str = input("Task number: ").strip()
            if not idx_str.isdigit():
                print("Invalid input.")
                input("Press Enter to continue...")
                continue

            idx = int(idx_str) - 1
            if idx < 0 or idx >= len(all_tasks):
                print("Out of range.")
                input("Press Enter to continue...")
                continue

            task_id, old_data = all_tasks[idx]
            confirm = input(f"Delete \"{old_data['title']}\"? (y/N): ").strip().lower()
            if confirm == "y":
                delete_task(username, task_id)
                print("Task deleted.")
            else:
                print("Deletion canceled.")
            input("Press Enter to continue...")

        elif choice == "5":
            # TOGGLE TASK COMPLETE/INCOMPLETE
            if not all_tasks:
                print("No tasks to toggle.")
                input("Press Enter to continue...")
                continue

            print("Select task number to toggle:")
            for idx, (_, data) in enumerate(all_tasks):
                status = "Done" if data.get("completed", False) else "Not done"
                print(f"{idx + 1}) {data['title']}  [{status}]")

            idx_str = input("Task number: ").strip()
            if not idx_str.isdigit():
                print("Invalid input.")
                input("Press Enter to continue...")
                continue

            idx = int(idx_str) - 1
            if idx < 0 or idx >= len(all_tasks):
                print("Out of range.")
                input("Press Enter to continue...")
                continue

            task_id, old_data = all_tasks[idx]
            new_status = not old_data.get("completed", False)
            update_task(username, task_id, mark_complete=new_status)
            state = "Done" if new_status else "Not done"
            print(f"Task \"{old_data['title']}\" marked {state}.")
            input("Press Enter to continue...")

        elif choice == "6":
            # LOGOUT
            print("Logging out...\n")
            break

        else:
            print("Invalid choice.")
            input("Press Enter to continue...")


def main_menu():
    """
    Display the initial menu for login, registration, or exit.
    Loops until a user successfully logs in and enters task_menu, or chooses to exit.
    """
    while True:
        # Clear the console before showing the main menu
        os.system("clear")
        print("=== Welcome to Cloud To-Do App ===")
        print("1) Login")
        print("2) Register")
        print("3) Exit")
        choice = input("Choose [1-3]: ").strip()

        if choice == "1":
            user = login_user()
            if user:
                # If login succeeds, enter the task management menu
                task_menu(user)
            else:
                # Show an error message, then return to main menu after Enter
                input("Press Enter to return to the main menu...")

        elif choice == "2":
            # REGISTER A NEW USER
            username = input("Choose a username: ").strip()
            if not username:
                print("Username cannot be empty.")
                input("Press Enter to continue...")
                continue
            if user_exists(username):
                print("Username already taken.")
                input("Press Enter to continue...")
            else:
                register_user(username)
                input("Press Enter to continue...")

        elif choice == "3":
            # EXIT THE APPLICATION
            print("Goodbye!")
            sys.exit(0)

        else:
            print("Invalid choice.")
            input("Press Enter to continue...")


if __name__ == "__main__":
    # Entry point: start at the main login/registration menu
    main_menu()
