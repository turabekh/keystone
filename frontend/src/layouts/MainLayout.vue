<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>
          <router-link
            to="/"
            class="text-white"
            style="text-decoration: none"
          >
            Keystone
          </router-link>
        </q-toolbar-title>
        <div class="text-caption q-mr-md">PA Property Tax Appeals</div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>

    <q-footer class="bg-grey-2 text-grey-8">
      <q-toolbar>
        <q-toolbar-title class="text-caption text-center">
          Keystone — Built for Pennsylvania property tax appeals.
          Recommendations are advisory; consult a qualified professional before filing.
        </q-toolbar-title>
      </q-toolbar>
    </q-footer>
  </q-layout>
</template>

<script setup lang="ts">
// no script needed
</script>