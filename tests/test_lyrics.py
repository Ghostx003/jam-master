import pytest
from backend.romanizer import is_indic_text, romanize_indic
from backend.lyrics import get_lyrics

def test_indic_detection():
    hindi = "हम तेरे बिन अब रह नहीं सकते"
    punjabi = "ਤੂੰ ਮੇਰਾ ਦਿਲ, ਤੂੰ ਮੇਰੀ ਜਾਨ"
    english = "Drake - Portland feat. Quavo"
    assert is_indic_text(hindi) is True
    assert is_indic_text(punjabi) is True
    assert is_indic_text(english) is False

def test_hindi_romanization():
    hindi = "हम तेरे बिन अब रह नहीं सकते"
    roman = romanize_indic(hindi)
    assert "tere" in roman
    assert "bin" in roman

def test_punjabi_romanization():
    punjabi = "ਦਿਲ ਦੀਆਂ ਗੱਲਾਂ"
    roman = romanize_indic(punjabi)
    assert "dil" in roman

def test_get_lyrics_fallback():
    # Unknown track returns structured dictionary with found=False
    res = get_lyrics("FakeArtistUnknown12345", "NonExistentTrackSong98765")
    assert res["found"] is False
    assert "message" in res
