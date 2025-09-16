from setuptools import setup, find_packages

setup(
    name="prismind",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # Add your project's dependencies here
        "streamlit>=1.0.0",
        "pandas",
        "python-dotenv",
        "requests",
        "playwright",
    ],
    python_requires=">=3.8",
)
