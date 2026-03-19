import { createRouter, createWebHashHistory } from 'vue-router';
import MainRoutes from './MainRoutes';
import AuthRoutes from './AuthRoutes';
import ChatBoxRoutes from './ChatBoxRoutes';
import { useRouterLoadingStore } from '@/stores/routerLoading';
import {
  getShowcaseRouteFallback,
  isShowcaseRouteAllowed,
} from '@/showcase/presets';

export const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    MainRoutes,
    AuthRoutes,
    ChatBoxRoutes
  ]
});

router.beforeEach(async (to, from, next) => {
  if (from.name && from.path !== to.path) {
    const loadingStore = useRouterLoadingStore();
    loadingStore.start();
  }

  if (to.path.startsWith('/auth')) {
    return next(getShowcaseRouteFallback('/', ''));
  }

  if (!isShowcaseRouteAllowed(to.path, to.hash)) {
    return next(getShowcaseRouteFallback(to.path, to.hash));
  }

  next();
});

router.afterEach(() => {
  const loadingStore = useRouterLoadingStore();
  loadingStore.finish();
});
