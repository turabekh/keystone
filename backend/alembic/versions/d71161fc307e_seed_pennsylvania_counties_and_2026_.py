"""seed pennsylvania counties and 2026 settings

Revision ID: d71161fc307e
Revises: d7ec42908766
Create Date: 2026-05-11 14:41:51.282002

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "d71161fc307e"
down_revision: str | Sequence[str] | None = "d7ec42908766"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO keystone.counties (name, state, slug, fips_code, filing_office_name, filing_office_address, filing_office_phone)
        VALUES
            ('Philadelphia', 'PA', 'philadelphia', '42101', 'Board of Revision of Taxes', 'The Curtis Center, 601 Walnut Street, Suite 325 East, Philadelphia, PA 19106', '(215) 686-4343'),
            ('Bucks', 'PA', 'bucks', '42017', 'Bucks County Board of Assessment Appeals', '55 East Court Street, Doylestown, PA 18901', '(215) 348-6219'),
            ('Montgomery', 'PA', 'montgomery', '42091', 'Montgomery County Board of Assessment Appeals', 'One Montgomery Plaza, 425 Swede Street, Norristown, PA 19401', '(610) 278-3761'),
            ('Delaware', 'PA', 'delaware', '42045', 'Delaware County Board of Assessment Appeals', '201 W Front Street, Media, PA 19063', '(610) 891-4273'),
            ('Chester', 'PA', 'chester', '42029', 'Chester County Board of Assessment Appeals', '313 W Market Street, West Chester, PA 19380', '(610) 344-6105');
    """)

    op.execute("""
        INSERT INTO keystone.county_year_settings (county_id, tax_year, clr_factor, par, appeal_deadline, last_reassessment_year, notes)
        SELECT
            c.id,
            settings.tax_year,
            settings.clr_factor,
            settings.par,
            settings.appeal_deadline,
            settings.last_reassessment_year,
            settings.notes
        FROM keystone.counties c
        JOIN (VALUES
            ('philadelphia', 2027, 1.00, 100.00, 'October 5, 2026 (first Monday in October)', 2024, 'No TY2026 reassessment. Appeals filed by Oct 5 2026 apply to TY2027.'),
            ('bucks', 2027, 17.06, 100.00, 'August 3, 2026', 1972, 'Last reassessment 1972. CLR factor extremely high.'),
            ('montgomery', 2027, 3.25, 100.00, 'August 1, 2026 (first business day in August)', 1996, NULL),
            ('delaware', 2027, 1.74, 100.00, 'August 1, 2026 (first business day in August)', 2020, NULL),
            ('chester', 2027, 3.14, 100.00, 'May 1 to first business day in August 2026', NULL, 'Filing window opens May 1, closes first business day in August.')
        ) AS settings(slug, tax_year, clr_factor, par, appeal_deadline, last_reassessment_year, notes)
        ON c.slug = settings.slug AND c.state = 'PA';
    """)


def downgrade() -> None:
    op.execute("DELETE FROM keystone.county_year_settings WHERE tax_year = 2027;")
    op.execute("DELETE FROM keystone.counties WHERE state = 'PA' AND slug IN ('philadelphia', 'bucks', 'montgomery', 'delaware', 'chester');")