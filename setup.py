#!/usr/bin/env python

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
]

test_requirements = [
    'pytest',
]

setup(
    name='aioworkers',
    version='0.0.1',
    description="Easy configurable workers based on asyncio",
    long_description=readme + '\n\n' + history,
    author="Alexander Malev",
    author_email='yttrium@somedev.ru',
    url='https://github.com/aamalev/aioworkers',
    packages=find_packages(include=['aioworkers*']),
    include_package_data=True,
    install_requires=requirements,
    license="Apache Software License 2.0",
    keywords='aioworkers',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points={
        'console_scripts': [
            'aioworkers=aioworkers.cli:main'
        ]
    },
)
