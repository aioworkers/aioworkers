#!/usr/bin/env python

from setuptools import find_packages, setup

version = __import__('aioworkers').__version__

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
    version=version,
    description="Easy configurable workers based on asyncio",
    long_description=readme + '\n\n' + history,
    author="Alexander Malev",
    author_email='yttrium@somedev.ru',
    url='https://github.com/aioworkers/aioworkers',
    packages=[i for i in find_packages() if i.startswith('aioworkers')],
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.5.3',
    license="Apache Software License 2.0",
    keywords='aioworkers',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points={
        'console_scripts': [
            'aioworkers=aioworkers.cli:main_with_conf'
        ]
    },
)
