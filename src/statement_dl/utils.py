import time
from datetime import date, datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

_download_handle: Optional[str] = None


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


def get_last_downloaded_filename(driver: webdriver.Firefox) -> str:
    global _download_handle
    if not _download_handle:
        driver.execute_script("window.open()")
        WebDriverWait(driver, 10).until(ec.new_window_is_opened)
        driver.switch_to.window(driver.window_handles[-1])
        driver.get("about:downloads")
        _download_handle = driver.window_handles[-1]
        time.sleep(0.5)
    else:
        driver.switch_to.window(_download_handle)

    wait_until_clickable(
        driver, "//*[@id='downloadsRichListBox']/*[1]//*[@class='downloadTarget']"
    )
    download_box = driver.find_element_by_xpath(
        "//*[@id='downloadsRichListBox']/*[1]//*[@class='downloadProgress']"
    )
    # wait until download is finished
    WebDriverWait(driver, 300).until(ec.invisibility_of_element(download_box))

    filename = driver.find_element_by_xpath(
        "//*[@id='downloadsRichListBox']/*[1]//*[@class='downloadTarget']"
    ).get_attribute("value")

    # delete last downloaded list to not accidentally find the same ones again later
    driver.find_element_by_xpath("//*[@id='downloadsRichListBox']").send_keys(
        Keys.ARROW_DOWN + Keys.DELETE
    )
    WebDriverWait(driver, 3).until(ec.staleness_of(download_box))
    driver.switch_to.window(driver.window_handles[0])

    return filename


def wait_until_clickable(driver: webdriver.Firefox, xpath: str) -> None:
    load_timeout = 300
    WebDriverWait(driver, load_timeout).until(
        ec.element_to_be_clickable((By.XPATH, xpath))
    )
