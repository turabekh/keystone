"""populate clr ratios effective tax rates and source notes

Revision ID: a8be66e7901d
Revises: 29feceb4dc34
Create Date: 2026-05-11 21:05:03.614452

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "a8be66e7901d"
down_revision: str | Sequence[str] | None = "29feceb4dc34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        UPDATE keystone.county_year_settings cys
        SET clr_ratio = updates.clr_ratio,
            effective_tax_rate = updates.effective_tax_rate,
            clr_sample_size = updates.clr_sample_size,
            clr_source_note = updates.clr_source_note,
            last_reassessment_year = COALESCE(updates.last_reassessment_year, cys.last_reassessment_year)
        FROM (VALUES
            (
                'philadelphia',
                100.0000::numeric(8,4),
                0.013998::numeric(8,6),
                NULL::integer,
                2024::integer,
                'Philadelphia uses Reassessment Use designation 100 (effective Jan 1 2025) per PA Bulletin 55-27. STEB 2024 statistical CLR was 90.70 but designated 100 for appeals. Effective tax rate 1.3998% is exact combined City + School District flat rate. Source: Philadelphia OPA, Pa. Bulletin 55-27 (Jul 5 2025).'
            ),
            (
                'bucks',
                5.8600::numeric(8,4),
                0.017300::numeric(8,6),
                6361::integer,
                NULL::integer,
                'STEB 2024 certified residential CLR 5.86% (sample size 6361, factor 17.06). Estimated effective tax rate 1.73% is midpoint of 1.55-1.91% range; actual rate varies by school district. Source: STEB 2024 Common Level Ratio document (Jun 18 2025), PA DOR factor list (Jan 2026), SmartAsset Pennsylvania Property Tax data. 2024 STEB values are most recent available; will be superseded by 2025 STEB ratios published ~Jul 2026.'
            ),
            (
                'montgomery',
                30.7600::numeric(8,4),
                0.014400::numeric(8,6),
                NULL::integer,
                NULL::integer,
                'STEB 2024 certified CLR 30.76% (factor 3.25). Estimated effective tax rate 1.44% is midpoint of 1.25-1.62% range; actual rate varies by school district. Source: STEB 2024 Common Level Ratio document (Jun 18 2025), PA DOR factor list (Jan 2026), Montgomery County official notice (Jun 25 2024). 2024 STEB values are most recent available; will be superseded by 2025 STEB ratios published ~Jul 2026.'
            ),
            (
                'delaware',
                57.3300::numeric(8,4),
                0.018600::numeric(8,6),
                6537::integer,
                2021::integer,
                'STEB 2024 certified CLR 57.33% (sample size 6537, factor 1.74). Delaware reassessed effective TY2021 — highest CLR among the five seeded counties as a result. Estimated effective tax rate 1.86% is midpoint of 1.67-2.05% range; actual rate varies by school district. Source: STEB 2024 Common Level Ratio document (Jun 18 2025), PA DOR factor list (Jan 2026), Ownwell Delaware County data.'
            ),
            (
                'chester',
                31.8400::numeric(8,4),
                0.012500::numeric(8,6),
                5297::integer,
                1998::integer,
                'STEB 2024 certified CLR 31.84% (sample size 5297, factor 3.14). Last reassessment 1998. Estimated effective tax rate 1.25% is countywide average; actual rate varies by school district. Source: STEB 2024 Common Level Ratio document (Jun 18 2025), PA DOR factor list (Jan 2026), SmartAsset Pennsylvania Property Tax data.'
            )
        ) AS updates(slug, clr_ratio, effective_tax_rate, clr_sample_size, last_reassessment_year, clr_source_note)
        WHERE cys.tax_year = 2027
          AND cys.county_id = (SELECT id FROM keystone.counties WHERE slug = updates.slug AND state = 'PA');
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE keystone.county_year_settings
        SET clr_ratio = NULL,
            effective_tax_rate = NULL,
            clr_sample_size = NULL,
            clr_source_note = NULL
        WHERE tax_year = 2027;
    """)
    op.execute("""
        UPDATE keystone.county_year_settings cys
        SET last_reassessment_year = 2020
        FROM keystone.counties c
        WHERE cys.county_id = c.id AND c.slug = 'delaware' AND cys.tax_year = 2027;
    """)