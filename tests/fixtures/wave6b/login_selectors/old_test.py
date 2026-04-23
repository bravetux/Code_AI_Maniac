from selenium import webdriver
from selenium.webdriver.common.by import By


def test_login_flow():
    driver = webdriver.Chrome()
    driver.get("https://example.test/login")
    driver.find_element(By.ID, "login-btn").click()
    email = driver.find_element(By.XPATH, "//input[@name='email']")
    email.send_keys("user@example.test")
    driver.find_element(By.CSS_SELECTOR, "#password-field").send_keys("secret")
    driver.find_element(By.ID, "submit-btn").click()
    driver.quit()
