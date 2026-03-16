from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="jobsearcher",
    version="0.1.0",
    author="JobSearcher Team",
    author_email="contact@jobsearcher.dev",
    description="AI-Powered Job Search Agent System with CrewAI and LinkedIn MCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/jobsearcher",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "jobsearcher=src.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
