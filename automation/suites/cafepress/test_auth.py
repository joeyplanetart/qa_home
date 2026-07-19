"""CafePress 登录 / 注册测试"""
import re

import pytest
from playwright.sync_api import Page, expect

from pages.auth import (
    CAFEPRESS_B2C_SITE_ID,
    LoginPage,
    RegisterPage,
    TEST_PASSWORD,
    get_customer_id,
    get_site_context,
    make_test_email,
    expect_logged_in,
)


def _record_auth_result(test_data, page: Page, *, action: str, email: str) -> None:
    site = get_site_context(page)
    test_data.record_auth(
        action=action,
        email=email,
        password=TEST_PASSWORD,
        customer_id=get_customer_id(page),
        site_id=site.get("site_id"),
        site_code=site.get("site_code"),
        page_url=site.get("url"),
        expected_site_id=CAFEPRESS_B2C_SITE_ID,
    )


def test_login_page_loads(login):
    login.open()
    site = get_site_context(login.page)
    expect(login.page).to_have_title(re.compile("Sign In", re.I))
    expect(login.form).to_be_visible()
    expect(login.email_input).to_be_visible()
    expect(login.password_input).to_be_visible()
    expect(login.sign_in_button).to_have_value("SIGN IN")
    assert site.get("site_id") == CAFEPRESS_B2C_SITE_ID
    assert site.get("site_code") == "CAFUS"


def test_register_page_loads(register):
    register.open()
    site = get_site_context(register.page)
    expect(register.page).to_have_title(re.compile("Sign Up", re.I))
    expect(register.form).to_be_visible()
    expect(register.form.locator('input[name="txtFirstName"]')).to_be_visible()
    expect(register.form.locator('input[name="txtEmail"]')).to_be_visible()
    expect(register.create_account_button).to_have_value("CREATE ACCOUNT")
    assert site.get("site_id") == CAFEPRESS_B2C_SITE_ID
    assert site.get("site_code") == "CAFUS"


@pytest.mark.selected
def test_register_new_account(register, page: Page, test_data):
    email = make_test_email()
    register.open()
    site = get_site_context(page)
    assert site.get("site_id") == CAFEPRESS_B2C_SITE_ID

    register.register(email=email)
    expect(expect_logged_in(page)).to_be_visible(timeout=30_000)
    _record_auth_result(test_data, page, action="register", email=email)


@pytest.mark.selected
def test_login_with_registered_account(register, login, page: Page, test_data):
    email = make_test_email()
    register.open()
    register.register(email=email)

    login.open()
    site = get_site_context(page)
    assert site.get("site_id") == CAFEPRESS_B2C_SITE_ID

    login.sign_in(email, TEST_PASSWORD)
    expect(expect_logged_in(page)).to_be_visible(timeout=30_000)
    _record_auth_result(test_data, page, action="login", email=email)
