# Builder stage
FROM node:lts as builder
COPY package*.json ./

# Arguments to env variables
ARG NPM_TOKEN

# Set registry and authentication token
RUN npm config set @xxxxenterprises:registry https://npm.pkg.github.com/xxxxenterprises && \
    npm config set //npm.pkg.github.com/:_authToken $NPM_TOKEN

# Set custom npm cache directory and clean it
RUN npm install --legacy-peer-deps

# Copy source files and build
COPY . .
    
RUN npm run build


# Serve stage with Nginx
FROM nginx:alpine

# Remove the default Nginx index.html
RUN rm /usr/share/nginx/html/*

# Copy built files from builder stage
COPY --from=builder src/dist /usr/share/nginx/html

COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for HTTP traffic
EXPOSE 80
ENTRYPOINT ["nginx", "-g", "daemon off;"]

