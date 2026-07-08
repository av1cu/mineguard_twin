/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    workerThreads: false,
    cpus: 1,
  },
  webpack: (config) => {
    config.externals = [...(config.externals || []), { canvas: "commonjs canvas" }];
    return config;
  },
};

export default nextConfig;
