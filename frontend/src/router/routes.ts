import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('pages/HomePage.vue') },
      {
        path: 'lookup',
        name: 'lookup',
        component: () => import('pages/LookupResultsPage.vue'),
      },
      {
        path: 'property/:id',
        name: 'property',
        component: () => import('pages/PropertyDetailPage.vue'),
        props: true,
      },
    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;