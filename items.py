from copy import copy

available_hooks = [
    'deploy_challenge',
    'clean_challenge',
    'deploy_cert',
    'unchanged_cert',
    'invalid_challenge',
    'request_failure',
    'exit_hook',
]

files = {
    '/etc/cron.daily/dehydrated': {
        'source': 'etc/cron.daily/dehydrated',
        'context': {
            'challenge_types': sorted(list(node.metadata.get('dehydrated/challenge_types', {}).keys()))
        },
        'content_type': 'jinja2',
        'owner': 'root',
        'group': 'root',
        'mode': "0755",
    },
}

actions = {}

default_hooks = {}
for hook_name in available_hooks:
    default_hooks[hook_name] = []

    for name, hook_hooks in sorted(
            node.metadata.get('dehydrated', {}).get('hooks', {}).get(hook_name, {}).items(),
            key=lambda x: x[0]
    ):
        default_hooks[hook_name] += hook_hooks

for challenge_type, config in node.metadata.get('dehydrated/challenge_types', {}).items():
    domains = set(config.get('domains', []))

    hooks = {}
    for hook_name in available_hooks:
        hooks[hook_name] = copy(default_hooks[hook_name])

        for name, hook_hooks in sorted(config.get('hooks', {}).get(hook_name, {}).items(), key=lambda x: x[0]):
            hooks[hook_name] += hook_hooks

    files[f'/etc/dehydrated/domains_{challenge_type}.txt'] = {
        'content': "\n".join(sorted(list(domains))) + "\n",
        'owner': 'root',
        'group': 'root',
        'mode': "0644",
        'triggers': {
            f'action:generate_certificates_{challenge_type}',
        }
    }

    files[f'/etc/dehydrated/config_{challenge_type}'] = {
        'source': 'etc/dehydrated/config',
        'content_type': 'jinja2',
        'owner': 'root',
        'group': 'root',
        'mode': "0644",
        'context': {
            'email': node.metadata.get('dehydrated', {}).get('email', 'stefan@ultrachaos.de'),
            'challenge_type': challenge_type,
        },
    }
    files[f'/etc/dehydrated/hook_{challenge_type}.sh'] = {
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
    }

    actions[f'generate_certificates_{challenge_type}'] = {
        'command': f'/opt/dehydrated/dehydrated -f /etc/dehydrated/config_{challenge_type} -c',
        'triggered': True,
        'needs': [
            'git_deploy:/opt/dehydrated',
            'action:accept_terms',
            'pkg_apt:bsdextrautils',
        ],
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

if 'http-01' in node.metadata.get('dehydrated/challenge_types', {}):
    directories['/var/www/dehydrated'] = {
        'mode': '755',
        'owner': 'root',
        'group': 'root',
    }

# will break, if we do not have any challenge_types, which means we cannot register
challenge_type = list(node.metadata.get('dehydrated/challenge_types', {}).keys())[0]
actions['accept_terms'] = {
    'command': f'/opt/dehydrated/dehydrated -f /etc/dehydrated/config_{challenge_type} --register --accept-terms',
    'unless': 'test -f "$(/opt/dehydrated/dehydrated -e | '
              'grep \'ACCOUNT_KEY=\' | sed \'s/.*ACCOUNT_KEY="\\(.*\\)"/\\1/g\')"',
    'needs': [
        'directory:/opt/dehydrated',
        'git_deploy:/opt/dehydrated',
        f'file:/etc/dehydrated/config_{challenge_type}',
        'pkg_apt:bsdextrautils',
    ],
}

git_deploy = {
    '/opt/dehydrated': {
        'repo': 'ssh://github.com/lukas2511/dehydrated.git',
        'rev': 'master',
    }
}

