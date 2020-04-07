from datetime import date, datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.firefox.options import Options


def parse_date(date_string: str) -> date:
    if date_string == "today":
        return date.today()
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def get_driver(
    geckodriver: Optional[str], download_dir: str, headless: bool
) -> webdriver.Firefox:
    fp = webdriver.FirefoxProfile()
    fp.set_preference("browser.download.folderList", 2)
    fp.set_preference("browser.helperApps.alwaysAsk.force", False)
    fp.set_preference("browser.download.dir", download_dir)
    fp.set_preference("pdfjs.disabled", True)
    fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    fp.set_preference("browser.download.manager.showWhenStarting", False)

    options = Options()
    options.headless = headless

    geckodriver = geckodriver if geckodriver else "geckodriver"
    driver = webdriver.Firefox(fp, options=options, executable_path=geckodriver)
    return driver
