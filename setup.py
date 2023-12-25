from setuptools import setup, find_packages
from fb2cal.__meta__ import __title__, __version__, __description__, __license__, __author__, __email__, __min_python_version__, __website__, __download_url__, __keywords__

setup(
    name=__title__,
    version=__version__,
    description=__description__,
    packages=find_packages(),
    license=__license__,
    author=__author__,
    author_email=__email__,
    url=__website__,
    download_url=__download_url__,
    keywords=__keywords__,
    python_requires='>3.9',
    install_requires=[
        'MechanicalSoup',
        'ics>=0.6',
        'requests',
        'freezegun',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Other Audience',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
