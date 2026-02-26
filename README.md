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


<img width="1025" height="234" alt="image" src="https://github.com/user-attachments/assets/0156a7ab-a327-4d0f-a38b-c89250a2b3b9" />


<img width="1030" height="280" alt="image" src="https://github.com/user-attachments/assets/1442f3ec-6a53-4c29-9fab-037717257072" />

</br>
This project also includes a Parking Traffic Simulator used for testing and demonstrating system behavior under dynamic load.

The simulator generates artificial parking activity and writes it directly to MongoDB, allowing the Telegram Bot and Next.js application to display realistic, real-time parking data.

What It Does:

Simulates random car arrivals using a Poisson distribution</br>

Simulates parking duration using a Normal distribution</br>

Randomly assigns cars to available parking slots</br>

Automatically handles parking and exit events</br>

Updates MongoDB in real time</br>

Displays live parking occupancy statistics</br>

Renders a real-time visualization graph using Matplotlib</br>


<img width="641" height="553" alt="image" src="https://github.com/user-attachments/assets/43385386-a443-4606-873b-067476e33ef1" />


<img width="769" height="289" alt="image" src="https://github.com/user-attachments/assets/c128d3cc-f1ad-4169-ad29-c0e5bffcb365" />


