# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "ClinicaIO"
copyright = "2026, ARAMIS Lab"
author = "ARAMIS Lab"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "myst_nb",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
autodoc_typehints = "both"

# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
napoleon_numpy_docstring = True
napoleon_custom_sections = [("Returns", "params_style"), ("Attributes", "params_style")]

# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
}

# -- autoapi configuration ---------------------------------------------------
# https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html

autoapi_dirs = ["../src"]
autoapi_root = "reference/api"
autoapi_options = [
    "members",
    "undoc-members",
    # Do not document private functions marked with single underscore _ prefix
    #'private-members',
    "show-inheritance",
    "show-module-summary",
    "special-members",
    # Otherwise we get duplicated documentation between the package documentation ("clinicaio") and
    # the module-level documentation (e.g. clinicaio.image). Also it creates warnings about
    # multiple available target reference for e.g. "Image".
    # "imported-members",
]
autoapi_python_class_content = "both"
autoapi_own_page_level = "method"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_theme_options = {
    "path_to_docs": "docs",
    "repository_url": "https://github.com/aramis-lab/clinicaio",
    "repository_branch": "main",
    "navigation_with_keys": False,
}
html_title = "ClinicaIO documentation"
html_static_path = ["_static"]
