try:
    from requests import Session, sessions
    from requests.adapters import HTTPAdapter

except ImportError:
    Session = None
    sessions = None
    HTTPAdapter = None