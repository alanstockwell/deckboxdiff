import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='deckboxdiff',
    version='0.1.3',
    author='Alan Stockwell',
    author_email='alan.stockwell@gmail.com',
    description='Helper classes and functions for deriving the difference between two deckbox exports',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alanstockwell/deckboxdiff',
    packages=setuptools.find_packages(),
    install_requires=[
        'python-dateutil',
        'openpyxl',
        'pandas',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
