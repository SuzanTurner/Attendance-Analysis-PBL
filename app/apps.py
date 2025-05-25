
from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import json
import smtplib
from datetime import datetime
import dotenv
import os 

dotenv.load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

result_list = []

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

class MyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            send_scheduled_mails,
            trigger=CronTrigger(hour=9, minute=0),
            id='weekly_mail',
            replace_existing=True
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
