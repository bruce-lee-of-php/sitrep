# Use a lightweight Nginx image to serve the static HTML file
FROM nginx:alpine

# Remove the default Nginx welcome page
RUN rm /usr/share/nginx/html/index.html

# Copy our single-file application into the Nginx html directory
COPY index.html /usr/share/nginx/html/index.html

