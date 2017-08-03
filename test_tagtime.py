import util


class TestUtil:
    def test_clip(self):
        assert util.clip(3, 1, 5) == 3
        assert util.clip(1, 3, 5) == 3
        assert util.clip(7, 3, 5) == 5

    # def test_callcmd(self):
    #     pass

    def test_strip(self):
        strip = util.strip
        assert strip('yes (and) no') == 'yes  no'
        assert strip('yes (and)) no') == 'yes ) no'
        assert strip('yes ((and) no') == 'yes ( no'
        assert strip('(one plus one)') == ''
        assert strip('(five of (them)) yesterday') == ' yesterday'
        assert strip('something(somearg)') == 'something'
        assert strip('yes [and] no') == 'yes  no'
        assert strip('yes [and]] no') == 'yes ] no'
        assert strip('yes [[and] no') == 'yes [ no'
        assert strip('[one plus one]') == ''
        assert strip('[five of [them]] yesterday') == ' yesterday'
        assert strip('something[somearg]') == 'something'
        assert strip('web lrn (something new) [not today]') == 'web lrn  '
        assert strip('testing (nesting [brackets] are cool)') == 'testing '


    # Def test_stripb(self):
    #     pass

    # def test_stripc(self):
    #     pass

    # def test_parsable(self):
    #     pass

    # def test_fetchp(self):
    #     pass

    # def test_gettags(self):
    #     pass

    # def test_lockb(self):
    #     pass

    # def test_lockn(self):
    #     pass

    # def test_unlock(self):
    #     pass

    # def test_splur(self):
    #     pass

    # def test_divider(self):
    #     pass

    # def test_lrjust(self):
    #     pass

    # def test_annotime(self):
    #     pass

    # def test_dd(self):
    #     pass

    # def test_padl(self):
    #     pass

    # def test_isnum(self):
    #     pass

    # def test_pd(self):
    #     pass

    # def test_playsound(self):
    #     pass
