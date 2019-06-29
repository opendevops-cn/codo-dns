FROM opencodo/base

COPY doc/requirements.txt /tmp/requirements.txt

RUN pip3 install -r /tmp/requirements.txt

ADD . /var/www/codo-dns/

VOLUME /var/log/

COPY doc/nginx_ops.conf /etc/nginx/conf.d/default.conf
COPY doc/supervisor_ops.conf  /etc/supervisord.conf

CMD ["/usr/bin/supervisord"]