# pylint: disable=unused-import
import csv
import random
import re
import string
import sys
import time
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Dict, List

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ....models.attachement import Attachement
from ....models.order import Order
from ....models.orderitem import OrderItem
from ....models.shop import Shop
from .base import BaseScraper, PagePart


class EbayScraper(BaseScraper):
    # Scrape comand and __init__

    def command_scrape(self):
        browser_kwargs = {
            "change_ua": (
                "Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U)"
                " AppleWebKit/537.36 (KHTML, like Gecko)"
                " SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile"
                " Safari/537.36"
            )
        }
        if settings.SCRAPER_EBY_MANUAL_LOGIN:
            self.log.debug(
                self.command.style.ERROR(
                    "Please log in to eBay and press enter when ready."
                )
            )
            input()
            brws = self.browser_get_instance(**browser_kwargs)
        else:
            brws = self.browser_get_instance(**browser_kwargs)

            self.log.debug("Visiting homepage %s", self.HOMEPAGE)
            self.browser_visit_page_v2(self.HOMEPAGE)

            self.log.debug(
                "Switching to mobile: %s",
                self.browser_website_switch_mode("mobile"),
            )
            brws.execute_script("window.scrollTo(0,document.body.scrollHeight)")

            self.log.debug("Visiting homepage %s", self.ORDER_LIST_URL)
            self.browser_visit_page_v2(self.ORDER_LIST_URL)

            time.sleep(3)
            while True:
                self.browser_scrape_individual_order_list()
                next_link = self.find_element(
                    By.CSS_SELECTOR, "a.m-pagination-simple-next"
                )
                if next_link.get_attribute("aria-disabled") == "true":
                    self.log.debug("No more orders")
                    break
                next_link.click()
                self.rand_sleep(2, 4)

        assert brws

    def browser_scrape_individual_order_list(self):
        for item_container in self.find_elements(
            By.CSS_SELECTOR, "div.m-mweb-item-container"
        ):
            order_href = self.find_element(
                By.CSS_SELECTOR, "a.m-mweb-item-link", item_container
            ).get_attribute("href")
            re_matches = re.match(
                r".*\?orderId=(?P<order_id>[0-9-]*).*", order_href
            )
            order_id = re_matches.group("order_id")
            print("Order ID", order_id)
            # thumb_img = self.find_element(
            #     By.CSS_SELECTOR, "div.m-image img", item_container
            # )
            # print("Item thumb", thumb_img.get_attribute("src"))
            # item_details = self.find_element(
            #     By.CSS_SELECTOR, "div.item-details", item_container
            # )
            # status = self.find_element(
            #     By.CSS_SELECTOR, "div.item-banner-text", item_details
            # ).text
            # print("Status", status)
            # name = self.find_element(
            #     By.CSS_SELECTOR, "h2.item-title", item_details
            # ).text
            # print("Name", name)
            # item_sku = ""
            # item_sku_div = self.find_element(
            #     By.CSS_SELECTOR, "div.item-variation", item_details
            # )
            # if item_sku_div:
            #     item_sku = item_sku_div.text
            # print("Item sku", item_sku)
            # div_item_info = self.find_element(
            #     By.CSS_SELECTOR, "div.item-div.item-info", item_container
            # )
            # price1 = self.find_element(
            #     By.CSS_SELECTOR,
            #     "span.info-displayprice span.BOLD",
            #     div_item_info,
            # ).text
            # print("Price 1", price1)
            # price2 = self.find_element(
            #     By.CSS_SELECTOR,
            #     "span.info-displayprice span.clipped",
            #     div_item_info,
            # ).text
            # print("Price 2", price2)
            # if price1 != price2:
            #     self.log.debug(
            #         self.command.style.SUCCESS(
            #             "PRICES DIFFER! TELL KAGEE!: '%s' '%s'"
            #         ),
            #         price1,
            #         price2,
            #     )
            # date = self.find_element(
            #     By.CSS_SELECTOR,
            #     "span.info-orderdate",
            #     div_item_info,
            # ).text
            # print("Date", date)

    def __init__(self, command: BaseCommand, options: Dict):
        super().__init__(command, options, __name__)

        self.setup_cache("ebay")
        self.setup_templates()
        self.load_imap()

    def load_imap(self):
        # pylint: disable=invalid-name
        self.IMAP_DATA = []
        if self.can_read(self.IMAP_JSON):
            self.IMAP_DATA = self.read(self.IMAP_JSON, from_json=True)

    def setup_cache(self, base_folder: Path):
        super().setup_cache(base_folder)
        # pylint: disable=invalid-name
        self.IMAP_JSON = Path(
            settings.SCRAPER_CACHE_BASE, "imap", "imap-ebay.json"
        )

    def command_db_to_csv(self):
        pass

    def command_load_to_db(self):
        pass

    # LXML-heavy functions
    # ...

    # Selenium-heavy function
    def browser_detect_handle_interrupt(self, expected_url):
        time.sleep(2)
        gdpr_accept = self.find_element(
            By.CSS_SELECTOR, "button#gdpr-banner-accept"
        )
        if gdpr_accept:
            self.log.debug("Accepting GDPR/cookies")
            gdpr_accept.click()
            time.sleep(0.5)
        else:
            self.log.debug("No GDPR/cookies to accept")
        if re.match(r".*captcha.*", self.browser.current_url):
            if self.find_element(By.CSS_SELECTOR, "div#captcha_loading"):
                self.log.info("Please complete captcha and press enter.")
                input()
        if re.match(self.LOGIN_PAGE_RE, self.browser.current_url):
            self.browser_login(expected_url)

    def browser_login(self, _):
        """
        Uses Selenium to log in eBay.
        Returns when the browser is at url, after login.

        Raises and alert in the browser if user action
        is required.
        """
        if settings.SCRAPER_EBY_MANUAL_LOGIN:
            self.log.debug(
                self.command.style.ERROR(
                    "Please log in to eBay and press enter when ready."
                )
            )
            input()
        else:
            # We (optionally) ask for this here and not earlier, since we
            # may not need to go live
            src_username = (
                input("Enter eBay username:")
                if not settings.SCRAPER_EBY_USERNAME
                else settings.SCRAPER_EBY_USERNAME
            )
            src_password = (
                getpass("Enter eBay password:")
                if not settings.SCRAPER_EBY_PASSWORD
                else settings.SCRAPER_EBY_PASSWORD
            )

            self.log.info(self.command.style.NOTICE("Trying to log in to eBay"))
            brws = self.browser_get_instance()

            wait = WebDriverWait(brws, 10)

            def captcha_test():
                if self.find_element(By.CSS_SELECTOR, "div#captcha_loading"):
                    self.log.info("Please complete captcha and press enter.")
                    input()

            try:
                self.rand_sleep(0, 2)
                captcha_test()
                self.log.debug("Looking for %s", "input#userid")
                username = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input#userid")
                    ),
                    "Could not find input#userid",
                )
                username.click()
                username.send_keys(src_username)
                self.rand_sleep(0, 2)
                self.log.debug("Looking for %s", "button#signin-continue-btn")
                wait.until(
                    EC.element_to_be_clickable(
                        ((By.CSS_SELECTOR, "button#signin-continue-btn"))
                    ),
                    "Could not find button#signin-continue-btn",
                ).click()
                self.rand_sleep(0, 2)

                captcha_test()
                self.log.debug("Looking for %s", "input#pass")
                password = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input#pass")
                    ),
                    "Could not find input#pass",
                )
                self.rand_sleep(2, 2)
                password.click()
                password.send_keys(src_password)
                self.rand_sleep(0, 2)

                self.log.debug("Looking for %s", "button#sgnBt")
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "button#sgnBt"),
                    ),
                    "Could not find button#sgnBt",
                ).click()
                self.rand_sleep(0, 2)
                captcha_test()
            except TimeoutException as toe:
                # self.browser_safe_quit()
                raise CommandError(
                    "Login to eBay was not successful "
                    "because we could not find a expected element.."
                ) from toe
        if re.match(self.LOGIN_PAGE_RE, self.browser.current_url):
            self.log.debug(
                "Login to eBay was not successful. If you want continue,"
                " complete login, and then press enter. Press Ctrl-Z to cancel."
            )
            input()
        self.log.info("Login to eBay was successful.")

    def browser_website_switch_mode(self, switch_to_mode=None):
        to_mobile_link = self.find_element(By.CSS_SELECTOR, "a#mobileCTALink")
        to_classic_link = self.find_element(
            By.CSS_SELECTOR, "div.gh-mwebfooter__siteswitch a"
        )
        if switch_to_mode == "mobile" and to_mobile_link:
            to_mobile_link.click()
            return True
        elif switch_to_mode == "classic" and to_classic_link:
            to_classic_link.click()
            return True
        elif not to_mobile_link and to_classic_link:
            self.log.debug("Failed to find a mode change link!!")
            raise CommandError("Failed to find a mode change link!!")
        else:
            return False

    # Utility functions
    def setup_templates(self):
        # pylint: disable=invalid-name
        login_url = re.escape("https://signin.ebay.com")
        self.HOMEPAGE = "https://ebay.com"
        self.LOGIN_PAGE_RE = rf"{login_url}.*"
        self.ORDER_LIST_URL = "https://www.ebay.com/mye/myebay/purchase"
        self.ORDER_LIST_URLv2 = "https://www.ebay.com/mye/myebay/v2/purchase"
        self.ITEM_URL_TEMPLATE = "https://www.ebay.com/itm/{item_id}"

        self.ORDER_URL_TEMPLATE_TRANS = "https://order.ebay.com/ord/show?transid={order_trans_id}&itemid={order_item_id}#/"
        self.ORDER_URL_TEMPLATE = (
            "https://order.ebay.com/ord/show?orderId={order_id}#/"
        )

        self.ORDER_FILENAME_TEMPLATE: Path = str(
            self.cache["ORDERS"] / Path("{order_id}/order.{ext}")
        )
        self.ORDER_ITEM_FILENAME_TEMPLATE: Path = str(
            self.cache["ORDERS"] / Path("{order_id}/item-{item_id}.{ext}")
        )

    def part_to_filename(self, part: PagePart, **kwargs):
        template: str
        if part == PagePart.ORDER_DETAILS:
            template = self.ORDER_FILENAME_TEMPLATE
        elif part == PagePart.ORDER_ITEM:
            template = self.ORDER_ITEM_FILENAME_TEMPLATE
        return Path(template.format(**kwargs))
