from aioworkers.net.uri import URI


def test_uri_parse():
    uri = URI('http://user:pass@localhost:90/abcde')
    assert uri.username == 'user'
    assert uri.password == 'pass'
    assert uri.hostname == 'localhost'
    assert uri.port == 90
    assert uri.path == '/abcde'


def test_netloc():
    uri = URI('http://user:pass@localhost/a')
    assert uri.with_auth('') == URI('http://localhost/a')
    assert uri.with_auth('', password='123') == URI('http://:123@localhost/a')
    assert uri.with_auth('user') == URI('http://user@localhost/a')
    assert uri.with_host("") == URI("http://user:pass@/a")


def test_uri_parse_bytes():
    uri = URI.from_bytes(b'http://user:pass@localhost:90/abcde?z=9')
    assert uri.scheme == 'http'
    assert uri.username == 'user'
    assert uri.password == 'pass'
    assert uri.hostname == 'localhost'
    assert uri.port == 90
    assert uri.path == '/abcde'
    assert uri.query_string == 'z=9'
    assert repr(uri) == "URI('http://user:pass@localhost:90/abcde?z=9')"


def test_with_scheme():
    uri = URI('http://h')
    assert uri.with_scheme('https') == URI('https://h')


def test_with_user():
    uri = URI('http://user:pass@localhost:90/abcde')
    uri = uri.with_username('anon')
    assert uri.username == 'anon'


def test_with_password():
    uri = URI('http://user:pass@h')
    assert uri.with_password('p') == URI('http://user:p@h')


def test_with_hostname():
    uri = URI('http://user:pass@localhost:90/a?b=9')
    assert uri.with_host('l:99') == URI('http://user:pass@l:99/a?b=9')


def test_with_hostname_port():
    uri = URI('http://user:pass@localhost:90/a?b=9')
    assert uri.with_host('l') == URI('http://user:pass@l:90/a?b=9')


def test_with_port():
    uri = URI('http://user:pass@l:90/a?b=9')
    assert uri.with_port(99) == URI('http://user:pass@l:99/a?b=9')


def test_with_path_rel():
    uri = URI('http://user:pass@localhost:90/abcde')
    uri = uri.with_path('fgh')
    assert uri.path == '/fgh'
    uri = URI('http://user:pass@localhost:90/abcde/')
    uri = uri.with_path('fgh')
    assert uri.path == '/abcde/fgh'


def test_with_path_abs():
    uri = URI('http://user:pass@localhost:90/abcde/3456789?a=9')
    assert uri.with_path('/fgh') == URI('http://user:pass@localhost:90/fgh')


def test_query():
    uri = URI('/a?b=9&b=8&c=7&z=1&y=0')
    assert uri.query.get('c') == '7'
    assert uri.query.get_int('c') == 7
    assert uri.query.get_bool('z') is True
    assert uri.query.get_bool('y') is False
    assert uri.query.get_list('b') == ['9', '8']
    assert uri.query.get_list('d') == []
    assert uri.query.get('x') is None
    assert uri.query.get_bool('b') is None
    assert set(uri.query.keys()) == {'b', 'c', 'z', 'y'}
    assert len(uri.query) == 4


def test_with_query():
    uri = URI('/a?b=9&b=8&c=7&z=1&y=0')
    assert uri.with_query(b='3').query_string == 'b=3'
    assert uri.with_query(x=3.14).query_string == 'x=3.14'
    assert uri.with_query('x').query_string == 'x'
    assert uri.with_query('x').query.get('x') is None
    assert uri.with_query().query_string is None


def test_update_query():
    uri = URI('/a?b=9&b=8&c=7&c=u&z=1&y=0')
    uwq = uri.update_query(b=3)
    assert uwq.query.get_list('b') == ['3']
    assert uwq.query.get_int('c') == 7
    assert uwq.query.get_int('x') is None
    assert uwq.query.get_float('c') == 7
    assert uwq.query.get_float('x') is None
    assert uwq.query.get_bool('z') is True
    assert uwq.query.get_bool('y') is False
