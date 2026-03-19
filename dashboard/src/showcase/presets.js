const SHOWCASE_VERSIONS = ["v1", "v2", "v3", "v4", "v5"];

const normalizeVersion = (value) => {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  return SHOWCASE_VERSIONS.includes(normalized) ? normalized : "v5";
};

const currentVersion = normalizeVersion(
  import.meta.env.VITE_PERSBOT_SHOWCASE_VERSION,
);

const SHOWCASE_PRESETS = {
  v1: {
    code: "v1",
    label: "Persbot",
    summary: "Personalized AI agent workspace.",
    highlights: [],
    features: {
      providers: true,
      config: true,
      platforms: false,
      knowledgeBase: false,
      persona: false,
      extensionInstalled: false,
      extensionMarket: false,
      extensionSkills: false,
      extensionComponents: false,
      extensionMcp: false,
      conversation: false,
      sessionManagement: false,
      cron: false,
      subagent: false,
      dashboard: false,
      console: false,
      trace: false,
    },
  },
  v2: {
    code: "v2",
    label: "Persbot",
    summary: "Personalized AI agent workspace.",
    highlights: [],
    features: {
      providers: true,
      config: true,
      platforms: true,
      knowledgeBase: true,
      persona: true,
      extensionInstalled: false,
      extensionMarket: false,
      extensionSkills: false,
      extensionComponents: false,
      extensionMcp: false,
      conversation: false,
      sessionManagement: false,
      cron: false,
      subagent: false,
      dashboard: false,
      console: false,
      trace: false,
    },
  },
  v3: {
    code: "v3",
    label: "Persbot",
    summary: "Personalized AI agent workspace.",
    highlights: [],
    features: {
      providers: true,
      config: true,
      platforms: true,
      knowledgeBase: true,
      persona: true,
      extensionInstalled: true,
      extensionMarket: true,
      extensionSkills: true,
      extensionComponents: false,
      extensionMcp: false,
      conversation: false,
      sessionManagement: false,
      cron: false,
      subagent: false,
      dashboard: false,
      console: false,
      trace: false,
    },
  },
  v4: {
    code: "v4",
    label: "Persbot",
    summary: "Personalized AI agent workspace.",
    highlights: [],
    features: {
      providers: true,
      config: true,
      platforms: true,
      knowledgeBase: true,
      persona: true,
      extensionInstalled: true,
      extensionMarket: true,
      extensionSkills: true,
      extensionComponents: false,
      extensionMcp: false,
      conversation: true,
      sessionManagement: true,
      cron: true,
      subagent: true,
      dashboard: true,
      console: false,
      trace: false,
    },
  },
  v5: {
    code: "v5",
    label: "Persbot",
    summary: "Personalized AI agent workspace.",
    highlights: [],
    features: {
      providers: true,
      config: true,
      platforms: true,
      knowledgeBase: true,
      persona: true,
      extensionInstalled: true,
      extensionMarket: true,
      extensionSkills: true,
      extensionComponents: true,
      extensionMcp: true,
      conversation: true,
      sessionManagement: true,
      cron: true,
      subagent: true,
      dashboard: true,
      console: true,
      trace: true,
    },
  },
};

const EXTENSION_TAB_FEATURES = {
  installed: "extensionInstalled",
  market: "extensionMarket",
  skills: "extensionSkills",
  components: "extensionComponents",
  mcp: "extensionMcp",
};

const ROUTE_FEATURE_MAP = {
  "/platforms": "platforms",
  "/providers": "providers",
  "/config": "config",
  "/extension": "extensionInstalled",
  "/extension-marketplace": "extensionMarket",
  "/knowledge-base": "knowledgeBase",
  "/persona": "persona",
  "/conversation": "conversation",
  "/session-management": "sessionManagement",
  "/cron": "cron",
  "/subagent": "subagent",
  "/dashboard/default": "dashboard",
  "/console": "console",
  "/trace": "trace",
};

const parseRouteTarget = (target = "") => {
  if (typeof target !== "string") {
    return { path: "", hash: "" };
  }

  const [path, rawHash] = target.split("#");
  return {
    path: path || "",
    hash: rawHash ? `#${rawHash}` : "",
  };
};

export const getShowcaseVersion = () => currentVersion;

export const getShowcasePreset = () => SHOWCASE_PRESETS[currentVersion];

export const getShowcaseFeatureMap = () => getShowcasePreset().features;

export const isShowcaseFeatureEnabled = (feature) =>
  Boolean(getShowcaseFeatureMap()[feature]);

export const getShowcaseAvailableExtensionTabs = () =>
  Object.entries(EXTENSION_TAB_FEATURES)
    .filter(([, feature]) => isShowcaseFeatureEnabled(feature))
    .map(([tab]) => tab);

export const getShowcaseDefaultExtensionTab = () =>
  getShowcaseAvailableExtensionTabs()[0] || null;

export const isShowcaseRouteAllowed = (path, hash = "") => {
  if (!path) {
    return true;
  }

  if (path === "/extension" || path === "/extension-marketplace") {
    const tabs = getShowcaseAvailableExtensionTabs();
    if (!tabs.length) {
      return false;
    }

    const requestedTab = String(hash || "").replace(/^#/, "");
    if (!requestedTab) {
      return true;
    }

    return tabs.includes(requestedTab);
  }

  const feature = ROUTE_FEATURE_MAP[path];
  if (!feature) {
    return true;
  }

  return isShowcaseFeatureEnabled(feature);
};

export const getShowcaseRouteFallback = (path, hash = "") => {
  if (path === "/extension" || path === "/extension-marketplace") {
    const defaultTab = getShowcaseDefaultExtensionTab();
    return defaultTab ? `/extension#${defaultTab}` : "/welcome";
  }

  if (path === "/extension-marketplace" && !hash) {
    const defaultTab = getShowcaseDefaultExtensionTab();
    return defaultTab ? `/extension#${defaultTab}` : "/welcome";
  }

  return "/welcome";
};

const filterSidebarItem = (item) => {
  const nextItem = { ...item };

  if (Array.isArray(nextItem.children) && nextItem.children.length > 0) {
    nextItem.children = nextItem.children
      .map((child) => filterSidebarItem(child))
      .filter(Boolean);

    if (nextItem.children.length === 0) {
      return null;
    }

    const { path, hash } = parseRouteTarget(nextItem.to);
    if (nextItem.to && !isShowcaseRouteAllowed(path, hash)) {
      nextItem.to = nextItem.children[0]?.to || "";
    }

    return nextItem;
  }

  const { path, hash } = parseRouteTarget(nextItem.to);
  if (nextItem.to && !isShowcaseRouteAllowed(path, hash)) {
    return null;
  }

  return nextItem;
};

export const filterShowcaseSidebarItems = (items = []) =>
  items.map((item) => filterSidebarItem(item)).filter(Boolean);
