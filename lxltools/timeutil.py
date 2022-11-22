from datetime import datetime, timezone


def nowstamp():
    return datetime.now().timestamp()


def w3c_dtz_to_ms(ztime: str):
    assert ztime.endswith('Z')
    try:  # fromisoformat is new in Python 3.7
        return int(datetime.fromisoformat(ztime.replace('Z', '+00:00'))
                   .timestamp() * 1000)
    except AttributeError:  # fallback can be removed when we rely on Py 3.7+
        ztime = ztime[:-1]  # drop 'Z'
        if '.' not in ztime:
            ztime += '.000'  # add millisecs to comply with format
        ztime += '+0000'  # strptime-compliant UTC timezone format
        return int(datetime.strptime(ztime, '%Y-%m-%dT%H:%M:%S.%f%z')
                   .timestamp() * 1000)


def to_w3c_dtz(ms: float):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def to_http_date(s: float):
    return datetime.utcfromtimestamp(s).strftime('%a, %d %b %Y %H:%M:%S GMT')
