from argparse import Namespace

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

from datetime import datetime, date
from pathlib import Path
import re
import shutil
import time
from typing import Optional
from urllib.parse import unquote


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
        _str_to_date(args.from_date),
        _str_to_date(args.to_date),
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

    driver = _get_driver(geckodriver, firefox_download_dir, headless)
    driver.get(f"http://www.flatex.{tld}/kunden-login/")
    _login(driver, user, pw)
    _go_to_documents_tab(driver)
    set_download_filter(driver, from_date, to_date, all_files)

    try:
        _download_pdfs(driver, dest, download_path, keep_filenames)
    finally:
        try:
            driver.find_element_by_xpath(
                '//div[contains(@class, "LogoutArea")]'
            ).click()
        finally:
            driver.close()

    print("Done!")


def _str_to_date(date_string: str) -> date:
    if date_string == "today":
        return date.today()
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def _get_driver(
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


def _login(driver: webdriver.Firefox, user: Optional[str], pw: Optional[str]) -> None:
    if user:
        driver.find_element_by_xpath('//input[@id="uname_app"]').send_keys(user)
    if pw:
        driver.find_element_by_xpath('//input[@id="password_app"]').send_keys(pw)
    if user and pw:
        driver.find_element_by_xpath('//div[@title="Anmelden"]').click()
    else:
        driver.find_element_by_xpath('//input[@id="uname_app"]').click()
        print("Please login")
    login_timeout = 300
    WebDriverWait(driver, login_timeout).until(ec.title_is("Onlinebanking"))
    time.sleep(1)


def _go_to_documents_tab(driver: webdriver.Firefox) -> None:
    driver.find_element_by_xpath('//td[@id="menu_mailMenu"]').click()
    driver.find_element_by_xpath('//*[text()="Dokumentenarchiv"]').click()
    time.sleep(1)


def set_download_filter(
    driver: webdriver.Firefox, from_date: date, to_date: date, all_files: bool
) -> None:
    # select all or unread
    driver.find_element_by_xpath('//div[contains(@id, "readState")]').click()
    selected_option = "0" if all_files else "2"
    driver.find_element_by_xpath(
        f'//div[@id="documentArchiveListForm_readState_item_{selected_option}"]'
    ).click()
    # expand date range
    date_from_elem = driver.find_element_by_xpath(
        '//input[contains(@id, "dateRangeComponent_startDate")]'
    )
    date_to_elem = driver.find_element_by_xpath(
        '//input[contains(@id, "dateRangeComponent_endDate")]'
    )
    _enter_date(driver, date_from_elem, from_date)
    _enter_date(driver, date_to_elem, to_date)
    # hit search
    driver.find_element_by_xpath('//input[contains(@id, "applyFilterButton")]').click()
    time.sleep(1)


def _enter_date(driver, date_elem, desired_date: date):
    driver.execute_script(
        'arguments[0].removeAttribute("readonly", "readonly")', date_elem
    )
    date_elem.click()
    date_elem.send_keys(Keys.BACKSPACE * 10)  # delete old date
    date_elem.send_keys(desired_date.strftime("%d.%m.%Y"))
    date_elem.send_keys(Keys.ENTER)


def _download_pdfs(
    driver: webdriver.Firefox, dest: Path, download_path: Path, keep_filenames: bool
) -> None:
    # the driver.get call that downloads the pdf does not return normally, so
    # we have to wait for it to time out default timeout is a couple minutes,
    # but 3 seconds should be enough to start the download
    driver.set_page_load_timeout(3)

    num_files = len(driver.find_elements_by_xpath(f'//table[@class="Data"]/tbody/tr'))

    print(f"Downloading files to {str(download_path)}")
    driver.execute_script(onfinished)
    for file_idx in range(num_files):
        driver.execute_script("window.pdf_download_url = ''")
        url = ""
        elems = driver.find_elements_by_xpath(
            f'//table[@class="Data"]/tbody/tr[{file_idx + 1}]/td'
        )
        if not elems:
            continue

        _, dmy_date_string, doc_type, raw_doc_title, _ = (e.text for e in elems)
        file_date = datetime.strptime(dmy_date_string, "%d.%m.%Y").date()
        ymd_date_string = file_date.strftime("%Y-%m-%d")

        print()
        print()
        print(f"File #{file_idx + 1}")
        print("Date:", dmy_date_string)
        print("Type:", doc_type)
        print("Name:", raw_doc_title)

        driver.execute_script("window.pdf_download_url = ''")
        row = driver.find_element_by_xpath(
            f'//table[@class="Data"]/tbody/tr[{file_idx + 1}]'
        )
        driver.execute_script(onclick.format(file_idx), row)

        time.sleep(0.3)
        while not url or url == "none":
            time.sleep(0.1)
            url = driver.execute_script("return window.pdf_download_url")

        dest_dir = dest / re.sub(r"_+", "_", re.sub(r"\W", "_", doc_type))

        downloaded_file_name = unquote(url).split("/")[-1]
        if keep_filenames:
            file_name = downloaded_file_name
        else:
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
                f"{ymd_date_string}_{file_name}_{doc_id}.pdf"
                if doc_id
                else f"{ymd_date_string}_{file_name}.pdf"
            )

        dest_file = dest_dir / file_name

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
        pdf = download_path / downloaded_file_name
        shutil.move(str(pdf), str(dest_file))
