import os

from setuptools import setup


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='vralib',
    packages=['vralib'],
    version='0.1',
    description='This is a helper library used to manage vRealize Automation via python.',
    author='Russell Pope',
    author_email='vralib@kovarus.com',
    url='https://github.com/kovarus/vrealize-pysdk',
    keywords=['vralib'],
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    license='Apache License, Version 2.0',
    install_requires=[
        'requests',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
