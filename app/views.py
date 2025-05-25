from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin
from playwright.async_api import async_playwright
import asyncio
import re
from datetime import datetime
import smtplib
import os
import json 
import dotenv

dotenv.load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")
BRAVE_PATH = os.getenv("BRAVE_PATH")

result_list = []

async def get_attendance(username, password, threshold=60):
    global result_list
    result_list = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=BRAVE_PATH)
        context = await browser.new_context(
            permissions= []
        )
        page = await context.new_page()

        try:
            if username[:2] == "22":
                print("Got into the wrong site, displaying error")
                await browser.close() 
                return render("<h1>This site does not work anymore</h1>", status=410, content_type='text/html')
                

            else:
                await page.goto("https://rcoem.in/login.htm")
                print("Got into site")

                #await page.wait_for_load_state('networkidle')

                await page.wait_for_selector('xpath=//*[@id="j_username"]')
                await page.fill('xpath=//*[@id="j_username"]', username)

                await page.wait_for_selector('xpath=//*[@id="password-1"]')
                await page.fill('xpath=//*[@id="password-1"]', password)

                # Wait for login to finish (replace wait_for_navigation if it doesn't work)
                await page.keyboard.press('Enter')
                #await page.wait_for_timeout(4000)

                # Now check for login failure
                try:
                    error_element = await page.query_selector('xpath=//*[@id="loginPageDiv"]/div/div/div/div/div[2]/div/div[2]/div[1]')
                    if error_element:
                        error_text = await error_element.inner_text()
                        if "Invalid" in error_text:
                            print("Login failed")
                            await browser.close()
                            return None
                except:
                    pass

                # Continue after successful login
                #await page.wait_for_load_state('networkidle')
                print("Logged in")

                print(" Gonna click attendance")
                await page.wait_for_selector('xpath=//*[@id="stud2"]/h2')
                await page.click('xpath=//*[@id="stud2"]/h2')
                # await page.wait_for_timeout(2000)

                #await page.wait_for_load_state('load')

                await page.wait_for_load_state('networkidle')

                await page.wait_for_selector('xpath=//*[@id="header-name-role"]/p/a')
                name = await page.text_content('xpath=//*[@id="header-name-role"]/p/a')

                await page.wait_for_selector('xpath=//*[@id="attendanceDiv"]/table/tbody/tr[11]/th[3]')
                overall = await page.text_content('xpath=//*[@id="attendanceDiv"]/table/tbody/tr[11]/th[3]')
                overall = float(overall)

                await page.wait_for_selector('xpath=//*[@id="attendanceDiv"]/table/tbody/tr[11]/th[2]')

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


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        data = asyncio.run(get_attendance(username, password))
        
        if isinstance(data, HttpResponse):  
            return data
        
        if data is None:  
            return HttpResponse("Invalid credentials or error", status=401)
    
        subjects, attendance, attended, analysis, overall, classes, name = data 

        combined_data = []
        for i in range(len(subjects)):
            analysis_text = analysis[i]
            bunk = re.search(r'bunk (\d+)', analysis_text)
            attend = re.search(r'Attend at least (\d+)', analysis_text)
            
            combined_data.append({
                'subject': subjects[i],
                'attendance': attendance[i],
                'attended': attended[i],
                'analysis': analysis_text,
                'bunk': bunk.group(1) if bunk else '',
                'attend': attend.group(1) if attend else ''
            })

        context = {
            'combined_data': combined_data,
            'overall': overall,
            'classes': classes,
            'name': name
        }
        return render(request, 'attendance.html', context)
            
    return render(request, 'login.html')


@csrf_exempt
def cgpa(request):
    grade_point_map = {
        "AA": 10,
        "AB": 9,
        "BB": 8,
        "BC": 7,
        "CC": 6,
        "CD": 5,
        "FF": 0
    }

    subjects = ["DL", "DL_lab", "SE", "SE_lab", "CV", "CV_lab", "DAA", "PBL", "MOOC"]

    if request.method == 'POST':
        def get_grade_point(grade_str):
            return grade_point_map.get(grade_str.upper(), 0)
        
        grades_and_credits = []

        for subject in subjects:
            grade_key = f"{subject}_grade"
            credit_key = f"{subject}_credit"

            grade = request.POST.get(grade_key, "FF")
            credit = int(request.POST.get(credit_key, 0))

            point = get_grade_point(grade)
            grades_and_credits.append((point, credit))

        total_weighted_score = sum(point * credit for point, credit in grades_and_credits)
        total_credits = sum(credit for _, credit in grades_and_credits)

        sgpa = total_weighted_score / total_credits if total_credits != 0 else 0
        sgpa = round(sgpa, 2)

        cgpa = float(request.POST.get('cgpa', 0))
        final_cgpa = round((cgpa + sgpa) / 2, 2)

        context = {
            'sgpa' : sgpa, 
            'final_cgpa' : final_cgpa
        }

        return render(request, 'cgpa.html', context)
    
    return render(request, 'cgpa.html',  {'subjects': subjects})

@csrf_exempt
def mail(request):
    global result_list
    now = datetime.now()
    day = now.strftime("%A")
    print(day)
    
    if request.method == 'POST':
        user_email = request.POST.get('email')  
        print(user_email)
        if not user_email or '@' not in user_email:
            return render(request, 'error.html', message="Invalid email entered.")

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
                return render(request, 'mail_sent.html')
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
                    return render(request, 'mail_sent.html')
            except Exception as e:
                print(f"SSL also failed for immediate mail to {user_email}: {e}")
                return render(request, 'error.html', message="Failed to send email. Please try again later.")
        
    return render(request, 'mail.html')

def error(request):
    return render(request, 'error.html')