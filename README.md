TikRip: Django TikTok Downloader
TikRip is a simple web application built with Django that allows users to download TikTok videos. It features a full user authentication system where users can register, log in, and view a history of their past downloads in a personal cabinet.

🚀 Features
TikTok Video Downloader: Download videos by pasting the URL.

User Authentication: Full Register, Login, and Logout functionality.

Personal Cabinet: Logged-in users have a personal dashboard.

Download History: Automatically saves a history of all downloaded videos for registered users.

Clean Interface: A modern, clean UI built with HTML and custom CSS.

💻 Tech Stack
Backend: Python, Django

Frontend: HTML, CSS

Database: SQLite3 (default)

API: Uses an external RapidAPI for fetching video data.


⚙️ Getting Started: Installation
Follow these instructions to get a local copy up and running on your machine.

Prerequisites
Python 3.8+

Git

A RapidAPI account (or similar) to get a TikTok Downloader API Key.

Setup
Clone the repository:

Bash

git clone https://github.com/YOUR_USERNAME/TIKRIP.git
cd TIKRIP
Create and activate a virtual environment:

Bash

# Create the environment
python -m venv venv

# Activate it
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Install dependencies: (It's recommended to create a requirements.txt file first with pip freeze > requirements.txt. You will need at least django and requests).

Bash

pip install -r requirements.txt
Set up environment variables: This project requires an API key to function. It's bad practice to hardcode it in views.py.

Install python-dotenv: pip install python-dotenv

Create a .env file in the root TIKRIP directory (the same level as manage.py):


RAPIDAPI_KEY=your_actual_api_key_here
RAPIDAPI_HOST=tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com
In TIKRIP/settings.py, add at the top:

Python

import os
from dotenv import load_dotenv
load_dotenv()
In your downloader/views.py, you can now access these keys safely:

Python

import os
api_key = os.getenv("RAPIDAPI_KEY")
api_host = os.getenv("RAPIDAPI_HOST")
Run database migrations: This will create the db.sqlite3 file and set up the tables for users and your DownloadHistory.

Bash

python manage.py migrate
(Optional) Create a superuser: This allows you to access the Django admin panel (/admin).

Bash

python manage.py createsuperuser
Run the development server:

Bash

python manage.py runserver
Open the application: Navigate to http://127.0.0.1:8000/ in your web browser.

📖 Usage
Register: Create a new account using the "Register" link.

Login: Log in to your new account.

Download: Go to the home page, paste a valid TikTok URL into the field, and click "Download".

View History: Click on "Cabinet" to see a list of all the videos you have previously downloaded.

📄 License
This project is licensed under the MIT License.
