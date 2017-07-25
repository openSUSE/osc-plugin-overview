from oscpluginoverview import diff

def test_diff_strings():
    unified_diff = diff.diff_strings('one\ntwo\nthree', 'one\nthree')
    assert '-two\n three' in unified_diff

