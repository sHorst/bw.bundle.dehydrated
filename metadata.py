defaults = {
   'apt': {
       'packages': {
           'bsdextrautils': {'installed': True, },
       }
   }
}


@metadata_reactor
def convert_to_challenge_types(metadata):
    new_metadata = {
        'challenge_types': {},
    }

    old_challenge_type = metadata.get('dehydrated/challenge_type', 'http-01')
    if metadata.get('dehydrated/domains', None):
        new_metadata['challenge_types'][old_challenge_type] = {
            'domains': metadata.get('dehydrated/domains'),
        }

    if metadata.get('dehydrated/acme_pdns_api', None) is not None:
        new_metadata['challenge_types'].setdefault('dns-01', {})
        new_metadata['challenge_types']['dns-01']['acme_pdns_api'] = metadata.get('dehydrated/acme_pdns_api')

    return {
        'dehydrated': new_metadata
    }


@metadata_reactor
def add_apache_certs(metadata):
    if not node.has_bundle("apache"):
        raise DoNotRunAgain

    vhosts = {}
    for vhost_name in metadata.get('apache/vhosts', []):
        vhost = metadata.get('apache/vhosts/{}'.format(vhost_name))
        if not vhost.get('ssl', False):
            continue

        # if value is set, continue
        if vhost.get('ssl_key', False):
            continue

        vhosts[vhost_name] = {
            'ssl_crt': '/etc/dehydrated/certs/{}/fullchain.pem'.format(vhost_name),
            'ssl_key': '/etc/dehydrated/certs/{}/privkey.pem'.format(vhost_name),
        }

        # if we do dns, then skip the well-known
        if vhost.get('dehydrated_challenge_type', 'http-01') == 'dns-01':
            continue

        vhosts[vhost_name]['additional_config'] = {
            'dehydrated': [
                '# enable dehydrated',
                'Alias "/.well-known/acme-challenge" "/var/www/dehydrated"',
                '<Directory /var/www/dehydrated>',
                '   Options -Indexes +FollowSymLinks +MultiViews',
                '   AllowOverride None',
                '   Require all granted',
                '</Directory>'
            ]
        }

    return {
        'apache': {
            'vhosts': vhosts,
        }
    }


@metadata_reactor
def add_dns_hooks(metadata):
    # add dns hooks
    if metadata.get('dehydrated/challenge_types/dns-01/acme_pdns_api', None):
        node_name = 'test'
        acme_pdns_api_config = metadata.get('dehydrated/challenge_types/dns-01/acme_pdns_api', {})
        user = acme_pdns_api_config.get('user', node_name)
        password = acme_pdns_api_config.get('password',
                                            repo.vault.password_for(f"acme_pdns_fsn-01.leela.ns1_{node_name}"))
        server = acme_pdns_api_config.get('server', 'ns1.ultrachaos.de')
        port = acme_pdns_api_config.get('port', 18080)

        return {
            'dehydrated': {
                'challenge_types': {
                    'dns-01': {
                        'hooks': {
                            'deploy_challenge': {
                                'dns': [
                                    f'curl -isk "https://{user}:{password}@{server}:{port}?domain=$DOMAIN&token='
                                    '$TOKEN_VALUE&action=deploy"',
                                    '    sleep 15',
                                ],
                            },
                            'clean_challenge': {
                                'dns': [
                                    f'curl -isk "https://{user}:{password}@{server}:{port}?domain=$DOMAIN&'
                                    'token=$TOKEN_VALUE&action=clean"'
                                ],
                            },
                        }
                    }

                }
            }
        }

    return {}

