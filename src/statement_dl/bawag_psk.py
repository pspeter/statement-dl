import shutil
import time
from argparse import Namespace
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from statement_dl.utils import (
    get_driver,
    get_last_downloaded_filename,
    parse_date,
    wait_until_clickable,
)


def download_documents_from_args(args: Namespace):
    download_documents(
        Path(args.dest),
        parse_date(args.from_date),
        parse_date(args.to_date),
        args.geckodriver,
        args.username,
        args.password,
        args.all_files,
        args.headless,
        args.keep_filenames,
        args.wsl,
    )


def download_documents(
    dest: Path,
    from_date: date,
    to_date: date,
    geckodriver: Optional[str],
    user: Optional[str],
    pw: Optional[str],
    all_files: bool,
    headless: bool,
    keep_filenames: bool,
    wsl: bool,
) -> None:
    if headless and not (user and pw):
        raise ValueError(
            "Headless mode does not work without providing username and password"
            " in advance"
        )

    dest = dest.absolute()
    firefox_download_dir = str(dest)
    download_path = dest
    if wsl:
        # can't download directly to a wsl path since firefox expects a windows
        # path, need to use an intermediate download directory
        firefox_download_dir = "C:\\tmp"
        download_path = Path("/mnt/c/tmp")

    driver = get_driver(geckodriver, firefox_download_dir, headless)

    driver.get("https://ebanking.bawagpsk.com")
    _login(driver, user, pw)
    wait_until_clickable(driver, "//a[text()='Kontoauszugsliste']")
    driver.find_element_by_xpath("//a[text()='Kontoauszugsliste']").click()

    # wait until @id="confirm-container" not visible
    confirm_container = driver.find_element_by_xpath('//div[@id="confirm-container"]')
    print("Please enter TAN")
    WebDriverWait(driver, 300).until(ec.invisibility_of_element(confirm_container))

    dest.mkdir(exist_ok=True, parents=True)

    while True:
        # wait for menu to be visible again
        wait_until_clickable(driver, "//a[text()='anfordern']")
        rows = driver.find_elements_by_xpath(
            "//table[contains(@class, 'sort-table')]/tbody/tr"
        )

        for row in rows:
            row_date_str = row.find_element_by_xpath("./td[3]").text
            row_date = datetime.strptime(row_date_str, "%d.%m.%Y").date()
            ymd_row_date = row_date.strftime("%Y-%m-%d")
            # todo check if downloaded already
            _download_pdf(driver, row)
            downloaded_filename = get_last_downloaded_filename(driver)
            filename = (
                downloaded_filename
                if keep_filenames
                else f"{ymd_row_date}_Kontoauszug.pdf"
            )

            dest_file = dest / filename
            print(f"Saving file {dest_file}")
            pdf = download_path / downloaded_filename
            shutil.move(str(pdf), str(dest_file))

        next_button = driver.find_element_by_xpath(
            "//div[contains(@class, 'footer')]/a/span[text()='weiter']/.."
        )

        if "disabled" in next_button.get_attribute("class"):
            break

        next_button.click()
        wait_timeout = 30
        WebDriverWait(driver, wait_timeout).until(ec.staleness_of(next_button))


def _login(driver: webdriver.Firefox, user: Optional[str], pw: Optional[str]) -> None:
    wait_until_clickable(driver, '//button[text()="LOGIN"]')

    user_elem = driver.find_element_by_xpath('//div[@class="form-wrap"]/input[1]')
    if user:
        user_elem.send_keys(user)

    if pw:
        driver.find_element_by_xpath('//div[@class="form-wrap"]/input[2]').send_keys(pw)

    if user and pw:
        driver.find_element_by_xpath('//button[@text="LOGIN"]').click()
    else:
        user_elem.click()
        print("Please login")

    login_timeout = 300
    WebDriverWait(driver, login_timeout).until(ec.staleness_of(user_elem))
    time.sleep(1)


def _download_pdf(driver: webdriver.Firefox, row: WebElement) -> None:
    # the download call only returns once the download is finished, but we can
    # start another one even quicker if we just time out earlier
    driver.set_page_load_timeout(0.3)
    try:
        row.find_element_by_xpath(".//a[text()='anfordern']").click()
    except TimeoutException:
        pass

    driver.set_page_load_timeout(30)
