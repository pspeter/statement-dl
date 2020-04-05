from setuptools import setup

with open("README.md", "r") as fp:
    long_description = fp.read()

setup(
    name="statement-dl",
    version="2020.04.05-post1",
    description="Automatic download of banking/broker documents from flatex",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pspeter/statement-dl",
    author="Peter Schmidbauer",
    author_email="peter.schmidb@gmail.com",
    license="MIT",
    packages=["statement_dl"],
    install_requires=["selenium>=3.141.0,<4.0.0"],
    python_requires=">=3.6",
    zip_safe=False,
    entry_points={"console_scripts": ["statement_dl = statement_dl:main"]},
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
