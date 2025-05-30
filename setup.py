from os import path
import re
from setuptools import setup, find_packages

from fb2cal.__meta__ import __title__, __version__, __description__, __license__, __author__, __email__, __github_url__, __github_short_url__, __github_assets_absolute_url__, __download_url__, __keywords__

def read(fname, base_url, base_image_url):
    """Read the content of a file."""
    with open(path.join(path.dirname(__file__), fname)) as fd:
        readme = fd.read()
    if hasattr(readme, 'decode'):
        # In Python 3, turn bytes into str.
        readme = readme.decode('utf8')
    # turn relative links into absolute ones
    readme = re.sub(r'`<([^>]*)>`__',
                    r'`\1 <' + base_url + r"/blob/main/\1>`__",
                    readme)
    readme = re.sub(r"\.\. image:: /", ".. image:: " + base_image_url + "/", readme)

    return readme

setup(
    name=__title__,
    version=__version__,
    description=__description__,
    packages=find_packages(),
    license=__license__,
    author=__author__,
    author_email=__email__,
    url=__github_short_url__,
    download_url=__download_url__,
    keywords=__keywords__,
    python_requires='>3.9',
    install_requires=[
        'MechanicalSoup',
        'ics>=0.6',
        'requests',
        'freezegun',
        'pycryptodomex',
        'PyNaCl',
    ],
    long_description=read('README.md', __github_url__, __github_assets_absolute_url__),
    long_description_content_type='text/markdown',
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
        'Programming Language :: Python :: 3.13',
    ],
)
