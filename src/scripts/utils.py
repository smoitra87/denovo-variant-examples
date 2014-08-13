import os

constants = {
    "DEFAULT_ZONE": 'us-central2-b',
    "API_VERSION": 'v1',
    "PROJECT_ID": 'de-novo-experiment',
    "GCE_USER": 'smoitra',
    "CLIENT_SECRETS": os.path.expanduser('~/Downloads/client_secrets.json'),
    "GCE_PRIVATE_KEY": os.path.expanduser('~/.ssh/google_compute_engine'),
    "OAUTH2_STORAGE": os.path.expanduser(
        '~/.store/genomics_denovo_caller/oauth2.dat'),
    "GCE_SCOPE": 'https://www.googleapis.com/auth/compute',
    "SNAPSHOT_NAME": "denovo-snapshot"
}
constants["GCE_URL"] = 'https://www.googleapis.com/compute/{API_VERSION}/projects/'.format(**constants)

def confirm(prompt="Are you sure?"):
    """prompts for yes or no """

    prompt = "{} (y|n): ".format(prompt)

    while True:
        ans = raw_input(prompt)
        if not ans:
            print prompt
            continue
        if ans in 'yY':
            return True
        if ans in 'nN':
            return False
        else:
            print prompt
            continue

def print_iterable(iterable):
    for e in iterable:
        print e
