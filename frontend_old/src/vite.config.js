import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // This is needed for file changes to be detected within Docker
    watch: {
      usePolling: true,
    },
    // Config for the Hot Module Replacement (HMR) client
    hmr: {
      host: 'localhost', // The host the browser connects to
      protocol: 'ws',
      port: 8085,      // The public port exposed by Nginx
    },
  },
})
