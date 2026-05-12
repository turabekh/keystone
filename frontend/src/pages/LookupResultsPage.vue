<template>
  <q-page padding>
    <div class="row justify-center">
      <div class="col-12 col-md-10 col-lg-8">
        <!-- Search header -->
        <div class="q-mb-md">
          <q-btn
            flat
            dense
            icon="arrow_back"
            label="New search"
            color="primary"
            to="/"
            class="q-mb-sm"
          />
          <div class="text-h5">
            <span v-if="!loading && results.length > 0">
              {{ results.length }} {{ results.length === 1 ? 'match' : 'matches' }} for
            </span>
            <span v-else-if="!loading">No matches for</span>
            <span v-else>Searching for</span>
            "<span class="text-primary">{{ query }}</span>"
            <span class="text-grey-7 text-body1">
              in {{ formatCountyName(county) }}
            </span>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="q-pa-xl text-center">
          <q-spinner-dots color="primary" size="3em" />
          <div class="text-grey-7 q-mt-sm">Looking up properties...</div>
        </div>

        <!-- Error state -->
        <q-banner v-else-if="error" class="bg-red-1 text-red-9 q-mb-md">
          <template v-slot:avatar>
            <q-icon name="error" color="red-9" />
          </template>
          {{ error }}
        </q-banner>

        <!-- No results -->
        <div v-else-if="results.length === 0" class="q-pa-xl text-center text-grey-7">
          <q-icon name="search_off" size="4em" class="text-grey-5" />
          <div class="text-h6 q-mt-md">No matches found</div>
          <div class="q-mt-sm">
            Try a different spelling, or search for just the street number and name.
          </div>
          <q-btn color="primary" outline class="q-mt-md" to="/">
            Try another search
          </q-btn>
        </div>

        <!-- Results list -->
        <q-list v-else bordered separator>
          <q-item
            v-for="prop in results"
            :key="prop.id"
            clickable
            v-ripple
            @click="selectProperty(prop.id)"
          >
            <q-item-section>
              <q-item-label class="text-weight-medium text-body1">
                {{ prop.address_full }}
              </q-item-label>
              <q-item-label caption class="q-mt-xs">
                <span class="text-grey-7">
                  {{ formatCategory(prop.property_category) }}
                </span>
                <span v-if="prop.zip_code" class="q-ml-md text-grey-7">
                  ZIP {{ prop.zip_code }}
                </span>
                <span v-if="prop.current_assessed_total" class="q-ml-md text-grey-7">
                  Assessed: ${{ formatNumber(prop.current_assessed_total) }}
                </span>
              </q-item-label>
            </q-item-section>

            <q-item-section side>
              <div class="text-caption text-grey-6">
                {{ Math.round(prop.similarity * 100) }}% match
              </div>
            </q-item-section>

            <q-item-section side>
              <q-icon name="chevron_right" color="grey-5" />
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="results.length > 0" class="q-mt-md text-caption text-grey-6 text-center">
          Click a property to see whether you should appeal.
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { propertiesService } from 'src/services/properties';
import type { PropertyLookupResult, PropertyCategory } from 'src/types/api';

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const error = ref<string | null>(null);
const results = ref<PropertyLookupResult[]>([]);

const query = computed(() => String(route.query.q ?? ''));
const county = computed(() => String(route.query.county ?? 'philadelphia'));
const state = computed(() => String(route.query.state ?? 'PA'));

const CATEGORY_LABELS: Record<PropertyCategory, string> = {
  rowhouse: 'Rowhouse',
  twin_semi: 'Twin / Semi-detached',
  single_family: 'Single-family',
  multi_family: 'Multi-family',
  condo: 'Condo',
  mixed_use: 'Mixed-use',
  commercial: 'Commercial',
  vacant: 'Vacant land',
  other: 'Other',
};

function formatCategory(cat: PropertyCategory): string {
  return CATEGORY_LABELS[cat] ?? cat;
}

function formatNumber(n: number): string {
  return n.toLocaleString('en-US');
}

function formatCountyName(slug: string): string {
  return slug.charAt(0).toUpperCase() + slug.slice(1);
}

function selectProperty(id: string) {
  void router.push({ name: 'property', params: { id } });
}

async function search() {
  loading.value = true;
  error.value = null;
  results.value = [];

  try {
    results.value = await propertiesService.lookup({
      q: query.value,
      state: state.value,
      county_slug: county.value,
      limit: 10,
    });
  } catch (err) {
    if (axios.isAxiosError(err)) {
      if (err.response?.status === 404) {
        error.value = `County not found: ${county.value}, ${state.value}.`;
      } else if (err.response?.status === 422) {
        error.value = 'Invalid search. Please enter at least 3 characters.';
      } else {
        error.value = 'Search failed. Please try again.';
        console.error(err);
      }
    } else {
      error.value = 'Search failed. Please try again.';
      console.error(err);
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (query.value.length >= 3) {
    void search();
  } else {
    error.value = 'Search query must be at least 3 characters.';
  }
});

// Re-search if URL query changes (e.g., user edits address bar)
watch([query, county, state], () => {
  if (query.value.length >= 3) {
    void search();
  }
});
</script>