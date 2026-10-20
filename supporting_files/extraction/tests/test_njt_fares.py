import unittest
import datetime as dt

from test_gtfs_importer import station_id_for  # Also installs the extraction import path.
from fetch_njt_fares import amount_cents, fare_query, parse_quotes
from build_njt_fares import compile_snapshot, ENDPOINT


class NjtFareTests(unittest.TestCase):
    def report(self, reverse_amount=2035):
        return {"source_url": ENDPOINT, "query_service_date": "2026-10-20",
                "retrieved_at": "2026-10-19T21:00:00+00:00", "quotes": [
                    {"origin": "NYP", "destination": "TRE", "quoted_amount_cents": 2035,
                     "usable_response": True, "via_secaucus_notice": False},
                    {"origin": "TRE", "destination": "NYP", "quoted_amount_cents": reverse_amount,
                     "usable_response": True, "via_secaucus_notice": False}]}

    def test_compiler_accepts_corroborated_prices_without_inventing_an_effective_date(self):
        snapshot = compile_snapshot(self.report(), required_pairs=[("NYP", "TRE")])
        self.assertEqual(snapshot["fares"]["NYP>TRE"]["amountCents"], 2035)
        self.assertEqual(snapshot["coverage"]["publishedPairs"], 2)
        self.assertNotIn("effectiveDate", snapshot)

    def test_directional_disagreement_does_not_choose_or_copy_a_price(self):
        with self.assertRaisesRegex(ValueError, "Missing corroborated core"):
            compile_snapshot(self.report(reverse_amount=2405), required_pairs=[("NYP", "TRE")])

    def test_undated_quotes_and_duplicate_pairs_rejected(self):
        report = self.report()
        report["query_service_date"] = None
        with self.assertRaisesRegex(ValueError, "explicit service date"):
            compile_snapshot(report)
        report = self.report()
        report["quotes"].append(report["quotes"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compile_snapshot(report)

    def test_secaucus_applicability_must_agree_in_both_responses(self):
        report = self.report()
        report["quotes"][1]["via_secaucus_notice"] = True
        with self.assertRaisesRegex(ValueError, "Missing corroborated core"):
            compile_snapshot(report, required_pairs=[("NYP", "TRE")])
    def test_only_unambiguous_positive_currency_is_a_quote(self):
        self.assertEqual(amount_cents("$20.35"), 2035)
        for value in [None, "", "$0.00", "$20", "$20.35–$24.05", "unknown", "-1", "20.35"]:
            self.assertIsNone(amount_cents(value))

    def test_partial_and_global_graphql_failures_do_not_become_prices(self):
        pairs = [("NYP", "TRE"), ("NJT_123", "NYP")]
        payload = {"data": {"q0": {"fare": {"regularFare": "$20.35", "showMessage": False}},
                            "q1": {"fare": {"regularFare": "$24.05", "showMessage": True}}},
                   "errors": [{"path": ["q1"], "message": "Failed"}]}
        quotes = parse_quotes(payload, pairs)
        self.assertEqual(quotes[0]["quoted_amount_cents"], 2035)
        self.assertIsNone(quotes[1]["quoted_amount_cents"])
        payload["errors"] = [{"message": "Global failure"}]
        self.assertFalse(any(q["usable_response"] for q in parse_quotes(payload, pairs)))

    def test_secaucus_notice_retained_and_missing_notice_rejected(self):
        payload = {"data": {"q0": {"fare": {"regularFare": "$24.05", "showMessage": True}}}}
        quote = parse_quotes(payload, [("NJT_123", "NYP")])[0]
        self.assertTrue(quote["via_secaucus_notice"])
        del payload["data"]["q0"]["fare"]["showMessage"]
        self.assertFalse(parse_quotes(payload, [("NJT_123", "NYP")])[0]["usable_response"])

    def test_station_titles_used_instead_of_incompatible_gtfs_ids(self):
        query = fare_query([("NYP", "TRE")], {"NYP": {"fare_station_title": "New York Penn Station"},
                                                 "TRE": {"fare_station_title": "Trenton Transit Center"}})
        self.assertIn('origin:"New York Penn Station"', query)
        self.assertNotIn("105", query)
        dated = fare_query([("NYP", "TRE")], {"NYP": {"fare_station_title": "New York Penn Station"},
                                                   "TRE": {"fare_station_title": "Trenton Transit Center"}}, dt.date(2026, 10, 20))
        self.assertIn('date:"10/20/2026"', dated)


if __name__ == "__main__":
    unittest.main()
