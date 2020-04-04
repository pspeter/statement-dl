# statement-dl

This tool is built to be able to automatically download all documents from 
online banks and brokes that don't offer batch download options themselves, 
since it is usually quite cumbersome to download each file individually. The
automatic download is especially useful when used in conjunction with portfolio 
tracking tools like 
[portfolio performance](https://www.portfolio-performance.info/) that are able
to subsequently import the downloaded PDFs.

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

To start off, you probably want to download all your previous documents. To download
them from flatex, use the command 

`statement_dl <destination dir> --all`

To see all options, type

`statement_dl --help`


