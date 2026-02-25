# Telegram Parking-Bot

Telegram Bot:</br>
Python + aiogram, the bot acts as a backend service that:
Handles user interactions inside Telegram</br>
Registers users</br>
Manages parking logic (park / exit)</br>
Updates user balance</br>
Writes parking data to MongoDB</br>


Shared Database Pattern:</br>

Telegram Bot  ─┐</br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── MongoDB</br>
Next.js App  ──┘</br>


Next.js Web Application:

Reads parking data from MongoDB</br>
Displays real-time parking status in the browser</br>
Provides a visual interface for monitoring parking availability</br>

The web app is responsible for data presentation (UI layer).

Next.js App source:
https://github.com/Yaroslav-Repos/parking-status
