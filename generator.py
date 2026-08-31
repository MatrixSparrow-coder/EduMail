"""
generator.py - Zero-input .edu email generator
100% anonymous - no user data used or stored
"""

import random
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from faker import Faker

class EduEmailGenerator:
    def __init__(self):
        self.faker = Faker()
        self.driver = None
        self.student_id = None
        self.edu_email = None
        self.password = None

    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver

    def _generate_temp_email(self):
        try:
            response = requests.get("https://api.temp-mail.org/request/domains/format/json", timeout=5)
            if response.status_code == 200:
                domains = response.json()
                domain = random.choice(domains) if domains else "temp-mail.org"
                prefix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
                return f"{prefix}@{domain}"
        except:
            pass
        return f"auto_{random.randint(100000, 999999)}@temp-mail.org"

    def _generate_temp_phone(self):
        area_codes = ['212', '310', '415', '718', '305', '202', '312', '404', '617', '214']
        return f"+1{random.choice(area_codes)}{random.randint(100, 999)}{random.randint(1000, 9999)}"

    def _generate_identity(self):
        return {
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "email": self._generate_temp_email(),
            "phone": self._generate_temp_phone(),
            "address": self.faker.street_address(),
            "city": self.faker.city(),
            "state": self.faker.state_abbr(),
            "zip": self.faker.zipcode(),
            "dob": self.faker.date_of_birth(minimum_age=18, maximum_age=30).strftime("%m/%d/%Y")
        }

    def generate(self):
        print("🚀 Starting automated .edu email generation...")
        print("🔒 No user data is used or stored - 100% anonymous")
        
        identity = self._generate_identity()
        print(f"📝 Auto-generated identity: {identity['first_name']} {identity['last_name']}")

        self._setup_driver()
        try:
            self.driver.get("https://apply.liberty.edu")
            time.sleep(3)
            wait = WebDriverWait(self.driver, 10)

            apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply')]")))
            apply_btn.click()
            time.sleep(2)

            online_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Online')]")))
            online_btn.click()
            time.sleep(1)

            # Fill form with fake data
            self.driver.find_element(By.ID, "firstName").send_keys(identity["first_name"])
            self.driver.find_element(By.ID, "lastName").send_keys(identity["last_name"])
            self.driver.find_element(By.ID, "email").send_keys(identity["email"])
            self.driver.find_element(By.ID, "phone").send_keys(identity["phone"])
            self.driver.find_element(By.ID, "dob").send_keys(identity["dob"])
            self.driver.find_element(By.ID, "addressLine1").send_keys(identity["address"])
            self.driver.find_element(By.ID, "city").send_keys(identity["city"])
            self.driver.find_element(By.ID, "state").send_keys(identity["state"])
            self.driver.find_element(By.ID, "zip").send_keys(identity["zip"])
            
            program_dropdown = wait.until(EC.element_to_be_clickable((By.ID, "program")))
            program_dropdown.click()
            time.sleep(0.5)
            program_option = self.driver.find_element(By.XPATH, "//option[contains(text(), 'Web Development')]")
            program_option.click()
            
            self.driver.find_element(By.ID, "highSchool").send_keys("Auto High School")
            self.driver.find_element(By.ID, "graduationYear").send_keys(str(random.randint(2020, 2026)))

            submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit')]")))
            submit_btn.click()
            time.sleep(5)

            page_source = self.driver.page_source
            student_id_match = re.search(r'L\d{6,8}', page_source)
            if student_id_match:
                self.student_id = student_id_match.group(0)
                print(f"✅ Student ID: {self.student_id}")
            else:
                time.sleep(10)
                self.driver.refresh()
                page_source = self.driver.page_source
                student_id_match = re.search(r'L\d{6,8}', page_source)
                if student_id_match:
                    self.student_id = student_id_match.group(0)
                    print(f"✅ Student ID: {self.student_id}")

            if not self.student_id:
                return {"status": "failed", "error": "Student ID not found"}

            time.sleep(30)
            self.driver.get("https://apply.liberty.edu/claim-account")
            time.sleep(3)

            self.driver.find_element(By.ID, "studentId").send_keys(self.student_id)
            self.driver.find_element(By.ID, "lastName").send_keys(identity["last_name"])
            claim_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Claim')]")))
            claim_btn.click()
            time.sleep(5)

            page_source = self.driver.page_source
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@liberty\.edu', page_source)
            if email_match:
                self.edu_email = email_match.group(0)
                print(f"✅ .edu Email: {self.edu_email}")

            if not self.edu_email:
                return {"status": "failed", "error": "Email not found"}

            self.password = f"Liberty{random.randint(1000, 9999)}!"
            self.driver.get("https://mylu.liberty.edu")
            time.sleep(3)
            self.driver.find_element(By.ID, "username").send_keys(self.edu_email)
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign In')]")))
            login_btn.click()
            time.sleep(5)

            return {
                "email": self.edu_email,
                "password": self.password,
                "student_id": self.student_id,
                "full_name": f"{identity['first_name']} {identity['last_name']}",
                "status": "success"
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}
        finally:
            self.driver.quit()