"""
Setup script for GitHub-Devin Integration Dashboard.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="github-devin-dashboard",
    version="1.0.0",
    author="GitHub-Devin Dashboard Team",
    author_email="support@example.com",
    description="Dashboard for integrating GitHub Issues with Devin AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/github-devin-dashboard",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Topic :: Software Development :: Tools",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "github-devin-dashboard=app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": ["static/**/*", "templates/**/*"],
    },
)
