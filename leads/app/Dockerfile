FROM php:8.3-apache
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && docker-php-ext-install pdo_pgsql && rm -rf /var/lib/apt/lists/*
RUN sed -ri 's!/var/www/html!/app/public!g' /etc/apache2/sites-available/*.conf \
 && printf '<Directory /app/public>\n  Options -Indexes\n  AllowOverride None\n  Require all granted\n</Directory>\nServerTokens Prod\n' > /etc/apache2/conf-enabled/weap.conf \
 && printf 'expose_php=Off\nvariables_order="EGPCS"\n' > /usr/local/etc/php/conf.d/weap.ini
COPY . /app
