#!/usr/bin/env python

from setuptools import find_packages, setup

version = __import__('aioworkers').__version__

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().split('\n' * 4, 4)
    history.pop()

requirements = [
]

test_requirements = [
    'pytest',
]

setup(
    name='aioworkers',
    version=version,
    description="Easy configurable workers based on asyncio",
    long_description='\n\n\n'.join([readme] + history),
    long_description_content_type='text/x-rst',
    author="Alexander Malev",
    author_email='yttrium@somedev.ru',
    url='https://github.com/aioworkers/aioworkers',
    packages=[i for i in find_packages() if i.startswith('aioworkers')],
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.6',
    license="Apache Software License 2.0",
    keywords='aioworkers',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points={
        'console_scripts': [
            'aioworkers=aioworkers.cli:main'
        ]
    },
)
