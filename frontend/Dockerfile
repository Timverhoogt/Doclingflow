FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port (mapped to 2001 externally in docker-compose)
EXPOSE 3000

# Development command (for production, use: npm run build && npm start)
CMD ["npm", "run", "dev"]
