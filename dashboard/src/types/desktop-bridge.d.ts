export {};

declare global {
  interface PersbotDesktopAppUpdateCheckResult {
    ok: boolean;
    reason?: string | null;
    currentVersion?: string;
    latestVersion?: string | null;
    hasUpdate: boolean;
  }

  interface PersbotDesktopAppUpdateResult {
    ok: boolean;
    reason?: string | null;
  }

  interface PersbotAppUpdaterBridge {
    checkForAppUpdate: () => Promise<PersbotDesktopAppUpdateCheckResult>;
    installAppUpdate: () => Promise<PersbotDesktopAppUpdateResult>;
  }

  interface Window {
    persbotAppUpdater?: PersbotAppUpdaterBridge;
    persbotDesktop?: {
      isDesktop: boolean;
      isDesktopRuntime: () => Promise<boolean>;
      getBackendState: () => Promise<{
        running: boolean;
        spawning: boolean;
        restarting: boolean;
        canManage: boolean;
      }>;
      restartBackend: (authToken?: string | null) => Promise<{
        ok: boolean;
        reason: string | null;
      }>;
      stopBackend: () => Promise<{
        ok: boolean;
        reason: string | null;
      }>;
      onTrayRestartBackend?: (callback: () => void) => () => void;
    };
  }
}
