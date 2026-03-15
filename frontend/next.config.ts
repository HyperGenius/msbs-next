import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async redirects() {
    return [
      // ハイフンなし /signup を正式な /sign-up にリダイレクト
      {
        source: "/signup",
        destination: "/sign-up",
        permanent: false,
      },
      {
        source: "/signup/:path*",
        destination: "/sign-up/:path*",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
