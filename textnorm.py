# Shared text normalisation for the Turkish search index (index build + query time must match).
import re

_TR = str.maketrans({'İ': 'i', 'I': 'i', 'ı': 'i'})
WORD = re.compile(r"[0-9A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛûÉéÀ-ÿ]+", re.U)


def norm(s: str) -> str:
    """Lower-case with Turkish dotted/dotless i folded to plain i (diacritics are removed by FTS5)."""
    return s.translate(_TR).lower()


_DIA = str.maketrans('çğöşüâîûéèàáíóú', 'cgosuaiueeaaiou')


def fold(s: str) -> str:
    """norm() plus diacritic removal, for Python-side term matching."""
    return norm(s).translate(_DIA)


def words(s: str):
    return WORD.findall(s)
