from setuptools import setup, find_packages

setup(
    name="modernauth",
    version="1.2.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    install_requires=[
        "Flask", "Authlib", "python-dotenv",
        "SQLAlchemy", "PyMySQL", "Flask-Limiter",
        "requests"
    ],
    entry_points={
        "console_scripts": {
            # optional: install a CLI entry point
            "modernauth = modernauth.app:app"
        }
    }
)
