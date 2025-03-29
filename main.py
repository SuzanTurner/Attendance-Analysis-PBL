from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from email.message import EmailMessage
import time
import re
import smtplib
import os
from dotenv import load_dotenv

app = Flask(__name__)


# Custom Jinja Filter for Regex Search
def regex_search(value, pattern):
    match = re.search(pattern, value)
    return match.group(1) if match else None

# Register the filter in Jinja
app.jinja_env.filters['regex_search'] = regex_search

result_list = []

# Web Scraping Function
def get_attendance(username, password, threshold=60):
    global result_list
    chromedriver_path = r"C:/Users/hp/Downloads/chromedriver-win64/chromedriver.exe"
    brave_path = r"C:/Program Files/BraveSoftware/Brave-Browser/Application/Brave.exe"
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.binary_location = brave_path
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get("https://rbu.icloudems.com/corecampus/index.php")
    
    try:
        driver.find_element(By.XPATH, '//*[@id="useriid"]').send_keys(username, Keys.ENTER)
        driver.find_element(By.XPATH, '//*[@id="actlpass"]').send_keys(password, Keys.ENTER)
        time.sleep(2)  # Let the page load
    
        # Check if login failed
        if "Invalid username/password" in driver.page_source:
            driver.quit()
            return None  # Redirect to error page
        
        driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[5]/div/div/div[2]/a/img').click()
        time.sleep(2)  


        name = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[2]/div[1]/div[1]/div[1]/div[1]/h5').text

        overall = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[2]/div[2]/div[3]/div/div/table/tbody/tr[23]/td[3]').text
        overall = float(overall.replace('%', ''))

        overall_fraction = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div[3]/div[2]/div[2]/div[3]/div/div/table/tbody/tr[23]/td[2]').text

        attended_classes, total_classes = map(int, overall_fraction.split('/'))

        required_percentage = 75

        if overall < required_percentage:
            classes = int(max(0, (0.75 * total_classes - attended_classes) / 0.25) - attended_classes)
            #print(f"Attend at least {attended_classes - (int(classes) + 1)} more classes to reach 75%")
        else:
            classes = max(0, (attended_classes - 0.75 * total_classes) / 0.75)  
            #print(f"You can skip {int(classes)} classes and still be above 75%")

        subjects = []
        attendance = []
        attended = []
        
        subject_indices = [14, 15, 16, 17, 11, 12, 13]
        
        for idx in subject_indices:
            try:
                subject = driver.find_element(By.XPATH, f'/html/body/div[1]/div/div[1]/div[3]/div[2]/div[2]/div[3]/div/div/table/tbody/tr[{idx}]/td[2]').text
                percent = driver.find_element(By.XPATH, f'/html/body/div[1]/div/div[1]/div[3]/div[2]/div[2]/div[3]/div/div/table/tbody/tr[{idx}]/td[6]').text
                attend = driver.find_element(By.XPATH, f'/html/body/div[1]/div/div[1]/div[3]/div[2]/div[2]/div[3]/div/div/table/tbody/tr[{idx}]/td[5]/div').text
                subjects.append(subject)
                attendance.append(percent)
                attended.append(attend)
            except:
                continue
        
        driver.quit()
        
        # Attendance Analysis
        analysis = []
        for i in range(len(subjects)):
            try:
                a, total = map(int, attended[i].split('/'))
                
                if (a / total) * 100 < threshold:
                    extra_classes = 0
                    while (a / total) * 100 < threshold:
                        a += 1
                        total += 1
                        extra_classes += 1
                    analysis.append(f"{subjects[i]}: Attend at least {extra_classes} more classes to cross {threshold}%")
                else:
                    bunkable = 0
                    temp_a, temp_total = a, total
                    while ((temp_a / temp_total) * 100) >= threshold:
                        temp_a -= 1
                        temp_total -= 1
                        bunkable += 1
                    bunkable -= 1  # The last decrement takes it below threshold
                    analysis.append(f"{subjects[i]}: You can bunk {bunkable} classes and still stay above {threshold}%")
            except:
                continue

        for i in range(len(subjects)):
            result_list.append(f"{subjects[i]} : {attended[i]}")
            result_list.append(analysis[i])
            result_list.append("")

        result_list.append(f"Overall Attendance is: {overall}")
        

        return subjects, attendance, attended, analysis, overall, classes, name
    except Exception as e:
        driver.quit()
        return None


# Flask Routes
@app.route('/', methods=['GET', 'POST'])  
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        data = get_attendance(username, password)
        if data:
            subjects, attendance, attended, analysis, overall, classes, name = data  
            return render_template('attendance.html', subjects=subjects, attendance=attendance, attended=attended, analysis=analysis, overall = overall, classes = classes, name = name)
        else:
            return redirect(url_for('error'))
    return render_template('login.html')


@app.route('/cgpa', methods=['GET', 'POST'])
def cgpa():
    cgpa_value = None
    desired_cgpa = None
    required_sgpa = None

    if request.method == 'POST':
        cgpa_value = float(request.form['cgpa'])
        desired_cgpa = float(request.form['desired_cgpa'])

        # Required SGPA Calculation
        required_sgpa = 2 * desired_cgpa - cgpa_value  
        if required_sgpa > 10:
            required_sgpa = 10

    return render_template('cgpa.html', cgpa=cgpa_value, desired_cgpa=desired_cgpa, required_sgpa=required_sgpa)


load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


@app.route('/mail', methods=['GET', 'POST'])
def mail():
    global result_list
    if request.method == 'POST':
        user_email = request.form.get('email')  

        try: 
            with smtplib.SMTP("smtp.gmail.com", 587) as con:
                con.starttls()
                con.login(user = "silvervoid3.14@gmail.com", password = "volt mcsb tcqm jcan")
                con.sendmail(from_addr = "silvervoid3.14@gmail.com", 
                            to_addrs = user_email, 
                            msg = f"Subject: Attendance Report\n\nHere is your attendance summary:\n\n" + "\n".join(result_list))

                return "Mail Sent Successfully!"
            
        except Exception as e:
            print("Error:", e)
            return "Mail Sending Failed!"
        
    return render_template('mail.html')


@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(debug=False)  
