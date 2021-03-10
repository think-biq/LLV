"""    
    setuptools script to install / build LLV (Live Link VOMiT).

    2021-∞ (c) blurryroots innovation qanat OÜ. All rights reserved.
    See license.md for details.

    https://think-biq.com
"""

import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

from src.llv import version

setuptools.setup(
    name="llv",
    version=version(),
    author="biq",
    author_email="sf@think-biq.com",
    description="CLI tool for recording or replaying Epic Games' live link face capture frames.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/think-biq/LiveLinkVomit",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': ['llv = src.llv.cli:main'],
    }
)