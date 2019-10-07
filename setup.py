import setuptools


setuptools.setup(
    name="dlt",
    description="Python DLT implementation for DLT",
    use_scm_version=True,
    url="https://github.com/bmwcarit/python-dlt",
    author="BMW Car IT",
    license="MPL 2.0",
    classifiers=[  # See:https://pypi.org/classifiers/
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Topic :: System :: Logging",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
    keywords="dlt log trace testing",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
    install_requires=[],
    zip_safe=False,
    test_suite="tests",
    entry_points={
        'console_scripts': [
            'py_dlt_receive = dlt.py_dlt_receive:main',
        ],
    },
)
