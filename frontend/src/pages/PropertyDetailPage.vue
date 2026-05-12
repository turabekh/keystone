<template>
  <q-page padding>
    <div class="row justify-center">
      <div class="col-12 col-md-10 col-lg-9 col-xl-7">
        <!-- Breadcrumb / back -->
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
        </div>

        <!-- Loading detail state -->
        <div v-if="detailLoading" class="q-pa-xl text-center">
          <q-spinner-dots color="primary" size="3em" />
          <div class="text-grey-7 q-mt-sm">Loading property...</div>
        </div>

        <!-- Detail error -->
        <q-banner v-else-if="detailError" class="bg-red-1 text-red-9">
          <template v-slot:avatar>
            <q-icon name="error" color="red-9" />
          </template>
          {{ detailError }}
        </q-banner>

        <!-- Main content -->
        <template v-else-if="detail">
          <!-- Address header -->
          <div class="q-mb-lg">
            <div class="text-h4 text-weight-medium">{{ detail.address_full }}</div>
            <div class="text-subtitle1 text-grey-7 q-mt-xs">
              {{ formatCategory(detail.property_category) }}
              <span v-if="detail.zip_code"> · ZIP {{ detail.zip_code }}</span>
              <span v-if="detail.year_built"> · Built {{ detail.year_built }}</span>
              <span v-if="detail.square_feet_living">
                · {{ formatNumber(detail.square_feet_living) }} sqft
              </span>
            </div>
          </div>

          <!-- Hero: recommendation -->
          <q-card
            v-if="recommendation"
            flat
            bordered
            class="q-mb-lg"
            :class="recommendationBgClass"
          >
            <q-card-section>
              <div class="row items-center q-gutter-md">
                <q-icon :name="recommendationIcon" size="3em" :color="recommendationColor" />
                <div class="col">
                  <div class="text-overline text-grey-7">Our recommendation</div>
                  <div class="text-h4 text-weight-bold" :class="`text-${recommendationColor}`">
                    {{ recommendationLabel }}
                  </div>
                  <div v-if="recommendation.annual_tax_savings && recommendation.annual_tax_savings > 0" class="text-subtitle1 q-mt-xs">
                    Potential annual savings:
                    <strong>${{ formatNumber(recommendation.annual_tax_savings) }}</strong>
                    <span class="text-grey-7">
                      · ${{ formatNumber(recommendation.three_year_savings ?? 0) }} over 3 years
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="recommendation.primary_argument !== 'none'" class="q-mt-md">
                <q-chip
                  :color="argumentChipColor"
                  text-color="white"
                  :icon="argumentIcon"
                  size="md"
                >
                  Primary argument: {{ argumentLabel }}
                </q-chip>
                <q-chip
                  v-if="recommendation.counter_appeal_risk !== 'low'"
                  :color="riskChipColor"
                  text-color="white"
                  icon="warning"
                  size="md"
                >
                  {{ recommendation.counter_appeal_risk.toUpperCase() }} counter-appeal risk
                </q-chip>
              </div>
            </q-card-section>
          </q-card>

          <q-card v-else-if="recommendationLoading" flat bordered class="q-mb-lg q-pa-lg">
            <q-skeleton type="text" class="text-h4 q-mb-md" />
            <q-skeleton type="text" width="60%" />
            <q-skeleton type="text" width="40%" />
          </q-card>

          <!-- Why this recommendation: 3-card grid -->
          <div class="text-h6 q-mb-md">Why this recommendation</div>

          <div class="row q-col-gutter-md q-mb-lg">
            <!-- Assessment summary -->
            <div class="col-12 col-md-4">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="text-overline text-grey-7">Current assessment</div>
                  <div class="text-h5 q-mt-sm">
                    ${{ formatNumber(detail.current_assessed_total ?? 0) }}
                  </div>
                  <div class="text-caption text-grey-7 q-mt-sm">
                    Tax year {{ detail.current_assessment_year ?? '—' }}
                  </div>
                  <q-separator class="q-my-sm" />
                  <div v-if="recommendation?.appeal_target_assessment" class="text-caption">
                    <div class="text-grey-7">Appeal target</div>
                    <div class="text-body1 text-weight-medium">
                      ${{ formatNumber(recommendation.appeal_target_assessment) }}
                    </div>
                  </div>
                </q-card-section>
              </q-card>
            </div>

            <!-- Market value -->
            <div class="col-12 col-md-4">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="text-overline text-grey-7">Market value estimate</div>
                  <div v-if="valuationLoading">
                    <q-skeleton type="text" class="text-h5" />
                    <q-skeleton type="text" width="60%" />
                  </div>
                  <template v-else-if="valuation?.point_estimate">
                    <div class="text-h5 q-mt-sm">
                      ${{ formatNumber(valuation.point_estimate) }}
                    </div>
                    <div class="text-caption text-grey-7 q-mt-sm">
                      Range: ${{ formatNumber(valuation.low_estimate ?? 0) }} —
                      ${{ formatNumber(valuation.high_estimate ?? 0) }}
                    </div>
                    <q-separator class="q-my-sm" />
                    <q-chip
                      :color="confidenceChipColor(valuation.confidence)"
                      text-color="white"
                      size="sm"
                      dense
                    >
                      {{ valuation.confidence }} confidence · {{ valuation.comp_count }} comps
                    </q-chip>
                  </template>
                  <div v-else class="text-grey-7 q-mt-sm">
                    Insufficient data for market estimate
                  </div>
                </q-card-section>
              </q-card>
            </div>

            <!-- Uniformity -->
            <div class="col-12 col-md-4">
              <q-card flat bordered class="full-height">
                <q-card-section>
                  <div class="text-overline text-grey-7">Uniformity vs neighbors</div>
                  <div v-if="uniformityLoading">
                    <q-skeleton type="text" class="text-h5" />
                    <q-skeleton type="text" width="60%" />
                  </div>
                  <template v-else-if="uniformity?.deviation_from_neighborhood !== null && uniformity?.deviation_from_neighborhood !== undefined">
                    <div class="text-h5 q-mt-sm" :class="uniformityColor">
                      {{ formatPercent(uniformity.deviation_from_neighborhood) }}
                    </div>
                    <div class="text-caption text-grey-7 q-mt-sm">
                      vs. {{ uniformity.neighborhood_sample_size }} recent
                      neighborhood sales
                    </div>
                    <q-separator class="q-my-sm" />
                    <q-chip
                      :color="signalChipColor(uniformity.signal)"
                      text-color="white"
                      size="sm"
                      dense
                    >
                      {{ formatSignal(uniformity.signal) }}
                    </q-chip>
                  </template>
                  <div v-else class="text-grey-7 q-mt-sm">
                    Insufficient data for uniformity analysis
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- Reasoning -->
          <q-card v-if="recommendation?.reasoning?.length" flat bordered class="q-mb-lg">
            <q-card-section>
              <div class="text-h6 q-mb-md">Detailed reasoning</div>
              <ol class="reasoning-list">
                <li v-for="(line, idx) in recommendation.reasoning" :key="idx">
                  {{ line }}
                </li>
              </ol>
            </q-card-section>
          </q-card>

          <!-- Evidence: comps used -->
          <q-card v-if="valuation?.comps?.length" flat bordered class="q-mb-lg">
            <q-card-section>
              <div class="text-h6 q-mb-md">
                Comparable sales used ({{ valuation.comps.length }})
              </div>
              <q-table
                :rows="valuation.comps"
                :columns="compColumns"
                row-key="property_id"
                flat
                dense
                :pagination="{ rowsPerPage: 0 }"
                hide-bottom
              />
              <div v-if="valuation.notes?.length" class="q-mt-md text-caption text-grey-7">
                <q-icon name="info" size="xs" class="q-mr-xs" />
                {{ valuation.notes.join(' ') }}
              </div>
            </q-card-section>
          </q-card>

          <!-- Evidence: block uniformity -->
          <q-card v-if="uniformity?.block_result" flat bordered class="q-mb-lg">
            <q-card-section>
              <div class="text-h6 q-mb-md">
                Same-block uniformity analysis ({{ uniformity.block_result.sample_size }} sales)
              </div>
              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-4">
                  <div class="text-overline text-grey-7">Block median ASR</div>
                  <div class="text-h5">{{ uniformity.block_result.median_asr.toFixed(2) }}</div>
                </div>
                <div class="col-12 col-md-4">
                  <div class="text-overline text-grey-7">Subject ASR</div>
                  <div class="text-h5">{{ uniformity.subject_asr?.toFixed(2) ?? '—' }}</div>
                </div>
                <div class="col-12 col-md-4">
                  <div class="text-overline text-grey-7">Deviation from block</div>
                  <div class="text-h5" :class="blockDeviationColor">
                    {{ uniformity.deviation_from_block !== null && uniformity.deviation_from_block !== undefined ? formatPercent(uniformity.deviation_from_block) : '—' }}
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Disclaimer -->
          <q-banner dense class="bg-grey-2 text-grey-7 q-mt-xl">
            <template v-slot:avatar>
              <q-icon name="info" />
            </template>
            <span class="text-caption">
              This analysis is advisory and based on public records. Property tax appeals
              require careful evidence preparation and adherence to county deadlines.
              Consult a qualified property tax attorney or consultant before filing.
            </span>
          </q-banner>
        </template>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import { propertiesService } from 'src/services/properties';
