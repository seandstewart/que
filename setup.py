#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import dataclasses
import inspect
import os
import pathlib
import sys
import typing
from shutil import rmtree

from setuptools import setup, Command


@dataclasses.dataclass
class About:
    title: str = None
    description: str = None
    url: str = None
    version: str = None
    author: str = None
    author_email: str = None
    license: str = None
    copyright: str = None

    @classmethod
    def from_dict(cls, dikt: typing.Mapping) -> 'About':
        dikt = dict(zip((x.strip('__') for x in dikt.keys()), dikt.values()))
        sig = inspect.signature(cls)
        return cls(**sig.bind(**{x: y for x, y in dikt.items() if x in sig.parameters}).arguments)

    @classmethod
    def from_path(cls, path: pathlib.Path) -> 'About':
        about = {}
        exec(path.resolve().read_text(), about)
        return cls.from_dict(about)


HOME = pathlib.Path(__file__).resolve().parent
LIB = HOME / 'que'
ABOUT = About.from_path(LIB / '__about__.py')
README = (HOME / 'README.md').read_text()


class UploadCommand(Command):
    """Support setup.py upload.

    Adapted from https://github.com/kennethreitz/setup.py/blob/master/setup.py
    """

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(HOME, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system(f'{sys.executable} setup.py sdist bdist_wheel --universal')

        self.status('Uploading the package to PyPI via Twine…')
        os.system('twine upload dist/*')

        self.status('Pushing git tags…')
        os.system(f'git tag v{ABOUT.version}')
        os.system('git push --tags')

        sys.exit()


setup(
    name=f"{ABOUT.title}-py",
    version=ABOUT.version,
    packages=[ABOUT.title],
    url=ABOUT.url,
    license=ABOUT.license,
    author=ABOUT.author,
    author_email=ABOUT.author_email,
    description=ABOUT.description,
    long_description=README,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: SQL',
        'Topic :: Database',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Utilities'
    ],
    python_requires='>=3.7',
    cmdclass={
        'upload': UploadCommand,
    },
)
