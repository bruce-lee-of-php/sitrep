FROM nginx:stable-alpine

# Remove the default configuration file to prevent any conflicts.
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom nginx.conf to the standard location for server configurations.
# This ensures it's loaded correctly by the main Nginx process.
COPY nginx.conf /etc/nginx/conf.d/default.conf

