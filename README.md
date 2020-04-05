# statement-dl

This tool is built to be able to automatically download all documents from 
online banks and brokes that don't offer batch download options themselves, 
since it is usually quite cumbersome to download each file individually. The
automatic download is especially useful when used in conjunction with portfolio 
tracking tools like 
[portfolio performance](https://www.portfolio-performance.info/) that are able
to subsequently import the downloaded PDFs. The downloaded files are 
sorted into separate subdirectories based on the document type.

Currently, only flatex is supported. PRs are welcome!

## Installation

This Python tool currently uses Firefox and geckodriver to find and download
your files. You can download Firefox from the mozilla homepage: 
https://www.mozilla.org/de/.

You can download geckodriver from Github: 
https://github.com/mozilla/geckodriver/releases.

Then, download `statement-dl` using pip: `pip install -U statement-dl` or simply
clone the repository and install from source using 
`pip install -U <repository-path>`. If you don't want to install the tool and 
its dependencies into your global python environment, I recommended using 
[pipx](https://github.com/pipxproject/pipx) instead of pip directly.


## Usage

To start off, you probably want to download all your previous documents. By default, 
the tool only downloads the unread files. To download all files from flatex, use the
command 

`>>> statement_dl <destination dir> --all-files`

If you don't specify the `--username` and `--password` options, you will be prompted
to enter them yourself in the browser.

To see all options, type

`>>> statement_dl --help`

To get all options for a specific broker/bank, type e.g.

```
>>> statement_dl flatex --help
usage: statement_dl flatex [-h] [-f DATE] [-t DATE] [-g PATH] [-u USERNAME]
                           [-p PASSWORD] [--wsl] [--headless] [-a] [-k] [--de]
                           dest

positional arguments:
  dest                  Directory in which your downloaded files will be saved

optional arguments:
  -h, --help            show this help message and exit
  -f DATE, --from-date DATE
                        Date from which you want to download your files (in
                        the format YYYY-MM-DD or 'today'). Defaults to
                        '2010-01-01'
  -t DATE, --to-date DATE
                        Date until which you want to download your files (in
                        the format YYYY-MM-DD or 'today'). Defaults to 'today'
  -g PATH, --geckodriver PATH
                        Path to geckodriver executable. If not specified, it
                        will look for it in the Path
  -u USERNAME, --username USERNAME
                        Username for automatic login
  -p PASSWORD, --password PASSWORD
                        Password for automatic login
  --wsl                 Set this option when running the script in WSL while
                        using a geckodriver executable that was installed on
                        Windows
  --headless            Launch browser in headless mode. This only works if
                        username and password are set
  -a, --all-files       Automatically download all files instead of only
                        unread
  -k, --keep-filenames  Keep the original filenames instead of renaming them
                        to a more useful format
  --de                  Use 'de' domain instead of 'at' (experimental)
```