import type {
  AppealArgument,
  AppealRecommendation,
  CounterAppealRisk,
  PropertyCategory,
  PropertyDetail,
  Recommendation,
  Uniformity,
  UniformitySignal,
  Valuation,
  ValuationConfidence,
} from 'src/types/api';

const props = defineProps<{ id: string }>();

const detail = ref<PropertyDetail | null>(null);
const valuation = ref<Valuation | null>(null);
const uniformity = ref<Uniformity | null>(null);
const recommendation = ref<Recommendation | null>(null);

const detailLoading = ref(true);
const valuationLoading = ref(true);
const uniformityLoading = ref(true);
const recommendationLoading = ref(true);

const detailError = ref<string | null>(null);

// Computed: recommendation styling
const recommendationLabel = computed((): string => {
  if (!recommendation.value) return '';
  const labels: Record<AppealRecommendation, string> = {
    appeal_strongly: 'Appeal Strongly',
    appeal: 'Appeal',
    marginal: 'Marginal Case',
    do_not_appeal: 'Do Not Appeal',
    insufficient_data: 'Insufficient Data',
  };
  return labels[recommendation.value.recommendation];
});

const recommendationColor = computed((): string => {
  if (!recommendation.value) return 'grey';
  const colors: Record<AppealRecommendation, string> = {
    appeal_strongly: 'positive',
    appeal: 'primary',
    marginal: 'warning',
    do_not_appeal: 'negative',
    insufficient_data: 'grey-7',
  };
  return colors[recommendation.value.recommendation];
});

