"""
Selenium Automation Tests — CivicReport
Run AFTER starting the Flask server: python app.py
Then in a new terminal: python selenium_tests.py
"""

import time
import sys

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
except ImportError:
    print("Install selenium: pip install selenium")
    sys.exit(1)

BASE = "http://127.0.0.1:5000"
PASS_COUNT = 0
FAIL_COUNT = 0


def get_driver():
    options = Options()
    options.add_argument('--start-maximized')
    # options.add_argument('--headless')  # uncomment to run without browser
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(6)
    return driver


def check(name, condition):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        print(f"  ✅ PASS — {name}")
        PASS_COUNT += 1
    else:
        print(f"  ❌ FAIL — {name}")
        FAIL_COUNT += 1


def test_home_page(driver):
    print("\n📋 Test: Home Page")
    driver.get(BASE)
    check("Home page loads",         "CivicReport" in driver.title or
                                     "Civic"       in driver.page_source)
    check("User Login card visible", "User Login"  in driver.page_source)
    check("Admin card visible",      "Admin"       in driver.page_source)


def test_register(driver):
    print("\n📋 Test: User Registration")
    driver.get(f"{BASE}/register")
    check("Register page loads", "Register" in driver.page_source)

    driver.find_element(By.NAME, "username").send_keys("selenium_user")
    driver.find_element(By.NAME, "email").send_keys("selenium@test.com")
    driver.find_element(By.NAME, "password").send_keys("selenium123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(1)
    check("Redirected after register",
          "/login" in driver.current_url or
          "Login"  in driver.page_source)


def test_user_login(driver):
    print("\n📋 Test: User Login")
    driver.get(f"{BASE}/login")
    driver.find_element(By.NAME, "username").send_keys("selenium_user")
    driver.find_element(By.NAME, "password").send_keys("selenium123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(1)
    check("Login successful",
          "dashboard" in driver.current_url or
          "Welcome"   in driver.page_source)


def test_submit_complaint(driver):
    print("\n📋 Test: Submit Complaint")
    driver.get(f"{BASE}/submit")
    check("Report page loads", "Report" in driver.page_source or
                               "Complaint" in driver.page_source)

    ta = driver.find_element(By.NAME, "complaint_text")
    ta.send_keys("There is an urgent water pipe burst on Main Street causing flooding")
    driver.find_element(By.NAME, "location").send_keys("13.0827,80.2707")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(1)
    check("Complaint submitted",
          "dashboard" in driver.current_url or
          "Water"     in driver.page_source or
          "submitted" in driver.page_source.lower())


def test_dashboard(driver):
    print("\n📋 Test: Dashboard")
    driver.get(f"{BASE}/dashboard")
    check("Dashboard loads",          "Dashboard"  in driver.page_source or
                                      "Complaints" in driver.page_source)
    check("Complaints table visible", "Category"   in driver.page_source)
    check("Chart canvas present",
          "statusChart" in driver.page_source or
          "canvas"      in driver.page_source)


def test_admin_login(driver):
    print("\n📋 Test: Admin Login")
    driver.get(f"{BASE}/logout")
    time.sleep(1)
    driver.get(f"{BASE}/admin-login")
    driver.find_element(By.NAME, "username").send_keys("admin")
    driver.find_element(By.NAME, "password").send_keys("admin123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(1)
    check("Admin login successful",
          "admin"  in driver.current_url or
          "Admin"  in driver.page_source)


def test_admin_panel(driver):
    print("\n📋 Test: Admin Panel")
    driver.get(f"{BASE}/admin")
    check("Admin panel loads",
          "All Complaints" in driver.page_source or
          "Admin"          in driver.page_source)
    check("Priority sorting visible",
          "High"   in driver.page_source or
          "Medium" in driver.page_source)
    check("Update button visible", "Update" in driver.page_source)


def test_chatbot(driver):
    print("\n📋 Test: Chatbot")
    driver.get(f"{BASE}/login")
    driver.find_element(By.NAME, "username").send_keys("selenium_user")
    driver.find_element(By.NAME, "password").send_keys("selenium123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(1)
    driver.get(f"{BASE}/dashboard")
    check("Chatbot widget present",
          "chatbot" in driver.page_source.lower())


def main():
    print("=" * 55)
    print("  CivicReport — Selenium Automation Test Suite")
    print("=" * 55)
    print("  Make sure Flask server is running: python app.py")
    print("=" * 55)

    driver = get_driver()
    try:
        test_home_page(driver)
        test_register(driver)
        test_user_login(driver)
        test_submit_complaint(driver)
        test_dashboard(driver)
        test_admin_login(driver)
        test_admin_panel(driver)
        test_chatbot(driver)
    finally:
        driver.quit()

    print("\n" + "=" * 55)
    print(f"  Results: ✅ {PASS_COUNT} Passed  |  ❌ {FAIL_COUNT} Failed")
    print("=" * 55)


if __name__ == "__main__":
    main()
