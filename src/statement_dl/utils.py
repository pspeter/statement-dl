from datetime import date, datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.firefox.service import Service


def parse_date(date_string: str) -> date:
    if date_string == "today":
        return date.today()
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def get_driver(
    geckodriver: Optional[str], download_dir: str, headless: bool
) -> webdriver.Firefox:
    options = webdriver.FirefoxOptions()
    options.headless = headless
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.helperApps.alwaysAsk.force", False)
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference("pdfjs.disabled", True)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    options.set_preference("browser.download.manager.showWhenStarting", False)

    geckodriver = geckodriver if geckodriver else "geckodriver"
    service = Service(executable_path=geckodriver)

    driver = webdriver.Firefox(options=options, service=service)
    return driver
