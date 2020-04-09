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
    DownloadDocumentBrowserBehaviorsClick.finished = function(a, b) {
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
    driver.get(f"http://www.flatex.{tld}/kunden-login/")
    _login(driver, user, pw, headless)
    _go_to_documents_tab(driver)

    try:
        _download_pdfs(
            driver, from_date, to_date, dest, download_path, all_files, keep_filenames
        )
    finally:
        try:
            _click(
                driver,
                driver.find_element_by_xpath('//div[contains(@class, "LogoutArea")]'),
            )
        finally:
            driver.close()

    print("Done!")


def _login(
    driver: webdriver.Firefox, user: Optional[str], pw: Optional[str], headless: bool
) -> None:
    user_input = driver.find_element_by_xpath('//input[@id="uname_app"]')
    pw_input = driver.find_element_by_xpath('//input[@id="password_app"]')

    while not user and headless:
        user = input("Enter your flatex username: ")

    while not pw and headless:
        pw = getpass("Enter your flatex password: ")

    if user:
        user_input.send_keys(user)

    if pw:
        pw_input.send_keys(pw)

    if user and pw:
        driver.find_element_by_xpath('//div[@title="Anmelden"]').click()
    else:
        driver.find_element_by_xpath('//input[@id="uname_app"]').click()
        print("Please login in the browser")

    login_timeout = 300
    WebDriverWait(driver, login_timeout).until(ec.title_is("Onlinebanking"))
    time.sleep(1)


def _go_to_documents_tab(driver: webdriver.Firefox) -> None:
    driver.find_element_by_xpath('//td[@id="menu_mailMenu"]').click()
    driver.find_element_by_xpath('//*[text()="Dokumentenarchiv"]').click()
    time.sleep(1)


def _download_pdfs(
    driver: webdriver.Firefox,
    from_date: date,
    to_date: date,
    dest: Path,
    download_path: Path,
    all_files: bool,
    keep_filenames: bool,
) -> None:
    _set_download_filter(driver, from_date, to_date, all_files)

    print(f"Downloading files to {str(download_path)}")

    # the driver.get call that downloads the pdf does not return normally, so
    # we have to wait for it to time out default timeout is a couple minutes,
    # but 3 seconds should be enough to start the download
    driver.set_page_load_timeout(3)

    rows = driver.find_elements_by_xpath(f'//table[@class="Data"]/tbody/tr')
    num_files = len(rows)
    max_loaded_files = 100

    while num_files == max_loaded_files:
        # only 100 files are displayed at most, so we need to do some manual
        # paging using the date filters
        print("More than 100 files, paging through results")
        last_date_string = driver.find_element_by_xpath(
            f"//table[@class='Data']/tbody/tr[last()]/td[2]"
        ).text
        last_date = _parse_list_date(last_date_string)
        day_after_last_date = last_date + timedelta(days=1)
        _set_download_filter(driver, day_after_last_date, to_date, all_files)
        _download_current_pdfs(driver, download_path, dest, all_files, keep_filenames)
        # set filter to cover the range of files we haven't downloaded yet
        _set_download_filter(driver, from_date, last_date, all_files)
        rows = driver.find_elements_by_xpath(f'//table[@class="Data"]/tbody/tr')
        num_files = len(rows)

    _download_current_pdfs(driver, download_path, dest, all_files, keep_filenames)


def _set_download_filter(
    driver: webdriver.Firefox, from_date: date, to_date: date, all_files: bool
) -> None:
    # flatex treats from date as exclusive, which is unintuitive, so let's
    # subtract 1 day
    from_date = from_date - timedelta(days=1)
    # select all or unread
    _click(driver, driver.find_element_by_xpath('//div[contains(@id, "readState")]'))
    selected_option = "0" if all_files else "2"
    _click(
        driver,
        driver.find_element_by_xpath(
            f'//div[@id="documentArchiveListForm_readState_item_{selected_option}"]'
        ),
    )
    # expand date range
    date_from_elem = driver.find_element_by_xpath(
        '//input[contains(@id, "dateRangeComponent_startDate")]'
    )
    date_to_elem = driver.find_element_by_xpath(
        '//input[contains(@id, "dateRangeComponent_endDate")]'
    )
    _enter_date(driver, date_from_elem, from_date)
    _enter_date(driver, date_to_elem, to_date)

    try:
        wait_elem = driver.find_element_by_xpath(
            "//table[@class='Data']/tbody/tr[last()]"
        )
    except NoSuchElementException:
        wait_elem = driver.find_element_by_xpath(
            "//div[text()='Keine Dokumente vorhanden.']"
        )

    # hit search
    _click(
        driver,
        driver.find_element_by_xpath('//input[contains(@id, "applyFilterButton")]'),
    )
    try:
        timeout = 5
        WebDriverWait(driver, timeout).until(ec.staleness_of(wait_elem))
    except TimeoutException:
        pass  # filter hasn't changed elements


def _enter_date(driver, date_elem, desired_date: date):
    driver.execute_script(
        'arguments[0].removeAttribute("readonly", "readonly")', date_elem
    )
    _click(driver, date_elem)
    date_elem.send_keys(Keys.BACKSPACE * 10)  # delete old date
    date_elem.send_keys(desired_date.strftime("%d.%m.%Y"))
    date_elem.send_keys(Keys.ENTER)
    time.sleep(0.1)


def _download_current_pdfs(driver, download_path, dest, all_files, keep_filenames):
    driver.execute_script(onfinished)
    num_files = len(driver.find_elements_by_xpath(f'//table[@class="Data"]/tbody/tr'))

    for file_idx in range(num_files):
        driver.execute_script("window.pdf_download_url = ''")
        url = ""
        # when we read a previously unread file, it disappears from the list, so
        # have to keep reading the first file
        download_idx = file_idx + 1 if all_files else 1
        elems = driver.find_elements_by_xpath(
            f'//table[@class="Data"]/tbody/tr[{download_idx}]/td'
        )
        if not elems:
            continue

        _, dmy_date_string, doc_type, raw_doc_title, _ = (e.text for e in elems)
        file_date = _parse_list_date(dmy_date_string)
        ymd_date_string = file_date.strftime("%Y-%m-%d")

        print()
        print("Date:", dmy_date_string)
        print("Type:", doc_type)
        print("Name:", raw_doc_title)

        row = driver.find_element_by_xpath(
            f'//table[@class="Data"]/tbody/tr[{file_idx + 1}]'
        )
        driver.execute_script(onclick.format(file_idx), row)

        time.sleep(0.3)
        while not url or url == "none":
            time.sleep(0.1)
            url = driver.execute_script("return window.pdf_download_url")

        dest_dir = dest / re.sub(r"_+", "_", re.sub(r"\W", "_", doc_type))

        downloaded_filename = unquote(url).split("/")[-1]
        if keep_filenames:
            filename = downloaded_filename
        else:
            filename = _proper_filename(
                downloaded_filename, raw_doc_title, ymd_date_string
            )

        dest_file = dest_dir / filename

        if dest_file.exists():
            print("Already downloaded, skipping:", url)
            time.sleep(0.5)
            continue

        time.sleep(1)
        try:
            print(f"Downloading pdf from url {url}")
            driver.get(f"https://konto.flatex.at{url}")
        except TimeoutException:
            pass

        print(f"Saving file {dest_file}")
        dest_dir.mkdir(exist_ok=True, parents=True)
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
    retry = driver.find_elements_by_xpath(
        "//input[@id='previousActionNotFinishedOverlayForm_retryButton']"
    )
    if retry:
        retry[0].click()

    elem.click()


def _parse_list_date(date_string: str) -> date:
    return datetime.strptime(date_string, "%d.%m.%Y").date()
