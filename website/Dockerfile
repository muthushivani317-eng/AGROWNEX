FROM nginx:alpine

COPY *.html legal.css legal.js /usr/share/nginx/html/
COPY assets /usr/share/nginx/html/assets
COPY default.conf.template /etc/nginx/templates/default.conf.template

# Railway injects $PORT; the base image's entrypoint runs envsubst on
# everything under /etc/nginx/templates/ into /etc/nginx/conf.d/ at startup,
# substituting only names that are actual environment variables (so nginx's
# own $uri/$host variables in the template below are left untouched).
