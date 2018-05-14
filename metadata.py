@metadata_processor
def add_apache_certs(metadata):
    if 'apache' in metadata:
        for vhost_name in metadata['apache'].get('vhosts', []):
            vhost = metadata['apache']['vhosts'][vhost_name]
            if not vhost.get('ssl', False):
                continue

            # if value is set, continue
            if vhost.get('ssl_key', False):
                continue

            metadata['apache']['vhosts'][vhost_name]['ssl_crt'] = \
                '/etc/dehydrated/certs/{}/fullchain.pem'.format(vhost_name)
            metadata['apache']['vhosts'][vhost_name]['ssl_key'] = \
                '/etc/dehydrated/certs/{}/privkey.pem'.format(vhost_name)

            metadata['apache']['vhosts'][vhost_name].setdefault('additional_config', {})

            metadata['apache']['vhosts'][vhost_name]['additional_config']['dehydrated'] = [
                '# enable dehydrated',
                'Alias "/.well-known/acme-challenge" "/var/www/dehydrated"',
                '<Directory /var/www/dehydrated>',
                '   Options -Indexes +FollowSymLinks +MultiViews',
                '   AllowOverride None',
                '   Require all granted',
                '</Directory>'
            ]

        return metadata, DONE

    return metadata, RUN_ME_AGAIN


@metadata_processor
def add_dns_hooks(metadata):
    # add dns hooks
    if metadata.get('dehydrated', {}).get('challenge_type', 'http-01') == 'dns-01':
        node_name = 'test'
        acme_pdns_api_config = metadata.get('dehydrated', {}).get('acme_pdns_api', {})
        user = acme_pdns_api_config.get('user', node_name)
        password = acme_pdns_api_config.get('password', repo.libs.pw.get("acme_pdns_fsn-01.leela.ns1_{}".format(
            node_name
        )))
        server = acme_pdns_api_config.get('server', 'ns1.ultrachaos.de')
        port = acme_pdns_api_config.get('port', 18080)

        metadata['dehydrated'].setdefault('hooks', {}).setdefault('deploy_challenge', {})
        metadata['dehydrated'].setdefault('hooks', {}).setdefault('clean_challenge', {})

        metadata['dehydrated']['hooks']['deploy_challenge']['dns'] = [
            'curl -i -k "https://{user}:{password}@{server}:{port}?domain=$DOMAIN&token=$TOKEN_VALUE&'
            'action=deploy"'.format(
                user=user,
                password=password,
                server=server,
                port=port,
            ),
            'sleep 5',
        ]

        metadata['dehydrated']['hooks']['clean_challenge']['dns'] = [
            'curl -i -k "https://{user}:{password}@{server}:{port}?domain=$DOMAIN&token=$TOKEN_VALUE&'
            'action=clean"'.format(
                user=user,
                password=password,
                server=server,
                port=port,
            )
        ]

    return metadata, DONE
