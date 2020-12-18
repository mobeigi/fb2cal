from setuptools import setup, find_packages
from fb2cal.__meta__ import __title__, __version__, __description__, __license__, __author__, __email__, __website__

setup(
    name=__title__,
    version=__version__,
    description=__description__,
    packages=find_packages(),
    license=__license__,
    author=__author__,
    author_email=__email__,
    url=__website__
)
