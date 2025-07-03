import re
import shutil
import time
from argparse import Namespace
from datetime import date, datetime, timedelta
from getpass import getpass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from statement_dl.utils import get_driver, parse_date

# JavaScript snippets used to trigger the downloads
onclick = """
    console.log(arguments[0]);
    WebcoreUtils.addHiddenField(
        arguments[0], 'documentArchiveListTable.selectedRowIdx', '{}'
    );
    ajaxEngine.submitForm(arguments[0], false);
    WebcoreUtils.removeHiddenField(
        arguments[0], 'documentArchiveListTable.selectedRowIdx'
    );
"""


onfinished = """
    DocumentViewer.display = function(a, b) {
       console.log(a);
       window.pdf_download_url = a;
    };
"""


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
        args.sub_dirs,
        args.keep_filenames,
        args.de,
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
    sub_dirs: bool,
    keep_filenames: bool,
    de: bool,
    wsl: bool,
) -> None:
    if headless and not (user and pw):
        raise ValueError(
            "Headless mode does not work without providing username and password"
            " in advance"
        )

    tld = "de" if de else "at"
    dest = dest.absolute()
    firefox_download_dir = str(dest)
    download_path = dest
    if wsl:
        # can't download directly to a wsl path since firefox expects a windows
        # path, need to use an intermediate download directory
        firefox_download_dir = "C:\\tmp"
        download_path = Path("/mnt/c/tmp")

    driver = get_driver(geckodriver, firefox_download_dir, headless)
    driver.get(f"http://konto.flatex.{tld}/")
    _login(driver, user, pw, headless)
    _accept_cookies(driver)
    _go_to_documents_tab(driver)

    try:
        _download_pdfs(
            driver,
            from_date,
            to_date,
            dest,
            download_path,
            all_files,
            keep_filenames,
            sub_dirs,
            tld,
        )
    finally:
        try:
            _click(
                driver,
                driver.find_element(By.XPATH, '//div[contains(@class, "LogoutArea")]'),
            )
        finally:
            driver.close()

    print("Done!")


def _wait_and_click(driver: webdriver.Firefox, elem: WebElement | tuple[str, str], timeout: float=10) -> None:
    WebDriverWait(driver, timeout).until(ec.element_to_be_clickable(elem))
    if isinstance(elem, tuple):
        elem = driver.find_element(*elem)
    elem.click()


def _accept_cookies(driver: webdriver.Firefox) -> None:
    _wait_and_click(driver, elem=(By.XPATH, '//button[text()="Alle akzeptieren"]'))
    time.sleep(1)


def _login(
    driver: webdriver.Firefox, user: Optional[str], pw: Optional[str], headless: bool) -> None:
    time.sleep(1)

    formid_user, formid_pw, formid_btn = "txtUserId", "txtPassword_txtPassword", "btnLogin"

    user_input = driver.find_element(By.XPATH, f'//input[@id="loginForm_{formid_user}"]')
    pw_input = driver.find_element(By.XPATH, f'//input[@id="loginForm_{formid_pw}"]')

    while not user and headless:
        user = input("Enter your flatex username: ")

    while not pw and headless:
        pw = getpass("Enter your flatex password: ")

    if user:
        user_input.send_keys(user)

    if pw:
        pw_input.send_keys(pw)

    if user and pw:
        driver.find_element(By.XPATH, f'//input[@id="loginForm_{formid_btn}"]').click()
    else:
        driver.find_element(By.XPATH, f'//input[@id="loginForm_{formid_user}"]').click()
        print("Please login in the browser")

    login_timeout = 300
    WebDriverWait(driver, login_timeout).until(
        ec.presence_of_element_located((By.CLASS_NAME, "AccountOverviewMenuTab"))
    )
    time.sleep(1)


def _go_to_documents_tab(driver: webdriver.Firefox) -> None:
    settings_button = WebDriverWait(driver, 60).until(
        ec.presence_of_element_located((By.CLASS_NAME, "SettingsButtonWidget"))
    )
    settings_button.click()
    driver.find_element(By.CLASS_NAME, "OpenDocumentArchive").click()
    WebDriverWait(driver, 60).until(
        ec.presence_of_element_located(
            (By.CLASS_NAME, 'DocumentArchiveListSubForm')
        )
    )


def _download_pdfs(
    driver: webdriver.Firefox,
    from_date: date,
    to_date: date,
    dest: Path,
    download_path: Path,
    all_files: bool,
    keep_filenames: bool,
    sub_dirs: bool,
    tld: str,
) -> None:
    _set_download_filter(driver, from_date, to_date, all_files)

    print(f"Downloading files to {str(download_path)}")

    # the driver.get call that downloads the pdf does not return normally, so
    # we have to wait for it to time out. Default timeout is a couple minutes,
    # but 3 seconds should be enough to start the download
    driver.set_page_load_timeout(3)
    _download_filtered_pdfs(driver, download_path, dest, all_files, keep_filenames, sub_dirs, tld)


def _check_if_max_documents_displayed(driver: webdriver.Firefox) -> bool:
    max_documents_displayed_txt = 'Es werden nur die ersten 100 Dokumente dargestellt.'
    max_documents_elems = driver.find_elements(By.XPATH, f'//div[text()="{max_documents_displayed_txt}"]')
    are_max_documents_displayed = len(max_documents_elems) != 0
    return are_max_documents_displayed


