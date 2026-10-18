FROM nginx:alpine

COPY templates/ /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/

ENV ENROLMENT_SERVICE_URL=http://enrolment-service:5001

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80
