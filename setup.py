from setuptools import setup, find_packages

setup(
    name="investment-master",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "openai>=1.12.0",
        "anthropic>=0.18.1",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-mock>=3.14.0",
    ],
    python_requires=">=3.8",
    author="Brett Gray",
    description="Investment analysis and portfolio optimization tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
) 