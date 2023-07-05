"""Contains languages aggregator"""


from checker_languages.basic import CheckerLanguage
from checker_languages.cpp import CPP_LANGUAGE
from checker_languages.java import JAVA_LANGUAGE
from checker_languages.pascal import PASCAL_LANGUAGE
from checker_languages.pypy import PYPY_LANGUAGE
from checker_languages.python import PYTHON_LANGUAGE

LANGUAGES_MAPPING = {
    "python": PYTHON_LANGUAGE,
    "pypy": PYPY_LANGUAGE,
    "cpp": CPP_LANGUAGE,
    "java": JAVA_LANGUAGE,
    "pascal": PASCAL_LANGUAGE,
}


def get_language_class(language_short_name: str) -> CheckerLanguage:
    """Returns suitable language class

    Args:
        language_short_name (str)

    Returns:
        Language: language class instance
    """
    return LANGUAGES_MAPPING[language_short_name]
