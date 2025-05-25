from flask import Flask, render_template, request, redirect, url_for, Response
from playwright.async_api import async_playwright
import asyncio
import re
from datetime import datetime
import smtplib
import os
from dotenv import load_dotenv
from flask_apscheduler import APScheduler
import json 

app = Flask(__name__)

load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
BRAVE_PATH = os.getenv("BRAVE_PATH")

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def regex_search(value, pattern):
    match = re.search(pattern, value)
    return match.group(1) if match else None

# Register the filter in Jinja
app.jinja_env.filters['regex_search'] = regex_search

result_list = []


async def get_attendance(username, password, threshold=60):
    global result_list
    result_list = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=BRAVE_PATH, args=["--disable-extensions", "--disable-gpu"])
        context = await browser.new_context(
            permissions= []
        )
        page = await context.new_page()

        try:
            if username[:2] == "22":
                print("Got into the wrong site, displaying error")
                await browser.close() 
                return Response("<h1>This site does not work anymore</h1>", status=410, content_type='text/html')
                

            else:
                await page.goto("https://rcoem.in/login.htm;jsessionid=F09207583D26F128F9A1B05790CE0713")
                print("Got into site")

                await page.wait_for_selector('xpath=//*[@id="j_username"]')
                await page.fill('xpath=//*[@id="j_username"]', username)

                await page.wait_for_selector('xpath=//*[@id="password-1"]')
                await page.fill('xpath=//*[@id="password-1"]', password)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)

                print("logged in")

                if "Invalid username/password" in await page.content():
                    await browser.close()
                    return None

                await page.click('xpath=//*[@id="stud2"]/h2')
                await page.wait_for_timeout(2000)

                name = await page.text_content('xpath=//*[@id="header-name-role"]/p/a')
                overall = await page.text_content('xpath=//*[@id="attendanceDiv"]/table/tbody/tr[11]/th[3]')
                overall = float(overall)

                overall_fraction = await page.text_content('xpath=//*[@id="attendanceDiv"]/table/tbody/tr[11]/th[2]')
                attended_classes, total_classes = map(int, overall_fraction.split('/'))

                required_percentage = 75

                if overall < required_percentage:
                    classes = int(max(0, (attended_classes - 0.75 * total_classes) / -0.25))
                else:
                    classes = int((attended_classes - 0.75 * total_classes) / 0.75)

                subjects, attendance, attended = [], [], []
                subject_indices = [1, 2, 3, 4, 5, 9, 10]

                for idx in subject_indices:
                    try:
                        subject = await page.text_content(f'xpath=//*[@id="attendanceDiv"]/table/tbody/tr[{idx}]/td[2]')
                        percent = await page.text_content(f'xpath=//*[@id="attendanceDiv"]/table/tbody/tr[{idx}]/td[4]')
                        attend = await page.text_content(f'xpath=//*[@id="attendanceDiv"]/table/tbody/tr[{idx}]/td[3]/a')
                        subjects.append(subject)
                        attendance.append(percent)
                        attended.append(attend)
                    except:
                        continue

                await browser.close()

                # Attendance analysis
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
                            analysis.append(f"Attend at least {extra_classes} more classes to cross {threshold}%".split(":")[-1])
                        else:
                            bunkable = 0
                            temp_total = total
                            while (a / temp_total) * 100 >= threshold:
                                temp_total += 1
                                bunkable += 1
                            bunkable -= 1
                            analysis.append(f"You can bunk {bunkable} classes and still stay above {threshold}%".split(":")[-1])
                    except Exception as e:
                        print(f"Error while extracting data: {e}")
                        continue

                for i in range(len(subjects)):
                    result_list.append(f"{subjects[i]} : {attended[i]}")
                    result_list.append(analysis[i])
                    result_list.append("")

                result_list.append(f"Overall Attendance is: {overall}")
                return subjects, attendance, attended, analysis, overall, classes, name

        except Exception as e:
            print("Fatal error:", e)
            await browser.close()
            return None


@app.route('/', methods=['GET', 'POST'])  
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        data = asyncio.run(get_attendance(username, password))
        
        if isinstance(data, Response):  
            return data
        
        if data is None:  
            return "Invalid credentials or error", 401
    
        subjects, attendance, attended, analysis, overall, classes, name = data  
        
        return render_template('attendance.html', 
                               subjects=subjects, attendance=attendance, attended=attended, 
                               analysis=analysis, overall=overall, classes=classes, name=name)
    
    return render_template('login.html')



