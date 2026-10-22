"""Part J6f, item 1 (L-13): the live sunset's T03 stopped "the keep is not whole" on a whole dump, because `has-section`
asked a data section of `realtime.messages`, a partitioned parent with no partitions. Postgres keeps no rows in a partitioned
parent, so pg_dump writes no COPY for it, and Supabase ships that table in every project. A CREATE TABLE statement whose own
statement ends, at its closing `;`, in a `PARTITION BY` clause needs no data section of its own; every other table, a
partition among them, still does; a statement that cannot be read whole to its `;` fails the keep (G23-F2).

The block below is the one pg_dump 18.6 wrote from server 17.11, as the control room gave it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prov"))
import provlib  # noqa: E402
import harness  # noqa: E402
import test_lane_prov_set as pset  # noqa: E402
from sun_core import effects  # noqa: E402

REALTIME = """CREATE TABLE realtime.messages (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp()) NOT NULL,
    inserted_at timestamp without time zone DEFAULT timezone('utc'::text, clock_timestamp()) NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    binary_payload bytea,
    skip_broadcast boolean DEFAULT false NOT NULL
)
PARTITION BY RANGE (inserted_at);
"""
ALPHA = "CREATE TABLE public.alpha (\n    v text\n);\n"
ALPHA_COPY = "COPY public.alpha (v) FROM stdin;\n1\n\\.\n"
PARTITION = "CREATE TABLE realtime.messages_2026_01_01 (\n    topic text NOT NULL,\n    inserted_at timestamp without time zone NOT NULL\n);\n"
ATTACH = ("ALTER TABLE ONLY realtime.messages ATTACH PARTITION realtime.messages_2026_01_01 FOR VALUES FROM "
          "('2026-01-01 00:00:00') TO ('2026-01-02 00:00:00');\n")
PARTITION_COPY = "COPY realtime.messages_2026_01_01 (topic, inserted_at) FROM stdin;\n\\.\n"


def holds(text):
    check = [c for c in pset.sunset_row("T03")["keep_scope"]["content_checks"] if c["check"] == "has-section"][0]
    return effects.text_checks_hold(text.encode("utf-8"), check)


class HasSection(harness.Case):
    def test_T03_L13_KEEP1_a_partitioned_parent_with_no_partitions_needs_no_data_section(self):
        self.assertIs(holds("\n".join([ALPHA, REALTIME, ALPHA_COPY])), True)

    def test_T03_L13_KEEP1_a_partition_without_its_copy_still_fails_and_with_it_holds(self):
        self.assertIs(holds("\n".join([ALPHA, REALTIME, PARTITION, ATTACH, ALPHA_COPY])), False)
        self.assertIs(holds("\n".join([ALPHA, REALTIME, PARTITION, ATTACH, ALPHA_COPY, PARTITION_COPY])), True)

    def test_T03_L13_KEEP1_an_ordinary_table_without_its_copy_still_fails(self):
        self.assertIs(holds("\n".join([ALPHA, REALTIME])), False)

    def test_T03_L13_G23_F2_a_statement_cut_off_before_its_semicolon_fails(self):
        self.assertIs(holds("\n".join([ALPHA, ALPHA_COPY, REALTIME.rstrip(";\n")])), False)
        self.assertIs(holds("\n".join([ALPHA, ALPHA_COPY, REALTIME.split("PARTITION BY")[0]])), False)


class WholeSunset(harness.Case):
    def test_T03_L13_KEEP1_KEEP3_a_sunset_whose_dump_holds_supabases_partitioned_realtime_messages_reaches_T03_done(self):
        m = pset.world(self)
        looked, went = pset.started(m)
        self.assertEqual(went.ending, "complete", went.text)
        run = looked.doc["run"]
        self.assertEqual(m.statuses(run)["T03"], "done")
        with open(os.path.join(pset.folder(m), "demo-db.sql")) as fh:
            dump = fh.read()
        self.assertIn(REALTIME, dump)
        self.assertNotIn("COPY realtime.messages ", dump)
        done = pset.completion(m, run, "T03")
        self.assertIn("CREATE TABLE realtime.messages (", pset.record(m, run, done["keep"]["inventory"]))
        self.assertTrue(provlib.calls(m, "pg", "pg_dump"))


if __name__ == "__main__":
    import unittest
    unittest.main()
