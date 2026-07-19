"""CafePress 登录 / 注册测试"""
import re

from playwright.sync_api import Page, expect

from pages.auth import (
    LoginPage,
    RegisterPage,
    TEST_PASSWORD,
    get_customer_id,
    make_test_email,
    expect_logged_in,
)


def test_login_page_loads(login):
    login.open()
    expect(login.page).to_have_title(re.compile("Sign In", re.I))
    expect(login.form).to_be_visible()
    expect(login.email_input).to_be_visible()
    expect(login.password_input).to_be_visible()
    expect(login.sign_in_button).to_have_value("SIGN IN")


def test_register_page_loads(register):
    register.open()
    expect(register.page).to_have_title(re.compile("Sign Up", re.I))
    expect(register.form).to_be_visible()
    expect(register.form.locator('input[name="txtFirstName"]')).to_be_visible()
    expect(register.form.locator('input[name="txtEmail"]')).to_be_visible()
    expect(register.create_account_button).to_have_value("CREATE ACCOUNT")


def test_register_new_account(register, page: Page, test_data):
    email = make_test_email()
    register.open()
    register.register(email=email)
    expect(expect_logged_in(page)).to_be_visible(timeout=30_000)

    test_data.record_auth(
        action="register",
        email=email,
        password=TEST_PASSWORD,
        customer_id=get_customer_id(page),
    )


def test_login_with_registered_account(register, login, page: Page, test_data):
    email = make_test_email()
    register.open()
    register.register(email=email)

    login.open()
    login.sign_in(email, TEST_PASSWORD)
    expect(expect_logged_in(page)).to_be_visible(timeout=30_000)

    test_data.record_auth(
        action="login",
        email=email,
        password=TEST_PASSWORD,
        customer_id=get_customer_id(page),
    )
