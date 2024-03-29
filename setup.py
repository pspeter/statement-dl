from setuptools import setup, find_packages

with open("README.md", "r") as fp:
    long_description = fp.read()

setup(
    name="statement-dl",
    version="2023.07.1",
    description="Automatic download of banking/broker documents from flatex",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pspeter/statement-dl",
    author="Peter Schmidbauer",
    author_email="peter.schmidb@gmail.com",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["selenium==4.*"],
    python_requires=">=3.8",
    zip_safe=False,
    entry_points={"console_scripts": ["statement_dl = statement_dl:main"]},
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
