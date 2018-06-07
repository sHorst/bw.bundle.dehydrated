
domains = set(node.metadata.get('dehydrated', {}).get('domains', []))
challenge_type = node.metadata.get('dehydrated', {}).get('challenge_type', 'http-01')

available_hooks = [
    'deploy_challenge',
    'clean_challenge',
    'deploy_cert',
    'unchanged_cert',
    'invalid_challenge',
    'request_failure',
    'exit_hook',
]

hooks = {}
for hook_name in available_hooks:
    hooks[hook_name] = []

    for name, hook_hooks in sorted(
        node.metadata.get('dehydrated', {}).get('hooks', {}).get(hook_name, {}).items(),
        key=lambda x: x[0]
    ):
        hooks[hook_name] += hook_hooks

files = {
    '/etc/dehydrated/domains.txt': {
        'content': "\n".join(sorted(list(domains))) + "\n",
        'owner': 'root',
        'group': 'root',
        'mode': "0644",
        'triggers': {
            'action:generate_certificates',
        }
    },
    '/etc/dehydrated/config': {
        'source': 'etc/dehydrated/config',
        'content_type': 'jinja2',
        'owner': 'root',
        'group': 'root',
        'mode': "0644",
        'context': {
            'email': node.metadata.get('dehydrated', {}).get('email', 'stefan@ultrachaos.de'),
            'challenge_type': challenge_type,
        },
    },
    '/etc/dehydrated/hook.sh': {
        'source': 'etc/dehydrated/hook.sh',
        'content_type': 'jinja2',
        'owner': 'root',
        'group': 'root',
        'mode': "0755",
        'context': {
            'deploy_challenge': hooks['deploy_challenge'],
            'clean_challenge': hooks['clean_challenge'],
            'deploy_cert': hooks['deploy_cert'],
            'unchanged_cert': hooks['unchanged_cert'],
            'invalid_challenge': hooks['invalid_challenge'],
            'request_failure': hooks['request_failure'],
            'exit_hooks': hooks['exit_hook'],
        },
    },
    '/etc/cron.daily/dehydrated': {
        'source': 'etc/cron.daily/dehydrated',
        'content_type': 'text',
        'owner': 'root',
        'group': 'root',
        'mode': "0755",
    },
}

directories = {
    '/etc/dehydrated': {
        'mode': '755',
        'owner': 'root',
        'group': 'root',
    },
    '/opt/dehydrated': {
        'mode': '755',
        'owner': 'root',
        'group': 'root',
    }
}

# TODO: make both posible, some domains one way, and others the other
if challenge_type == 'http-01':
    directories['/var/www/dehydrated'] = {
        'mode': '755',
        'owner': 'root',
        'group': 'root',
    }

actions = {
    'accept_terms': {
        'command': '/opt/dehydrated/dehydrated --register --accept-terms',
        'unless': 'test -f "$(/opt/dehydrated/dehydrated -e | '
                  'grep \'ACCOUNT_KEY=\' | sed \'s/.*ACCOUNT_KEY="\(.*\)"/\\1/g\')"',
        'needs': [
            'directory:/opt/dehydrated',
            'git_deploy:/opt/dehydrated',
            'file:/etc/dehydrated/config'
        ],
    },
    'generate_certificates': {
        'command': '/opt/dehydrated/dehydrated -c',
        'triggered': True,
        'needs': [
            'git_deploy:/opt/dehydrated',
            'action:accept_terms'
        ],
    }
}

git_deploy = {
    '/opt/dehydrated': {
        'needs': ['directory:/opt/dehydrated'],
        'repo': 'ssh://github.com/lukas2511/dehydrated.git',
        'rev': 'master',
    }
}

