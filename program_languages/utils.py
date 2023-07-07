"""Contains languages aggregator"""


from program_languages.basic import ProgramLanguage
from program_languages.cpp import CPP_LANGUAGE
from program_languages.csharp import CSHARP_LANGUAGE
from program_languages.java import JAVA_LANGUAGE
from program_languages.pascal import PASCAL_LANGUAGE
from program_languages.pypy import PYPY_LANGUAGE
from program_languages.python import PYTHON_LANGUAGE
from program_languages.rust import RUST_LANGUAGE

LANGUAGES_MAPPING = {
    "python": PYTHON_LANGUAGE,
    "pypy": PYPY_LANGUAGE,
    "cpp": CPP_LANGUAGE,
    "csharp": CSHARP_LANGUAGE,
    "java": JAVA_LANGUAGE,
    "pascal": PASCAL_LANGUAGE,
    "rust": RUST_LANGUAGE,
}


def get_language_class(language_short_name: str) -> ProgramLanguage:
    """Returns suitable language class

    Args:
        language_short_name (str)

    Returns:
        Language: language class instance
    """
    return LANGUAGES_MAPPING[language_short_name]
