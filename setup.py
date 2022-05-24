import setuptools
import os
from pathlib import Path

root = Path(os.path.realpath(__file__)).parent
version_file = root / "src" / "sphinx_codeautolink" / "VERSION"
readme_file = root / "readme_pypi.rst"

setuptools.setup(
    name="sphinx-codeautolink",
    version=version_file.read_text().strip(),
    license="MIT",
    description="Automatic links from code examples to reference documentation.",
    keywords="sphinx extension code link",
    long_description=readme_file.read_text(),
    long_description_content_type="text/x-rst",

    url="https://pypi.org/project/sphinx-codeautolink",
    download_url="https://pypi.org/project/sphinx-codeautolink",
    project_urls={
        "Source": "https://github.com/felix-hilden/sphinx-codeautolink",
        "Issues": "https://github.com/felix-hilden/sphinx-codeautolink/issues",
        "Documentation": "https://sphinx-codeautolink.rtfd.org",
    },

    author="Felix Hildén",
    author_email="felix.hilden@gmail.com",
    maintainer="Felix Hildén",
    maintainer_email="felix.hilden@gmail.com",

    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,

    python_requires=">=3.6",
    install_requires=[
        'sphinx>=3.2.0',
        'beautifulsoup4',
        'dataclasses;python_version<"3.7"',
    ],
    # Keep extras in sync with requirements manually
    extras_require={
        "ipython": ["ipython"],
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Sphinx',
        'Framework :: Sphinx :: Extension',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Documentation',
        'Topic :: Documentation :: Sphinx',
        'Topic :: Software Development :: Documentation',
    ],
)
