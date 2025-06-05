# Overview

For this project, I developed a command-line cloud-based to-do list manager. This tool enables users to log in with a secure password, manage personal tasks, and store everything remotely using Firestore—a NoSQL cloud database provided by Firebase.

The goal was to become more comfortable integrating Python applications with cloud services and learn how to handle basic user authentication, task CRUD operations, and persistent storage remotely. The program supports registration, login, and personalized task management (create, list, update, delete, and mark complete/incomplete).

To use the app:

- Run `main.py` from the terminal
- Register a new user or log in
- Manage your tasks through a simple menu-driven interface

[Software Demo Video](https://youtu.be/KmhanovMCGI)

# Cloud Database

I used Google Firebase’s Firestore as the cloud database for this project. Each user is stored as a document under a `users` collection. Each user document has a subcollection `tasks`, where each task is stored with fields such as title, description, timestamp, and completion status.

**Firestore Structure:**
users (collection)
(document)
password_hash:
tasks (subcollection)
(document)
title
description
completed
created_at

# Development Environment

- **Language:** Python 3.11
- **Libraries:** `firebase-admin`, `hashlib`, `datetime`, `os`, `sys`
- **Database:** Firebase Firestore

# Useful Websites

- [Firebase Python SDK Docs](https://firebase.google.com/docs/admin/setup)
- [Firestore Python Admin Guide](https://firebase.google.com/docs/firestore/quickstart)
- [Hashlib Documentation (Python)](https://docs.python.org/3/library/hashlib.html)

# Future Work

- Add real-time listeners to reflect task changes dynamically
- Encrypt passwords client-side for extra security before sending to Firebase
- Add a GUI version with Tkinter or PyQT for better UX
- Implement pagination or filtering for large task lists