def _set_download_filter(
    driver: webdriver.Firefox, from_date: date, to_date: date, all_files: bool
) -> None:
    print(f"Setting download filter to {from_date} - {to_date}, {all_files=}")
    # select all or unread
    selected_option = "Alle" if all_files else "Nur Ungelesene"
    _click(
        driver,
        driver.find_element(
            By.XPATH,
            f"//div[@class='Left']/div/div/a[normalize-space(text())='{selected_option}']"
        ),
    )

    # select time range
    _click(driver, driver.find_element(By.CLASS_NAME, 'DateRangePeriodSelectionWidget'))
    _click(
        driver,
        driver.find_element(
            By.XPATH,
            f"//div[@class='DateRangePeriodSelectionWidget']/div[normalize-space(text())='individuell']"
        ),
    )

    time.sleep(1)
    # expand date range
    date_from_elem = driver.find_element(
        By.XPATH,
        "//div[@class='DateRangeSelectionInputArea']/div[div/div[normalize-space(text())='Von']]//input"
    )
    date_to_elem = driver.find_element(
        By.XPATH,
        "//div[@class='DateRangeSelectionInputArea']/div[div/div[normalize-space(text())='Bis']]//input"
    )
    _enter_date(driver, date_from_elem, from_date)
    _enter_date(driver, date_to_elem, to_date)
    _click(driver, driver.find_element(
        By.XPATH, "//div[@class='DateRangeSelectionInputView']//div[@class='Button']"
    ))
    time.sleep(3)


def _enter_date(driver, date_elem, desired_date: date):
    _click(driver, date_elem)
    date_elem.send_keys(Keys.BACKSPACE * 10)  # delete old date
    date_elem.send_keys(desired_date.strftime("%d%m%Y"))
    time.sleep(0.1)


def _download_filtered_pdfs(driver, download_path, dest, all_files, keep_filenames, sub_dirs: bool, tld):
    driver.execute_script(onfinished)
    num_files = len(driver.find_elements(
        By.XPATH,
        f'//div[@class="DocumentArchiveListEntries"]/div[@class="EntryWidgetAsSingleTilesArea"]'
    ))

    for file_idx in range(num_files):
        driver.execute_script("window.pdf_download_url = ''")
        url = ""
        # when we read a previously unread file, it disappears from the list, so
        # have to keep reading the first file
        download_idx = file_idx + 1 if all_files else 1
        
        dmy_date_string = driver.find_element(
            By.XPATH,
            f'//div[@class="DocumentArchiveListEntries"]/div[contains(@class, "DocumentDate")][{download_idx}]'
        ).text

        raw_doc_title = driver.find_element(
            By.XPATH,
            f'//div[@class="DocumentArchiveListEntries"]/div[@class="EntryWidgetAsSingleTilesArea"][{download_idx}]//div[@class="Description"]'
        ).text

        file_date = _parse_list_date(dmy_date_string)
        ymd_date_string = file_date.strftime("%Y-%m-%d")

        print()
        print("Date:", dmy_date_string)
        print("Name:", raw_doc_title)

        row = driver.find_element(By.XPATH, 
            f'//div[@class="DocumentArchiveListEntries"]/div[@class="EntryWidgetAsSingleTilesArea"][{download_idx}]'
        )
        driver.execute_script(onclick.format(download_idx - 1), row)

        time.sleep(0.3)
        while not url or url == "none":
            time.sleep(0.1)
            url = driver.execute_script("return window.pdf_download_url")

        downloaded_filename = unquote(url).split("/")[-1]
        if keep_filenames:
            filename = downloaded_filename
        else:
            filename = _proper_filename(
                downloaded_filename, raw_doc_title, ymd_date_string
            )

        dest_file = dest / filename

        if dest_file.exists():
            print("Already downloaded, skipping:", url)
            time.sleep(0.5)
            continue

        time.sleep(1)
        try:
            print(f"Downloading pdf from url {url}")
            driver.get(f"https://konto.flatex.{tld}{url}")
        except TimeoutException:
            pass

        print(f"Saving file {dest_file}")
        dest.mkdir(exist_ok=True, parents=True)
        pdf = download_path / downloaded_filename
        shutil.move(str(pdf), str(dest_file))


def _proper_filename(
    downloaded_file_name: str, raw_doc_title: str, date_string: str
) -> str:
    doc_id_match = re.search(r"(\d+).pdf", downloaded_file_name)
    doc_id = doc_id_match.group(1) if doc_id_match else None
    # remove date from back of title
    file_name = re.sub(r" vom \d\d\.\d\d.\d\d\d\d$", "", raw_doc_title)
    # replace special chars
    file_name = re.sub(r"\W", "_", file_name)
    file_name = re.sub(r"_+", "_", file_name)
    file_name = file_name.strip("_")
    # prepend date, append doc id
    file_name = (
        f"{date_string}_{file_name}_{doc_id}.pdf"
        if doc_id
        else f"{date_string}_{file_name}.pdf"
    )

    return file_name


def _click(driver: webdriver.Firefox, elem: WebElement) -> None:
    retry = driver.find_elements(By.XPATH, 
        "//input[@id='previousActionNotFinishedOverlayForm_retryButton']"
    )
    if retry:
        retry[0].click()

    elem.click()


def _parse_list_date(date_string: str) -> date:
    return datetime.strptime(date_string, "%d.%m.%Y").date()
