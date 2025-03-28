6th Sem Project Based Learning - Attendance Analysis

A fully automated system that scrapes attendance data from the college website and provides insights on how many classes to attend or skip to maintain the required attendance percentage.

📌 Features

✅ Automated Attendance Scraping – Uses Selenium to log in and fetch attendance data.

✅ Class Recommendation – Calculates how many classes a student can skip or needs to attend.

✅ Web Extension & Website - Available as a fully functional website

✅ CGPA Predictor - Also includes an addtional CGPA predictor feature


🛠 Setup Instructions

1️⃣ Clone the Repository

git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git


2️⃣ Install Dependencies

Make sure you have Python installed (preferably 3.9+). Then install the required dependencies:

```powershell
pip install -r requirements.txt
```


3️⃣ Download and Set Up ChromeDriver

Download the Chromedriver folder in the repo. Make sure to enter the correct path in the python script.


4️⃣ Check the files

Make sure the files are in the following format:

```powershell

📂 Attendance-Analysis-PBL
│── 📂 templates/
          │── attendance.html
          │── error.html
          │── login.html
          │── cgpa.html
│── main.py                
│── requirements.txt        
│── README.md  
```

5️⃣ Run the Project 🚀

```powershell
python main.py
```

This will:

✔ Open the college website

✔ Log in using the provided credentials

✔ Scrape attendance details

✔ Provide class recommendations