@app.route('/cgpa', methods=['GET', 'POST'])
def cgpa():
    grade_point_map = {
        "AA": 10,
        "AB": 9,
        "BB": 8,
        "BC": 7,
        "CC": 6,
        "CD": 5,
        "FF": 0
    }

    if request.method == 'POST':
        def get_grade_point(grade_str):
            return grade_point_map.get(grade_str.upper(), 0)

        subjects = ["DL", "DL_lab", "SE", "SE_lab", "CV", "CV_lab", "DAA", "PBL", "MOOC"]
        grades_and_credits = []

        for subject in subjects:
            grade_key = f"{subject}_grade"
            credit_key = f"{subject}_credit"

            grade = request.form.get(grade_key, "FF")
            credit = int(request.form.get(credit_key, 0))

            point = get_grade_point(grade)
            grades_and_credits.append((point, credit))

        total_weighted_score = sum(point * credit for point, credit in grades_and_credits)
        total_credits = sum(credit for _, credit in grades_and_credits)

        sgpa = total_weighted_score / total_credits if total_credits != 0 else 0
        sgpa = round(sgpa, 2)

        cgpa = float(request.form.get('cgpa', 0))
        final_cgpa = round((cgpa + sgpa) / 2, 2)

        return render_template('cgpa.html', sgpa=sgpa, final_cgpa=final_cgpa)
    
    return render_template('cgpa.html')

@scheduler.task('cron', id='weekly_mail', hour=9, minute=0)
def send_scheduled_mails():
    global result_list
    now = datetime.now()
    today = now.strftime("%A")
    print(f"Running mail scheduler on {today}")

    try:
        with open('subscriptions.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No subscriptions yet.")
        return

    for email, scheduled_day in data.items():
        if scheduled_day == today:
            try:
                # First try with TLS
                with smtplib.SMTP("smtp.gmail.com", 587) as con:
                    con.starttls()
                    con.login(EMAIL_USER, EMAIL_PASS)
                    con.sendmail(
                        from_addr=EMAIL_USER,
                        to_addrs=email,
                        msg=f"Subject: Attendance Report\n\nHere is your attendance summary:\n\n" + "\n".join(result_list)
                    )
                    print(f"Mail sent to {email} using TLS")
            except Exception as e:
                print(f"TLS failed for {email}: {e}")
                try:
                    # Fallback to SSL
                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as con:
                        con.login(EMAIL_USER, EMAIL_PASS)
                        con.sendmail(
                            from_addr=EMAIL_USER,
                            to_addrs=email,
                            msg=f"Subject: Attendance Report\n\nHere is your attendance summary:\n\n" + "\n".join(result_list)
                        )
                        print(f"Mail sent to {email} using SSL")
                except Exception as e:
                    print(f"SSL also failed for {email}: {e}")

@app.route('/mail', methods=['GET', 'POST'])
def mail():
    global result_list
    now = datetime.now()
    day = now.strftime("%A")
    print(day)
    
    if request.method == 'POST':
        user_email = request.form.get('email')  
        print(user_email)
        if not user_email or '@' not in user_email:
            return render_template('error.html', message="Invalid email entered.")

        # Save subscription
        try:
            with open('subscriptions.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}

        data[user_email] = day

        with open('subscriptions.json', 'w') as f:
            json.dump(data, f)

        # Send immediate mail
        try:
            # First try with TLS
            with smtplib.SMTP("smtp.gmail.com", 587) as con:
                con.starttls()
                con.login(EMAIL_USER, EMAIL_PASS)
                con.sendmail(
                    from_addr=EMAIL_USER,
                    to_addrs=user_email,
                    msg=f"Subject: Attendance Report\n\nHere is your attendance summary:\n\n" + "\n".join(result_list)
                )
                print(f"Immediate mail sent to {user_email} using TLS")
                return render_template('mail_sent.html')
        except Exception as e:
            print(f"TLS failed for immediate mail to {user_email}: {e}")
            try:
                # Fallback to SSL
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as con:
                    con.login(EMAIL_USER, EMAIL_PASS)
                    con.sendmail(
                        from_addr=EMAIL_USER,
                        to_addrs=user_email,
                        msg=f"Subject: Attendance Report\n\nHere is your attendance summary:\n\n" + "\n".join(result_list)
                    )
                    print(f"Immediate mail sent to {user_email} using SSL")
                    return render_template('mail_sent.html')
            except Exception as e:
                print(f"SSL also failed for immediate mail to {user_email}: {e}")
                return render_template('error.html', message="Failed to send email. Please try again later.")
        
    return render_template('mail.html')


@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(debug=True)  
