"""A setuptools based setup module for the parcel market 2 parcel tour connector.
"""

import pathlib
from os.path import join
from ast import literal_eval

from io import open

# Always prefer setuptools over distutils
from setuptools import setup, find_packages


here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

# Get the version from the __init__.py file
def get_version():
    """Scan __init__ file for __version__ and retrieve."""

    finit = join(here, 'src', 'mkt2tour', '__init__.py')
    with open(finit, 'r', encoding="utf-8") as fpnt:
        for line in fpnt:
            if line.startswith('__version__'):
                return literal_eval(line.split('=', 1)[1].strip())
    return '0.0.1-alpha'

setup(
    name='mkt2tour',
    version=get_version(),
    description='Connector between parcel market and parcel tour models',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Horizon-LEAD/Conn_Mkt2Tour',
    keywords='lead, parcel, market, tour',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.6, <4',
    install_requires=[
        'networkx',
        'pandas',
        'pyshp',
        'python-dotenv'
    ],
    entry_points={
        'console_scripts': [
            'mkt2tour=mkt2tour.__main__:main'
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/Horizon-LEAD/Conn_Mkt2Tour/issues',
        'Source': 'https://github.com/Horizon-LEAD/Conn_Mkt2Tour',
    }
)
