from pathlib import Path

from aioworkers.core.config import \
    MergeDict, Config, IniLoader, StringReplaceLoader


def test_dict_create():
    d = MergeDict(f=3, d=dict(g=1))
    assert d.d.g == 1


def test_contains():
    d = MergeDict(f=3, d=dict(g=1))
    assert 'd.g' in d


def test_dict_dot_get_1():
    d = MergeDict(f=3, d=dict(g=1))
    assert d.get('f.d.e.d') is None


def test_dict_dot_get_2():
    d = MergeDict(f=3, d=dict(g=1))
    assert d.get('d.g') == 1


def test_dict_dot_get_3():
    d = MergeDict(f=3, d=dict(g=1))
    assert d['d.g'] == 1


def test_dict_replace1():
    d = MergeDict(f=3, d=dict(g=1))
    d['d.g.r!'] = 4
    assert d.d.g.r == 4, d


def test_dict_replace2():
    d = MergeDict(f=3, d=dict(g=1))
    d['d.g!'] = dict(r=4)
    assert d.d.g.r == 4, d


def test_dict_replace3():
    d = MergeDict(f=3, d=dict(g=1))
    d['d!'] = dict(r=4)
    assert d.d.r == 4, d


def test_dict_set1():
    d = MergeDict(f=3, d=dict(g=1))
    d['d.g'] = dict(r=4)
    assert d.d.g.r == 4, d


def test_dict_set2():
    d = MergeDict(f=3, d=dict(g=1))
    d['d'] = dict(r=4)
    assert d.d.r == 4, d
    assert d.d.g == 1, d


def test_dict_set3():
    d = MergeDict(f=3, d=dict(g=1))
    d.d = dict(r=4)
    assert d.d.r == 4, d
    assert d.d.g == 1, d


def test_dict_set4():
    d = MergeDict(f=3, d=dict(g=dict()))
    d['d.g'] = dict(r=4)
    assert d.d.g.r == 4, d


def test_merge():
    d = MergeDict(f=4)
    d(dict(g=3))
    assert d.g == 3, d
    assert d.f == 4, d
    d(dict(f=dict(g=2)), dict(f=4))
    assert d.g == 3, d
    assert d.f == 4, d


def test_load_config():
    p = Path(__file__).parent / 'data'
    conf = Config(search_dirs=[p])
    config = conf.load(p / 'conf1.json', 'conf2.json')
    assert config


def test_ini():
    loader = IniLoader()
    d = loader.load_str("""
        [sec]
        int1: 1
        int2 = 2
        int3:3
        int4=4
        int5=-4
        int6=+4
        float1:1.1
        float2:-1.1
        float3:+1.1
        list_multiline=
            1
            2
        list1: [1,2]
        list2:[1,2]
        list3=[1,2]
        list4 = [1,2]
        """)
    for k, v in d['sec'].items():
        if k.startswith('int'):
            assert isinstance(v, int)
        elif k.startswith('float'):
            assert isinstance(v, float)
        elif k.startswith('list'):
            assert isinstance(v, list)
            assert v == [1, 2]
        else:
            assert False


def test_string_replacer():
    c = StringReplaceLoader()
    conf = {'a': '1', 'b': ['2'], 'c': {'d': '3'}}
    c._replace(conf)
    assert conf == {'a': 1, 'b': [2], 'c': {'d': 3}}