const recommendationBgClass = computed(() => {
  if (!recommendation.value) return '';
  const bgs: Record<AppealRecommendation, string> = {
    appeal_strongly: 'bg-green-1',
    appeal: 'bg-blue-1',
    marginal: 'bg-orange-1',
    do_not_appeal: 'bg-red-1',
    insufficient_data: 'bg-grey-2',
  };
  return bgs[recommendation.value.recommendation];
});

const recommendationIcon = computed((): string => {
  if (!recommendation.value) return 'help';
  const icons: Record<AppealRecommendation, string> = {
    appeal_strongly: 'thumb_up',
    appeal: 'check_circle',
    marginal: 'help',
    do_not_appeal: 'do_not_disturb',
    insufficient_data: 'help_outline',
  };
  return icons[recommendation.value.recommendation];
});

// Computed: argument styling
const argumentLabel = computed((): string => {
  if (!recommendation.value) return '';
  const labels: Record<AppealArgument, string> = {
    market_value: 'Market Value',
    uniformity: 'Uniformity',
    both: 'Market Value + Uniformity',
    none: '—',
  };
  return labels[recommendation.value.primary_argument];
});

const argumentChipColor = computed((): string => {
  if (!recommendation.value) return 'grey';
  return recommendation.value.primary_argument === 'both' ? 'positive' : 'primary';
});

const argumentIcon = computed((): string => {
  if (!recommendation.value) return '';
  const icons: Record<AppealArgument, string> = {
    market_value: 'attach_money',
    uniformity: 'balance',
    both: 'gavel',
    none: '',
  };
  return icons[recommendation.value.primary_argument];
});

const riskChipColor = computed((): string => {
  if (!recommendation.value) return 'grey';
  const colors: Record<CounterAppealRisk, string> = {
    low: 'grey',
    medium: 'warning',
    high: 'negative',
    unknown: 'grey',
  };
  return colors[recommendation.value.counter_appeal_risk];
});

// Computed: uniformity coloring
const uniformityColor = computed((): string => {
  if (!uniformity.value?.deviation_from_neighborhood) return '';
  return uniformity.value.deviation_from_neighborhood > 0
    ? 'text-negative'
    : 'text-positive';
});

