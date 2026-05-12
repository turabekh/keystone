<template>
  <q-page padding>
    <div class="row justify-center q-pa-md">
      <div class="col-12 col-md-8 col-lg-6">
        <div class="text-h3 text-center q-mb-sm">
          Should you appeal your property tax?
        </div>
        <div class="text-subtitle1 text-center text-grey-7 q-mb-xl">
          Search a Pennsylvania address. We'll analyze your assessment against
          comparable sales and neighborhood norms — and tell you if appealing is worth it.
        </div>

        <q-card flat bordered class="q-pa-md">
          <q-form @submit.prevent="onSearch">
            <q-select
              v-model="county"
              :options="countyOptions"
              label="County"
              outlined
              emit-value
              map-options
              class="q-mb-md"
              :disable="loadingCounties"
              :hint="loadingCounties ? 'Loading counties...' : undefined"
            />

            <q-input
              v-model="query"
              outlined
              label="Property address"
              placeholder="e.g. 1204 Master, 7000 Emlen, 106 Overhill"
              :error="hasError"
              :error-message="errorMessage"
              autofocus
              clearable
            >
              <template v-slot:append>
                <q-icon name="search" />
              </template>
            </q-input>

            <div class="q-mt-md">
              <q-btn
                type="submit"
                color="primary"
                size="lg"
                class="full-width"
                :loading="loading"
                :disable="!canSearch"
              >
                Find my property
              </q-btn>
            </div>
          </q-form>
        </q-card>

        <div class="text-center text-caption text-grey-6 q-mt-lg">
          <q-icon name="info" size="xs" class="q-mr-xs" />
          v1 covers Philadelphia properties only.
          Suburban counties (Bucks, Montgomery, Delaware, Chester) coming soon.
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { api } from 'src/boot/axios';
import type { County } from 'src/types/api';

const router = useRouter();

const query = ref('');
const county = ref('philadelphia');
const loading = ref(false);
const loadingCounties = ref(true);
const hasError = ref(false);
const errorMessage = ref('');

const counties = ref<County[]>([]);

const countyOptions = computed(() =>
  counties.value.map((c) => ({
    label: `${c.name} County, ${c.state}`,
    value: c.slug,
  })),
);

const canSearch = computed(() => query.value.trim().length >= 3 && !loading.value);

async function loadCounties() {
  try {
    const response = await api.get<County[]>('/api/v1/counties/', {
      params: { state: 'PA' },
    });
    counties.value = response.data;
  } catch (err) {
    console.error('Failed to load counties:', err);
  } finally {
    loadingCounties.value = false;
  }
}

function onSearch() {
  hasError.value = false;
  errorMessage.value = '';

  const trimmed = query.value.trim();
  if (trimmed.length < 3) {
    hasError.value = true;
    errorMessage.value = 'Please enter at least 3 characters';
    return;
  }

  void router.push({
    name: 'lookup',
    query: {
      q: trimmed,
      county: county.value,
      state: 'PA',
    },
  });
}

onMounted(() => {
  void loadCounties();
});
</script>