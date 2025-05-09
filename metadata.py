
defaults = {
   'apt': {
       'packages': {
           'bsdextrautils': {'installed': True, },
       }
   }
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
            'additional_config': {
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
        }

    return {
        'apache': {
            'vhosts': vhosts,
        }
    }


@metadata_reactor
def add_dns_hooks(metadata):
    # add dns hooks
    if metadata.get('dehydrated/challenge_type', 'http-01') == 'dns-01':
        node_name = 'test'
        acme_pdns_api_config = metadata.get('dehydrated/acme_pdns_api', {})
        user = acme_pdns_api_config.get('user', node_name)
        password = acme_pdns_api_config.get('password', repo.vault.password_for("acme_pdns_fsn-01.leela.ns1_{}".format(
            node_name
        )))
        server = acme_pdns_api_config.get('server', 'ns1.ultrachaos.de')
        port = acme_pdns_api_config.get('port', 18080)

        return {
            'dehydrated': {
                'hooks': {
                    'deploy_challenge': {
                        'dns': [
                            'curl -isk "https://{user}:{password}@{server}:{port}?domain=$DOMAIN&token=$TOKEN_VALUE&'
                            'action=deploy"'.format(
                                user=user,
                                password=password,
                                server=server,
                                port=port,
                            ),
                            'sleep 15',
                        ],
                    },
                    'clean_challenge': {
                        'dns': [
                            'curl -isk "https://{user}:{password}@{server}:{port}?domain=$DOMAIN&token=$TOKEN_VALUE&'
                            'action=clean"'.format(
                                user=user,
                                password=password,
                                server=server,
                                port=port,
                            )
                        ],
                    },

                }
            }
        }

    return {}

