# Use a standard Node.js image for development
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package files and install dependencies
# This is done in a separate step to leverage Docker's layer caching
COPY package*.json ./
RUN npm install

# Copy the rest of the application source code
COPY . .

# Expose the port Vite uses
EXPOSE 5173

# The command to start the Vite development server
# 'npm run dev' is the standard for Vite projects
CMD ["npm", "run", "dev"]

