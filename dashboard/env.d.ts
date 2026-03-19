/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PERSBOT_RELEASE_BASE_URL?: string;
  readonly VITE_PERSBOT_SHOWCASE_VERSION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
