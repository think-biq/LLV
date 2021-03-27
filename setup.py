"""    
    setuptools script to install / build LLV.

    2021-∞ (c) blurryroots innovation qanat OÜ. All rights reserved.
    See license.md for details.

    https://think-biq.com
"""

import setuptools
from src.llv import version

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="llv",
    version=version(),
    author="biq",
    author_email="sf@think-biq.com",
    description="CLI tool for recording or replaying Epic Games' live link face capture frames.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/think-biq/LLV",
    package_dir = {'llv': 'src/llv'},
    packages=['llv'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    entry_points={
        'console_scripts': ['llv = llv.cli:main'],
    }
)