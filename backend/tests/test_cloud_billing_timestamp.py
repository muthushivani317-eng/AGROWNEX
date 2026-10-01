from datetime import UTC, datetime

from app.modules.admin.cloud_billing import _bigquery_timestamp


def test_bigquery_epoch_float_and_iso_are_both_parsed():
    assert _bigquery_timestamp("1.7907192E9") == datetime.fromtimestamp(1_790_719_200, tz=UTC)
    assert _bigquery_timestamp("2026-09-30T00:00:00Z") == datetime(2026, 9, 30, tzinfo=UTC)
