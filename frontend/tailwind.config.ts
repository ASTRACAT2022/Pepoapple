import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101113",
        haze: "#f4f0e6",
        mango: "#f7b02b",
        mint: "#64d8b4",
        rust: "#e85b2b"
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'IBM Plex Sans'", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