const blockDeviationColor = computed((): string => {
  if (!uniformity.value?.deviation_from_block) return '';
  return uniformity.value.deviation_from_block > 0
    ? 'text-negative'
    : 'text-positive';
});

// Helpers
function confidenceChipColor(c: ValuationConfidence): string {
  const colors: Record<ValuationConfidence, string> = {
    high: 'positive',
    medium: 'primary',
    low: 'warning',
    insufficient_data: 'grey',
  };
  return colors[c];
}

function signalChipColor(s: UniformitySignal): string {
  const colors: Record<UniformitySignal, string> = {
    strong_case: 'positive',
    moderate_case: 'primary',
    weak_case: 'warning',
    no_case: 'grey',
    insufficient_data: 'grey',
  };
  return colors[s];
}

function formatSignal(s: UniformitySignal): string {
  const labels: Record<UniformitySignal, string> = {
    strong_case: 'Strong case',
    moderate_case: 'Moderate case',
    weak_case: 'Weak case',
    no_case: 'No case',
    insufficient_data: 'Insufficient data',
  };
  return labels[s];
}

function formatCategory(cat: PropertyCategory): string {
  const labels: Record<PropertyCategory, string> = {
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
  return labels[cat] ?? cat;
}

function formatNumber(n: number): string {
  return n.toLocaleString('en-US');
}

function formatPercent(n: number): string {
  const sign = n > 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(1)}%`;
}

const compColumns = [
  {
    name: 'address',
    label: 'Address',
    field: 'address_full',
    align: 'left' as const,
  },
  {
    name: 'sale_date',
    label: 'Sold',
    field: 'sale_date',
    align: 'left' as const,
  },
  {
    name: 'sale_price',
    label: 'Price',
    field: 'sale_price',
    align: 'right' as const,
    format: (v: number) => `$${formatNumber(v)}`,
  },
  {
    name: 'sqft',
    label: 'Sqft',
    field: 'living_area',
    align: 'right' as const,
    format: (v: number | null) => v ? formatNumber(v) : '—',
  },
  {
    name: 'ppsf',
    label: '$/sqft',
    field: 'price_per_sqft',
    align: 'right' as const,
    format: (v: number | null) => v ? `$${Math.round(v)}` : '—',
  },
  {
    name: 'scope',
    label: 'Scope',
    field: 'geographic_scope',
    align: 'left' as const,
    format: (v: string) => {
      const labels: Record<string, string> = {
        same_block: 'Same block',
        same_census_tract: 'Same neighborhood',
        same_ward: 'Same area',
      };
      return labels[v] ?? v.replace(/_/g, ' ');
    },
  },
  {
    name: 'score',
    label: 'Match',
    field: 'similarity_score',
    align: 'right' as const,
    format: (v: number) => `${Math.round(v * 100)}%`,
  },
];

// Data loading
async function loadDetail() {
  detailLoading.value = true;
  detailError.value = null;
  try {
    detail.value = await propertiesService.getDetail(props.id);
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      detailError.value = 'Property not found.';
    } else {
      detailError.value = 'Failed to load property. Please try again.';
      console.error(err);
    }
  } finally {
    detailLoading.value = false;
  }
}

async function loadValuation() {
  valuationLoading.value = true;
  try {
    valuation.value = await propertiesService.getValuation(props.id);
  } catch (err) {
    console.error('Valuation load failed', err);
  } finally {
    valuationLoading.value = false;
  }
}

async function loadUniformity() {
  uniformityLoading.value = true;
  try {
    uniformity.value = await propertiesService.getUniformity(props.id);
  } catch (err) {
    console.error('Uniformity load failed', err);
  } finally {
    uniformityLoading.value = false;
  }
}

async function loadRecommendation() {
  recommendationLoading.value = true;
  try {
    recommendation.value = await propertiesService.getRecommendation(props.id);
  } catch (err) {
    console.error('Recommendation load failed', err);
  } finally {
    recommendationLoading.value = false;
  }
}

async function loadAll() {
  await loadDetail();
  if (detailError.value) return;
  await Promise.all([loadValuation(), loadUniformity(), loadRecommendation()]);
}

onMounted(() => {
  void loadAll();
});

watch(
  () => props.id,
  () => {
    void loadAll();
  },
);
</script>

<style scoped>
.reasoning-list {
  padding-left: 1.5em;
  margin: 0;
}
.reasoning-list li {
  margin-bottom: 0.5em;
  line-height: 1.5;
}
</style>