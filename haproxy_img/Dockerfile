FROM haproxy:2.3

COPY errors /etc/haproxy/errors
COPY crt_key.pem /crt_key.pem

ENV TZ=Europe/Rome
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN mkdir /run/haproxy/

COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg", "-V"]
