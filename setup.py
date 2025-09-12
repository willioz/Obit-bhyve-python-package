from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="orbit-bhyve",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Python package for controlling Orbit Bhyve irrigation controllers",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/orbit-bhyve-python-package",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/orbit-bhyve-python-package/issues",
        "Documentation": "https://github.com/yourusername/orbit-bhyve-python-package#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "pytest-mock>=3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "orbit-bhyve=orbit_bhyve.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
