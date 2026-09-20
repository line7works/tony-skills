"""Batch C of the sealed bench: the hand-off test (Astra's gaps 6 and 7).

52 of these 55 tests fail against batch B's commit `ddf96c4` and pass after batch C, measured.
The three that pass at both are in `PlanAndOrder` and are BACKWARD-COMPATIBILITY assertions,
which is what they are for: a plan with no `consumer` object still mints the old single pair,
the old flag forms still validate, and an id naming a case the plan does not run is still
refused.

Standard library only, Python 3.9, runs from any working directory. No test opens
`evals/answer-key/`, the held-out set, or any routing request, and nothing here launches a live
model: the campaign tests drive the fake launchers.
"""
import os
import shutil
import unittest

from testlib import CASE, RunnerCase, cli, parse_stdout, runner


def producer_command(run_dir, workspace, kind="comparison", case=CASE, setup="claude-code"):
    return {"setup": setup, "condition": "available", "kind": kind, "case": case,
            "status": "complete", "run_dir": run_dir, "workspace": workspace}


class PairFixture(RunnerCase):
    """A stand-in producer laid out the way a real one is: record, run leaf, workspace.

    The run leaf and the workspace are SIBLINGS outside the record (E10-54(a)), and the
    record holds its own copy of the run leaf, which is exactly what `collect_trial` writes.
    That layout is what the artifact normalizer exists for.
    """

    setups = ("claude-code", "codex")

    def producer(self, name="producer", stopped=False, artifact_in="run_dir"):
        record = os.path.join(self.scratch, name, "record")
        live = os.path.join(self.scratch, name, "live")
        run_dir = os.path.join(live, "run")
        workspace = os.path.join(live, "workspace")
        runner.ensure_dir(os.path.join(run_dir, "verifier"))
        runner.ensure_dir(workspace)
        runner.write_text(os.path.join(workspace, "README.md"), "a stand-in workspace\n")
        if artifact_in == "run_dir":
            artifact = os.path.join(run_dir, "verifier", "observation.txt")
        else:
            artifact = os.path.join(workspace, "observation.txt")
        runner.write_text(artifact, "observed seven\n")
        # the record's own copy of the run leaf, as `collect_trial` makes it
        shutil.copytree(run_dir, os.path.join(record, "run"))
        result = {
            "status": "verifier_unavailable" if stopped else "completed",
            "items": [] if stopped else [
                {"location": {"file": "src/demo.py", "line": 7},
                 "claim": "a stand-in claim", "failure_scenario": "run the counter",
                 "severity": "MAJOR", "disposition": "not_fixed", "reason": "reproduces",
                 "verification": {"evidence": [
                     {"kind": "command", "artifact_path": artifact,
                      "detail": "The observed counter remained at seven after the "
                                "operation; expected eight."}]}}],
            "cards": [],
            "source_identity": {"actual": {"commit": "abc123", "dirty": False}},
        }
        if stopped:
            result["stop_reason"] = "the transport refused the verifier call"
        runner.write_json(os.path.join(record, "result.json"), result)
        runner.write_json(os.path.join(record, "run", "checkpoint.json"),
                          {"phase": "completed", "continuations": 0, "scope": {"items": []}})
        row = {"record": record, "trial": "standin-%s" % name,
               "command": producer_command(run_dir, workspace)}
        return row, artifact

    def staged(self, producer, leaf="pair", setup=None, plan=None):
        campaign = runner.Campaign(self.campaign)
        return runner.stage_consumer_pair(campaign, producer,
                                          os.path.join(self.scratch, leaf),
                                          setup=setup, plan=plan)

    def honest_answer(self, pair, producer, **extra):
        """What a consumer that read the pair and the published schema would write."""
        expected = runner._consumer_expected(producer)
        items = []
        for item in expected["items"]:
            evidence = []
            for entry in item["evidence"]:
                evidence.append({"kind": entry["kind"], "detail": entry["detail"],
                                 "artifact_path": entry["artifact_path"]})
            items.append({"location": item["location"], "claim": item["claim"],
                          "disposition": item["disposition"], "reason": item["reason"],
                          "evidence": evidence})
        answer = {"items": items, "cards": expected["cards"],
                  "source_identity": expected["source_identity"]}
        answer.update(extra)
        path = os.path.join(pair["pair_dir"], runner.CONSUMER_ANSWER)
        runner.write_json(path, answer)
        return path, answer


# --------------------------------------------------------------------- 1. the caller's facts


class CallerFacts(PairFixture):
    """Gap 6: "Supply model/harness/date facts"."""

    def plan_with(self, model=None, effort=None, name="codex", sealed=False):
        plan = dict(self.plan_document)
        setups = []
        for spec in plan["setups"]:
            spec = dict(spec)
            if spec["name"] == name:
                if model:
                    spec["model"] = model
                if effort:
                    spec["effort"] = effort
            setups.append(spec)
        plan["setups"] = setups
        plan["sealed"] = sealed
        return plan

    def test_the_input_carries_the_callers_harness_and_model(self):
        producer, _artifact = self.producer("facts")
        plan = self.plan_with(model="gpt-5.6-sol", effort="medium", sealed=True)
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, plan, "codex")
        pair = self.staged(producer, "facts-pair", setup=setup, plan=plan)
        document = runner.read_json(pair["input"])
        invocation = document["invocation"]
        self.assertEqual(invocation["harness"],
                         {"name": "codex", "version": "unknown", "entry": "plugin",
                          "sandbox": "sandbox-exec, the bench's own profile (A1)"})
        self.assertEqual(invocation["model"]["id"], "gpt-5.6-sol")
        self.assertEqual(invocation["model"]["floor_class"], "opus")
        self.assertIs(invocation["model"]["floor_met"], True)
        self.assertEqual(invocation["model"]["effort"], "medium")
        self.assertEqual(invocation["run_date"], plan["run_date"])
        self.assertIs(invocation["session_wrote_fix"], False)

    def test_an_unsealed_campaign_says_so_in_the_sandbox_field(self):
        producer, _artifact = self.producer("unsealed")
        plan = self.plan_with(model="gpt-5.6-sol", sealed=False)
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, plan, "codex")
        pair = self.staged(producer, "unsealed-pair", setup=setup, plan=plan)
        harness = runner.read_json(pair["input"])["invocation"]["harness"]
        self.assertEqual(harness["sandbox"], "the harness's own default")

    def test_an_unpinned_model_is_unknown_and_never_guessed(self):
        """The plan named no model, so the caller has no class to assert. E9-3's own answer."""
        producer, _artifact = self.producer("unpinned")
        plan = self.plan_with()          # no model on either setup
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, plan, "codex")
        pair = self.staged(producer, "unpinned-pair", setup=setup, plan=plan)
        model = runner.read_json(pair["input"])["invocation"]["model"]
        self.assertEqual(model["floor_class"], "unknown")
        self.assertIsNone(model["floor_met"])

    def test_the_floor_map_is_each_adapters_own(self):
        self.assertEqual(runner.caller_model_class("claude-code", "opus"), ("opus", True))
        self.assertEqual(runner.caller_model_class("claude-code", "claude-opus-5"),
                         ("opus", True))
        self.assertEqual(runner.caller_model_class("claude-code", "claude-haiku-4"),
                         ("haiku", False))
        self.assertEqual(runner.caller_model_class("codex", "gpt-5.6-sol"), ("opus", True))
        self.assertEqual(runner.caller_model_class("opencode",
                                                   "openrouter/qwen/qwen3.8-flash"),
                         ("opus", True))
        self.assertEqual(runner.caller_model_class("codex", "a-model-no-map-lists"),
                         ("unknown", None))
        self.assertEqual(runner.caller_model_class("codex", None), ("unknown", None))

    def test_the_facts_validate_against_the_input_schema(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is not installed for this interpreter")
        schema = runner.read_json(os.path.join(runner.SKILL_DIR, "references",
                                               "input.schema.json"))
        producer, _artifact = self.producer("valid")
        plan = self.plan_with(model="gpt-5.6-sol", effort="medium")
        campaign = runner.Campaign(self.campaign)
        setup = runner.setup_for(campaign, plan, "codex")
        pair = self.staged(producer, "valid-pair", setup=setup, plan=plan)
        Draft202012Validator(schema).validate(runner.read_json(pair["input"]))


# ------------------------------------------------------------------- 2. the pair is retained


class PairRetention(PairFixture):
    """Gap 6: "retain the entire pair"."""

    def consumer_record(self, name="retained"):
        producer, _artifact = self.producer(name)
        pair = self.staged(producer, "%s-pair" % name)
        record = os.path.join(self.scratch, "%s-record" % name)
        runner.ensure_dir(record)
        return producer, pair, record

    def test_the_whole_pair_is_copied_into_the_record_with_a_manifest(self):
        producer, pair, record = self.consumer_record()
        self.honest_answer(pair, producer)
        manifest = runner.retain_pair(record, pair, producer, {"result.json": "deadbeef"})
        self.assertTrue(manifest["copied"])
        copied_root = os.path.join(record, "pair")
        self.assertTrue(os.path.isdir(copied_root))
        self.assertTrue(os.path.isfile(os.path.join(record, "pair-manifest.json")))
        # every file of the pair, with its size and its sha256
        on_disk = set()
        for base, _dirs, names in os.walk(copied_root):
            for entry in names:
                on_disk.add(os.path.relpath(os.path.join(base, entry), copied_root))
        self.assertEqual(sorted(row["path"] for row in manifest["files"]), sorted(on_disk))
        for row in manifest["files"]:
            full = os.path.join(copied_root, row["path"])
            self.assertEqual(row["sha256"], runner.file_sha256(full), row["path"])
            self.assertEqual(row["bytes"], os.path.getsize(full), row["path"])
        self.assertEqual(manifest["file_count"], len(on_disk))
        self.assertIn(runner.CONSUMER_ANSWER, on_disk)
        self.assertIn(os.path.join("run", runner.CONSUMER_ANSWER_SCHEMA), on_disk)

    def test_the_manifest_names_the_producer_record_and_both_hash_sets(self):
        producer, pair, record = self.consumer_record("hashes")
        after = dict(pair["producer_hashes_before"])
        manifest = runner.retain_pair(record, pair, producer, after)
        self.assertEqual(manifest["producer_record"], producer["record"])
        self.assertEqual(manifest["producer_trial"], producer["trial"])
        self.assertEqual(manifest["producer_hashes_before"],
                         pair["producer_hashes_before"])
        self.assertEqual(manifest["producer_hashes_after"], after)
        self.assertTrue(manifest["producer_hashes_before"])

    def test_the_pair_is_copied_and_never_moved(self):
        producer, pair, record = self.consumer_record("copy")
        before = sorted(os.listdir(pair["pair_dir"]))
        runner.retain_pair(record, pair, producer)
        self.assertTrue(os.path.isdir(pair["pair_dir"]))
        self.assertEqual(sorted(os.listdir(pair["pair_dir"])), before)

    def test_a_retained_pair_is_never_overwritten(self):
        producer, pair, record = self.consumer_record("once")
        runner.retain_pair(record, pair, producer)
        with self.assertRaises(runner.Usage):
            runner.retain_pair(record, pair, producer)

    def test_a_grade_reads_the_retained_copy_when_the_scratch_is_gone(self):
        """The point of retaining it: the tree survives a cleared `<campaign>/tmp/`."""
        producer, pair, record = self.consumer_record("survives")
        self.honest_answer(pair, producer)
        runner.retain_pair(record, pair, producer, dict(pair["producer_hashes_before"]))
        shutil.rmtree(pair["pair_dir"])
        view, how = runner.retained_pair_view(record, pair)
        self.assertTrue(how["rebased"])
        self.assertTrue(os.path.isdir(view["pair_dir"]))
        self.assertTrue(os.path.isfile(os.path.join(view["pair_dir"],
                                                    runner.CONSUMER_ANSWER)))
        grade = runner.consumer_grade(
            view, producer, os.path.join(view["pair_dir"], runner.CONSUMER_ANSWER),
            producer_hashes_after=dict(pair["producer_hashes_before"]))
        self.assertTrue(grade["checks"]["original_scope"])
        self.assertTrue(grade["checks"]["evidence_references"])
        self.assertTrue(grade["checks"]["evidence_artifacts_recovered"])

    def test_the_live_pair_is_preferred_while_it_is_still_there(self):
        producer, pair, record = self.consumer_record("live")
        runner.retain_pair(record, pair, producer)
        view, how = runner.retained_pair_view(record, pair)
        self.assertFalse(how["rebased"])
        self.assertEqual(view["pair_dir"], pair["pair_dir"])


# ----------------------------------------------------------------- 3. the published schema


class PublishedSchema(PairFixture):
    """Gap 6: "publish the answer schema in the prompt and use that same shape in grading"."""

    def test_the_schema_is_copied_into_the_pairs_run_directory(self):
        producer, _artifact = self.producer("schema")
        pair = self.staged(producer, "schema-pair")
        copied = os.path.join(pair["run_dir"], runner.CONSUMER_ANSWER_SCHEMA)
        self.assertEqual(pair["answer_schema"], copied)
        self.assertTrue(os.path.isfile(copied))
        canonical = os.path.join(runner.SKILL_DIR, "references",
                                 runner.CONSUMER_ANSWER_SCHEMA)
        self.assertEqual(runner.file_sha256(copied), runner.file_sha256(canonical))

    def test_the_prompt_cites_the_schema_and_inlines_no_shape(self):
        producer, _artifact = self.producer("prompt")
        pair = self.staged(producer, "prompt-pair")
        prompt = runner.CONSUMER_PROMPT_TEMPLATE.format(
            producer=pair["producer_dir"], workspace=pair["workspace"],
            input=pair["input"], run_dir=pair["run_dir"], run_id=pair["run_id"],
            run_date="2026-09-20",
            answer=os.path.join(pair["pair_dir"], runner.CONSUMER_ANSWER),
            answer_schema=pair["answer_schema"])
        self.assertIn(pair["answer_schema"], prompt)
        # the old inlined shape is gone, `artifact` and all
        self.assertNotIn('"disposition": "fixed | not_fixed"', prompt)
        self.assertNotIn('"artifact"', prompt)
        self.assertNotIn("<the artifact or null>", prompt)

    def test_the_grader_reads_the_published_names(self):
        """`artifact_path`, `status`, `stop_reason`, `continuation.item_rows`."""
        schema = runner.read_json(os.path.join(runner.SKILL_DIR, "references",
                                               runner.CONSUMER_ANSWER_SCHEMA))
        properties = schema["properties"]
        self.assertIn("status", properties)
        self.assertIn("stop_reason", properties)
        self.assertIn("artifact_path",
                      properties["items"]["items"]["properties"]["evidence"]["items"]
                      ["properties"])
        self.assertIn("item_rows", properties["continuation"]["properties"])

    def test_a_schema_valid_answer_is_never_failed_for_its_shape(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is not installed for this interpreter")
        producer, _artifact = self.producer("valid-answer")
        pair = self.staged(producer, "valid-answer-pair")
        answer_path, answer = self.honest_answer(pair, producer)
        schema = runner.read_json(os.path.join(runner.SKILL_DIR, "references",
                                               runner.CONSUMER_ANSWER_SCHEMA))
        Draft202012Validator(schema).validate(answer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        # every check the ANSWER's own shape decides passes; the checks that need a
        # consumer result (there is none in this grade) are not the subject here.
        for name in ("answer_present", "original_scope", "item_identity",
                     "evidence_references", "evidence_artifacts_recovered",
                     "card_interpretation", "producer_history_preserved"):
            self.assertTrue(grade["checks"][name], "%s: %s" % (name, grade["why"]))


# -------------------------------------------------------------- 4. the artifact path mapping


class ArtifactPathMapping(PairFixture):
    """Gap 6: "map original artifact paths through the recorded producer run directory"."""

    def test_an_artifact_under_the_producers_run_directory_reaches_the_pair(self):
        producer, artifact = self.producer("mapped")
        pair = self.staged(producer, "mapped-pair")
        row = pair["artifacts"][0]
        self.assertEqual(row["artifact_path"], artifact)
        self.assertEqual(row["root"], "run_dir")
        self.assertTrue(row["copied"], row.get("why"))
        self.assertTrue(os.path.isfile(row["staged"]))
        self.assertEqual(runner.file_sha256(row["staged"]), runner.file_sha256(artifact))
        self.assertEqual(row["staged"],
                         os.path.join(pair["producer_dir"], "run", "verifier",
                                      "observation.txt"))

    def test_an_artifact_under_the_producers_workspace_reaches_the_pair(self):
        producer, artifact = self.producer("ws", artifact_in="workspace")
        pair = self.staged(producer, "ws-pair")
        row = pair["artifacts"][0]
        self.assertEqual(row["root"], "workspace")
        self.assertTrue(row["copied"], row.get("why"))
        self.assertEqual(row["staged"],
                         os.path.join(pair["workspace"], "observation.txt"))
        self.assertEqual(runner.file_sha256(row["staged"]), runner.file_sha256(artifact))

    def test_both_forms_of_one_path_key_the_same(self):
        producer, artifact = self.producer("keys")
        pair = self.staged(producer, "keys-pair")
        mapping = pair["path_map"]
        relocated = pair["artifacts"][0]["staged"]
        self.assertNotEqual(relocated, artifact)
        self.assertEqual(runner.artifact_key(artifact, mapping, pair),
                         runner.artifact_key(relocated, mapping, pair))
        as_producer = runner.normalize_artifact_path(relocated, mapping, pair)
        self.assertEqual(as_producer["as_producer"], artifact)
        self.assertEqual(as_producer["in_the_pair"], relocated)
        as_pair = runner.normalize_artifact_path(artifact, mapping, pair)
        self.assertEqual(as_pair["in_the_pair"], relocated)
        self.assertEqual(as_pair["as_producer"], artifact)

    def test_any_other_path_keys_as_itself(self):
        producer, _artifact = self.producer("other")
        pair = self.staged(producer, "other-pair")
        mapping = pair["path_map"]
        row = runner.normalize_artifact_path("/somewhere/else/observation.txt",
                                             mapping, pair)
        self.assertIsNone(row["as_producer"])
        self.assertIsNone(row["in_the_pair"])
        self.assertEqual(row["key"], "/somewhere/else/observation.txt")
        self.assertIn("under neither", row["why"])

    def test_the_relocated_path_the_consumer_opened_is_accepted(self):
        """The consumer opened the pair's copy, so that is the path it can name."""
        producer, _artifact = self.producer("relocated")
        pair = self.staged(producer, "relocated-pair")
        relocated = pair["artifacts"][0]["staged"]
        answer_path, _answer = self.honest_answer(pair, producer)
        answer = runner.read_json(answer_path)
        answer["items"][0]["evidence"][0]["artifact_path"] = relocated
        runner.write_json(answer_path, answer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertTrue(grade["checks"]["evidence_references"], grade["evidence"][0]["why"])
        self.assertTrue(grade["checks"]["evidence_artifacts_recovered"])

    def test_any_other_path_still_fails(self):
        producer, _artifact = self.producer("wrong")
        pair = self.staged(producer, "wrong-pair")
        answer_path, _answer = self.honest_answer(pair, producer)
        answer = runner.read_json(answer_path)
        answer["items"][0]["evidence"][0]["artifact_path"] = "/elsewhere/observation.txt"
        runner.write_json(answer_path, answer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertFalse(grade["checks"]["evidence_references"])
        self.assertFalse(grade["checks"]["evidence_artifacts_recovered"])

    def test_the_grade_row_records_both_forms(self):
        producer, artifact = self.producer("rows")
        pair = self.staged(producer, "rows-pair")
        relocated = pair["artifacts"][0]["staged"]
        answer_path, _answer = self.honest_answer(pair, producer)
        answer = runner.read_json(answer_path)
        answer["items"][0]["evidence"][0]["artifact_path"] = relocated
        runner.write_json(answer_path, answer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        row = grade["evidence_artifacts"][0]
        self.assertEqual(row["producer_as_recorded"], artifact)
        self.assertEqual(row["producer_in_the_pair"], relocated)
        self.assertEqual(row["consumer_named"], relocated)
        self.assertEqual(row["consumer_as_recorded"], artifact)
        self.assertTrue(row["content_matches"])
        self.assertEqual(row["root"], "run_dir")
        self.assertTrue(grade["artifact_path_map"])
        self.assertEqual(sorted(entry["which"] for entry in grade["artifact_path_map"]),
                         ["record", "run_dir", "workspace"])


# ------------------------------------------------------------- 5. consumption_completed


class ConsumptionCompleted(PairFixture):
    """Gap 6: "Treat an intended completed outcome separately from a valid terminal envelope"."""

    def graded(self, name, result, answer_extra=None, stopped=False):
        producer, _artifact = self.producer(name, stopped=stopped)
        pair = self.staged(producer, "%s-pair" % name)
        answer_path, _answer = self.honest_answer(pair, producer, **(answer_extra or {}))
        result_path = os.path.join(pair["run_dir"], "result.json")
        runner.write_json(result_path, result)
        reply = os.path.join(self.scratch, name, "reply.md")
        runner.ensure_dir(os.path.dirname(reply))
        runner.write_text(reply, "the consumer's reply\n")
        return runner.consumer_grade(pair, producer, answer_path,
                                     result_path=result_path,
                                     producer_hashes_after=dict(
                                         pair["producer_hashes_before"])), pair

    def test_a_valid_terminal_envelope_fails_the_check(self):
        grade, _pair = self.graded("envelope", {"status": "missing_input", "items": []})
        self.assertFalse(grade["checks"]["consumption_completed"])
        self.assertEqual(grade["consumption"]["consumer_status"], "missing_input")
        self.assertFalse(grade["consumption"]["status_is_completed"])
        self.assertIn("consumption_completed", grade["why"])
        # the shape of the envelope is not what failed: the answer's own checks stand
        self.assertTrue(grade["checks"]["original_scope"])

    def test_a_verifier_unavailable_envelope_fails_the_check_too(self):
        grade, _pair = self.graded("unavailable",
                                   {"status": "verifier_unavailable", "items": []})
        self.assertFalse(grade["checks"]["consumption_completed"])

    def test_the_check_is_required_not_conditional(self):
        self.assertIn("consumption_completed", runner.CONSUMER_CHECKS)
        self.assertNotIn("consumption_completed", runner.CONSUMER_CHECKS_CONDITIONAL)

    def test_a_missing_result_fails_the_check(self):
        producer, _artifact = self.producer("noresult")
        pair = self.staged(producer, "noresult-pair")
        answer_path, _answer = self.honest_answer(pair, producer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertFalse(grade["checks"]["consumption_completed"])
        self.assertIsNone(grade["consumption"]["consumer_status"])

    def test_a_stopped_producer_is_consumed_by_recovering_the_stop(self):
        """The rule, written down: the intended outcome follows the PRODUCER's own ending."""
        producer, _artifact = self.producer("stopped", stopped=True)
        pair = self.staged(producer, "stopped-pair")
        answer_path = os.path.join(pair["pair_dir"], runner.CONSUMER_ANSWER)
        runner.write_json(answer_path, {
            "items": [], "cards": [],
            "status": "verifier_unavailable",
            "stop_reason": "the transport refused the verifier call"})
        result_path = os.path.join(pair["run_dir"], "result.json")
        runner.write_json(result_path, {"status": "completed", "items": []})
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      result_path=result_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertTrue(grade["checks"]["producer_stop_recovered"])
        self.assertIn("recovered", grade["consumption"]["intended_outcome"])
        self.assertTrue(grade["consumption"]["intended_outcome_reached"])

    def test_a_stopped_producer_whose_stop_is_not_recovered_fails(self):
        producer, _artifact = self.producer("missed-stop", stopped=True)
        pair = self.staged(producer, "missed-stop-pair")
        answer_path = os.path.join(pair["pair_dir"], runner.CONSUMER_ANSWER)
        runner.write_json(answer_path, {"items": [], "cards": []})
        result_path = os.path.join(pair["run_dir"], "result.json")
        runner.write_json(result_path, {"status": "completed", "items": []})
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      result_path=result_path,
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertFalse(grade["checks"]["producer_stop_recovered"])
        self.assertFalse(grade["checks"]["consumption_completed"])
        self.assertFalse(grade["consumption"]["intended_outcome_reached"])


# ------------------------------------------------- 6. the pair-scoped isolation fact (gap 7)


class PairScopedIsolation(PairFixture):

    def test_the_pair_scoped_fact_is_its_own_field_and_the_check_stays_required(self):
        producer, _artifact = self.producer("scope")
        pair = self.staged(producer, "scope-pair")
        answer_path, _answer = self.honest_answer(pair, producer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      isolation={"separated": True},
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertTrue(grade["checks"]["unrelated_records_unavailable"])
        self.assertEqual(grade["pair_scope"]["unrelated_records_staged"], [])
        self.assertTrue(grade["pair_scope"]["no_unrelated_record_was_staged"])
        self.assertEqual(grade["pair_scope"]["producer_record"], producer["record"])
        # the read-access check is still what decides the grade
        ungraded = runner.consumer_grade(pair, producer, answer_path,
                                         isolation={"separated": False},
                                         producer_hashes_after=dict(
                                             pair["producer_hashes_before"]))
        self.assertFalse(ungraded["checks"]["unrelated_records_unavailable"])
        self.assertTrue(ungraded["pair_scope"]["no_unrelated_record_was_staged"])

    def test_an_unrelated_record_staged_into_the_pair_is_named(self):
        producer, _artifact = self.producer("dirty")
        pair = self.staged(producer, "dirty-pair")
        runner.write_text(os.path.join(pair["producer_dir"], "someone-elses.json"), "{}\n")
        pair["unrelated_records_present"] = [
            name for name in sorted(os.listdir(pair["producer_dir"]))
            if name not in runner.CONSUMER_COPIED and name != "run"]
        answer_path, _answer = self.honest_answer(pair, producer)
        grade = runner.consumer_grade(pair, producer, answer_path,
                                      isolation={"separated": True},
                                      producer_hashes_after=dict(
                                          pair["producer_hashes_before"]))
        self.assertIn("someone-elses.json", grade["pair_scope"]["unrelated_records_staged"])
        self.assertFalse(grade["pair_scope"]["no_unrelated_record_was_staged"])


# ------------------------------------------------------------------- 7. the plan and the ids


class PlanAndOrder(RunnerCase):
    setups = ("claude-code", "codex")

    def plan(self, **overrides):
        plan = dict(self.plan_document)
        plan.update(overrides)
        return plan

    def test_a_plan_with_no_consumer_block_mints_the_old_single_pair(self):
        plan = self.plan()
        plan.pop("consumer", None)
        order = runner.consumer_order(plan)
        self.assertEqual(sorted(t for rows in order.values() for t in rows),
                         ["consumer-claude-code-to-codex-r1",
                          "consumer-codex-to-claude-code-r1"])

    def test_the_consumer_block_mints_one_trial_per_kind_per_pair(self):
        plan = self.plan(cases=[CASE, "F2-01-reproduces"],
                         continuation={"case": "F3-02-mixed-two-items",
                                       "condition": "available", "repetitions": 1},
                         consumer={"repetitions_per_pair": 1})
        order = runner.consumer_order(plan)
        ids = sorted(t for rows in order.values() for t in rows)
        # two directed pairs, four kinds each: both continuation kinds and the two cases
        self.assertEqual(len(ids), 8)
        self.assertIn("consumer-claude-code-to-codex-handoff-r1", ids)
        self.assertIn("consumer-claude-code-to-codex-compaction-r1", ids)
        self.assertIn("consumer-claude-code-to-codex-%s-r1" % CASE, ids)
        self.assertEqual(len(set(ids)), len(ids))

    def test_eight_per_directed_pair_is_the_clean_runs_shape(self):
        """Section 6 of the contract: both continuation kinds and the six cases."""
        plan = self.plan(cases=list(runner.DEFAULT_CASES), consumer={})
        order = runner.consumer_order(plan)
        for lane, rows in order.items():
            self.assertEqual(len(rows), 8, lane)
        self.assertEqual(sum(len(rows) for rows in order.values()), 16)

    def test_repetitions_per_pair_multiplies_the_kinds(self):
        plan = self.plan(cases=[CASE], consumer={"repetitions_per_pair": 2,
                                                 "producers": ["comparison:%s" % CASE]})
        order = runner.consumer_order(plan)
        ids = sorted(t for rows in order.values() for t in rows)
        self.assertEqual(len(ids), 4)
        self.assertIn("consumer-claude-code-to-codex-%s-r2" % CASE, ids)

    def test_the_ids_parse_back_to_their_kind(self):
        plan = self.plan(cases=[CASE])
        for tid, kind in (
                ("consumer-claude-code-to-codex-handoff-r1", "continuation:handoff"),
                ("consumer-claude-code-to-codex-compaction-r3", "continuation:compaction"),
                ("consumer-codex-to-claude-code-%s-r1" % CASE, "comparison:%s" % CASE),
                ("consumer-codex-to-claude-code-r1", None)):
            parts = runner.parse_consumer_id(plan, tid)
            self.assertEqual(parts["kind"], kind, tid)
        self.assertEqual(
            runner.parse_consumer_id(plan, "consumer-claude-code-to-codex-handoff-r2"),
            {"trial": "consumer-claude-code-to-codex-handoff-r2", "producer": "claude-code",
             "consumer": "codex", "rep": 2, "token": "handoff",
             "kind": "continuation:handoff"})

    def test_an_id_naming_a_case_the_plan_does_not_run_is_refused(self):
        plan = self.plan(cases=[CASE])
        with self.assertRaises(runner.Usage):
            runner.parse_consumer_id(plan, "consumer-claude-code-to-codex-F9-99-nope-r1")

    def test_the_plan_refuses_an_unknown_producer_kind(self):
        plan = self.plan(cases=[CASE], consumer={"producers": ["comparison:F9-99-nope"]})
        with self.assertRaises(runner.Usage) as caught:
            runner.validate_plan(plan)
        self.assertIn("producers", str(caught.exception))

    def test_the_plan_refuses_an_unknown_consumer_key(self):
        plan = self.plan(consumer={"repetitions": 3})
        with self.assertRaises(runner.Usage) as caught:
            runner.validate_plan(plan)
        self.assertIn("repetitions_per_pair", str(caught.exception))

    def test_the_plan_refuses_a_bad_repetition_count(self):
        plan = self.plan(consumer={"repetitions_per_pair": 0})
        with self.assertRaises(runner.Usage):
            runner.validate_plan(plan)

    def test_the_plan_refuses_a_continuation_kind_with_no_continuation_set(self):
        plan = self.plan(continuation=None,
                         consumer={"producers": ["continuation:handoff"]})
        with self.assertRaises(runner.Usage) as caught:
            runner.validate_plan(plan)
        self.assertIn("continuation", str(caught.exception))

    def test_the_old_flag_forms_still_validate(self):
        for value in (True, False, None):
            plan = self.plan(consumer=value)
            if value is None:
                plan.pop("consumer", None)
            runner.validate_plan(plan)

    def test_the_plan_command_counts_the_new_rows(self):
        path = os.path.join(self.scratch, "plan.json")
        plan = {"plan_version": 1, "campaign_id": "batchc", "run_date": "2026-09-20",
                "setups": [{"name": "claude-code", "harness": "claude-code"},
                           {"name": "codex", "harness": "codex"}],
                "cases": [CASE], "conditions": ["available"], "repetitions": 1,
                "continuation": None, "routing": None,
                "consumer": {"repetitions_per_pair": 1,
                             "producers": ["comparison:%s" % CASE]},
                "timeouts": {"comparison": 60, "continuation": 60, "routing": 60}}
        runner.write_json(path, plan)
        root = os.path.join(self.scratch, "planned")
        # `plan` reads the campaign's stage record; this test plans, it does not stage.
        runner.ensure_dir(root)
        shutil.copy2(runner.Campaign(self.campaign).stage_json,
                     runner.Campaign(root).stage_json)
        got = cli(["plan", "--campaign", root, "--plan", path, "--synthetic"])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        document = parse_stdout(got)
        self.assertEqual(document["counts"]["consumer"], 2)
        minted = runner.read_json(os.path.join(root, "campaign.json"))["consumer_order"]
        self.assertEqual(sorted(t for rows in minted.values() for t in rows),
                         ["consumer-claude-code-to-codex-%s-r1" % CASE,
                          "consumer-codex-to-claude-code-%s-r1" % CASE])

    def test_an_empty_consumer_object_is_not_the_same_as_false(self):
        """`{}` is the all-kinds form; only `false` mints none, and `{}` is falsy in Python."""
        path = os.path.join(self.scratch, "empty-consumer.json")
        base = {"plan_version": 1, "campaign_id": "batchc2", "run_date": "2026-09-20",
                "setups": [{"name": "claude-code", "harness": "claude-code"},
                           {"name": "codex", "harness": "codex"}],
                "cases": [CASE], "conditions": ["available"], "repetitions": 1,
                "continuation": None, "routing": None,
                "timeouts": {"comparison": 60, "continuation": 60, "routing": 60}}
        for value, wanted in (({}, 2), (False, 0)):
            plan = dict(base, consumer=value)
            runner.write_json(path, plan)
            root = os.path.join(self.scratch, "planned-%s" % wanted)
            runner.ensure_dir(root)
            shutil.copy2(runner.Campaign(self.campaign).stage_json,
                         runner.Campaign(root).stage_json)
            got = cli(["plan", "--campaign", root, "--plan", path, "--synthetic"])
            self.assertEqual(got.returncode, 0, got.stderr[-2000:])
            self.assertEqual(parse_stdout(got)["counts"]["consumer"], wanted, value)


# ------------------------------------------------------------- 8. which producer is consumed


class ProducerSelection(RunnerCase):
    setups = ("claude-code", "codex")

    def place(self, tid, kind, case=CASE, status="complete", result=None, setup="codex"):
        campaign = runner.Campaign(self.campaign)
        directory = campaign.trial_dir(tid)
        runner.ensure_dir(directory)
        runner.write_json(os.path.join(directory, "command.json"),
                          {"setup": setup, "condition": "available", "kind": kind,
                           "case": case, "status": status})
        if result is not None:
            runner.write_json(os.path.join(directory, "result.json"), result)
        return directory

    def test_the_wanted_kind_selects_the_right_record(self):
        complete = {"status": "completed", "items": []}
        self.place("codex-%s-available-r1" % CASE, "comparison", result=complete)
        self.place("cont-codex-F3-02-mixed-two-items-handoff-r1", "continuation:handoff",
                   case="F3-02-mixed-two-items", result=complete)
        self.place("cont-codex-F3-02-mixed-two-items-compaction-r1",
                   "continuation:compaction", case="F3-02-mixed-two-items", result=complete)
        campaign = runner.Campaign(self.campaign)
        plan = self.plan_document
        self.assertEqual(
            runner.producer_record_for(campaign, plan, "codex",
                                       kind="continuation:handoff")["trial"],
            "cont-codex-F3-02-mixed-two-items-handoff-r1")
        self.assertEqual(
            runner.producer_record_for(campaign, plan, "codex",
                                       kind="comparison:%s" % CASE)["trial"],
            "codex-%s-available-r1" % CASE)

    def test_a_failed_attempt_is_refused_and_the_next_repetition_is_used(self):
        complete = {"status": "completed", "items": []}
        self.place("codex-%s-available-r1" % CASE, "comparison", status="no_result")
        self.place("codex-%s-available-r2" % CASE, "comparison", result=complete)
        chosen = runner.producer_record_for(runner.Campaign(self.campaign),
                                            self.plan_document, "codex",
                                            kind="comparison:%s" % CASE)
        self.assertEqual(chosen["trial"], "codex-%s-available-r2" % CASE)
        self.assertEqual([row["trial"] for row in chosen["refused"]],
                         ["codex-%s-available-r1" % CASE])
        self.assertIn("no_result", chosen["refused"][0]["why"])
        self.assertIn("earliest repetition first", chosen["why"])

    def test_an_empty_attempt_is_refused(self):
        self.place("codex-%s-available-r1" % CASE, "comparison", result={})
        self.place("codex-%s-available-r2" % CASE, "comparison",
                   result={"status": "completed", "items": []})
        chosen = runner.producer_record_for(runner.Campaign(self.campaign),
                                            self.plan_document, "codex",
                                            kind="comparison:%s" % CASE)
        self.assertEqual(chosen["trial"], "codex-%s-available-r2" % CASE)
        self.assertIn("neither items nor a status", chosen["refused"][0]["why"])

    def test_repetition_one_wins_over_a_later_one(self):
        complete = {"status": "completed", "items": []}
        self.place("codex-%s-available-r1" % CASE, "comparison", result=complete)
        self.place("codex-%s-available-r2" % CASE, "comparison", result=complete)
        chosen = runner.producer_record_for(runner.Campaign(self.campaign),
                                            self.plan_document, "codex",
                                            kind="comparison:%s" % CASE)
        self.assertEqual(chosen["trial"], "codex-%s-available-r1" % CASE)
        self.assertEqual([row["trial"] for row in chosen["considered"]],
                         ["codex-%s-available-r1" % CASE, "codex-%s-available-r2" % CASE])

    def test_every_attempt_refused_is_a_missing_record_naming_why(self):
        self.place("codex-%s-available-r1" % CASE, "comparison", status="timed_out")
        with self.assertRaises(runner.Missing) as caught:
            runner.producer_record_for(runner.Campaign(self.campaign), self.plan_document,
                                       "codex", kind="comparison:%s" % CASE)
        self.assertIn("timed_out", str(caught.exception))
        self.assertIn("1 attempt(s) were refused", str(caught.exception))


# --------------------------------------------------------------- 9. grading is deferred


class DeferredGrading(RunnerCase):
    """Gap 7: "Delay all consumer grading and enforce record separation"."""

    setups = ("claude-code", "codex")

    def producer_trial(self, setup="claude-code"):
        tid = runner.trial_id(setup, CASE, "available", 1)
        got = cli(["run", "--campaign", self.campaign, tid,
                   "--fake-launcher", self.fake_launcher(setup)])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        return tid

    def test_a_lone_consumer_run_leaves_the_attempt_ungraded_and_says_so(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        self.assertIsNone(document["consumer_grade"])
        self.assertFalse(document["graded"])
        self.assertTrue(document["grading"]["deferred"])
        self.assertIn("third phase", document["grading"]["why"])
        self.assertFalse(os.path.isfile(os.path.join(document["record"],
                                                     "consumer-grade.json")))
        self.assertEqual(
            [p for p in os.listdir(document["record"]) if p.startswith("consumer-grade")],
            [])

    def test_the_ledger_row_is_pending_until_the_backfill(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        campaign = runner.Campaign(self.campaign)
        rows = [r for r in runner.jsonl_lines(campaign.trials_jsonl) if r["id"] == tid]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["graded_ok"])
        self.assertTrue(rows[0]["grade_pending"])
        graded = cli(["consumer", "--campaign", self.campaign, "--regrade", "--all"])
        self.assertEqual(graded.returncode, 0, graded.stderr[-2000:])
        self.assertTrue(parse_stdout(graded)["first_grades"])
        rows = [r for r in runner.jsonl_lines(campaign.trials_jsonl) if r["id"] == tid]
        self.assertEqual(len(rows), 2)
        self.assertIn("backfill", rows[1])
        self.assertIsNotNone(rows[1]["graded_ok"])
        # the two rows are ONE attempt for every reader
        collapsed = [r for r in runner.ledger_rows(campaign) if r["id"] == tid]
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0]["graded_ok"],
                         runner.read_json(os.path.join(document["record"],
                                                       "consumer-grade.json"))["ok"])
        self.assertEqual(collapsed[0]["status"], "complete")
        self.assertEqual(collapsed[0]["_rows"], 2)

    def test_the_report_counts_the_backfilled_attempt_once(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        cli(["consumer", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("codex")])
        before = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertEqual(before["consumer_grades_read"], 0)
        cli(["consumer", "--campaign", self.campaign, "--regrade", "--all"])
        after = parse_stdout(cli(["report", "--campaign", self.campaign]))
        # the back-fill row added a grade, not an attempt
        self.assertEqual(after["trials_seen"], before["trials_seen"])
        self.assertEqual(after["attempts_seen"], before["attempts_seen"])
        self.assertEqual(after["consumer_grades_read"], 1)

    def test_a_first_grade_is_never_replaced(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        cli(["consumer", "--campaign", self.campaign, tid,
             "--fake-launcher", self.fake_launcher("codex")])
        self.assertEqual(cli(["consumer", "--campaign", self.campaign,
                              "--regrade", "--all"]).returncode, 0)
        again = cli(["consumer", "--campaign", self.campaign, "--regrade", "--all"])
        self.assertEqual(again.returncode, 2, again.stdout[-400:])
        self.assertIn("--revision", again.stderr)
        derived = cli(["consumer", "--campaign", self.campaign, "--regrade", "--all",
                       "--revision", "batch-c"])
        self.assertEqual(derived.returncode, 0, derived.stderr[-2000:])
        record = runner.Campaign(self.campaign).trial_dir(tid)
        self.assertTrue(os.path.isfile(os.path.join(record, "consumer-grade.json")))
        self.assertTrue(os.path.isfile(os.path.join(record,
                                                    "consumer-grade.batch-c.json")))

    def test_the_grade_carries_the_cross_trial_witness(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        cli(["consumer", "--campaign", self.campaign, "--regrade", "--all"])
        grade = runner.read_json(os.path.join(document["record"], "consumer-grade.json"))
        self.assertEqual(grade["kind"], "consumer")
        self.assertEqual(grade["trial"], tid)
        self.assertIn("records_reached", grade)
        self.assertTrue(grade["graded_after_every_consumer_session_ended"])

    def test_the_pair_is_retained_in_the_record_by_the_live_path(self):
        self.producer_trial()
        tid = "consumer-claude-code-to-codex-r1"
        document = parse_stdout(cli(["consumer", "--campaign", self.campaign, tid,
                                     "--fake-launcher", self.fake_launcher("codex")]))
        record = document["record"]
        manifest = runner.read_json(os.path.join(record, "pair-manifest.json"))
        self.assertTrue(manifest["copied"])
        self.assertTrue(os.path.isdir(os.path.join(record, "pair")))
        self.assertTrue(manifest["files"])
        self.assertTrue(os.path.isdir(document["pair"]["pair_dir"]),
                        "the pair was moved, not copied")


class TheThirdPhase(RunnerCase):
    """The campaign runs producers, then consumers, then grading, in that order."""

    setups = ("claude-code", "codex")

    def campaign_with_consumers(self):
        self.make_campaign({"cases": [CASE], "conditions": ["available"], "repetitions": 1,
                            "routing": {"entries": [], "repetitions": 1},
                            "continuation": None,
                            "consumer": {"repetitions_per_pair": 1,
                                         "producers": ["comparison:%s" % CASE]}})
        campaign = runner.Campaign(self.campaign)
        document = runner.read_json(campaign.campaign_json)
        document["consumer_order"] = runner.consumer_order(document)
        document["counts"]["consumer"] = sum(len(v) for v
                                             in document["consumer_order"].values())
        document["counts"]["total"] = sum(v for k, v in document["counts"].items()
                                          if k != "total")
        runner.write_json(campaign.campaign_json, document)
        self.plan_document = document
        return campaign

    def test_the_campaign_grades_the_consumers_in_a_third_phase(self):
        campaign = self.campaign_with_consumers()
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--skip-probe-gate", "--reopen-key",
                   "--fake-launcher", self.dispatch_launcher()])
        self.assertEqual(got.returncode, 0, got.stderr[-4000:])
        document = parse_stdout(got)
        self.assertEqual(document["failed"], [])
        grading = document["consumer_grading"]
        self.assertEqual(grading["errors"], [])
        self.assertEqual(grading["records"], 2)
        self.assertEqual(grading["graded"], 2)

        # the log says the three phases happened in order and the grading came last
        log = runner.read_text(campaign.log, "")
        consumer_phase = log.index("the consumer phase begins")
        grading_phase = log.index("the grading phase begins")
        self.assertLess(consumer_phase, grading_phase)
        self.assertLess(grading_phase, log.index("the grading phase ended"))

        # NO consumer grade existed while any consumer session could still be running: every
        # grade file is younger than every consumer record's own command.json
        records = [row[2] for row in runner.consumer_records(campaign)]
        self.assertEqual(len(records), 2)
        last_session = max(os.path.getmtime(os.path.join(r, "command.json"))
                           for r in records)
        for record in records:
            grade = os.path.join(record, "consumer-grade.json")
            self.assertTrue(os.path.isfile(grade), record)
            self.assertGreaterEqual(os.path.getmtime(grade), last_session)
            self.assertTrue(runner.read_json(grade)
                            ["graded_after_every_consumer_session_ended"])

        # the back-fill landed and the ledger still reads one row per attempt
        rows = [r for r in runner.ledger_rows(campaign) if r["id"].startswith("consumer-")]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIsNotNone(row["graded_ok"])
            self.assertFalse(row["grade_pending"])

        # and the report joins on the same attempts, once each
        report = parse_stdout(cli(["report", "--campaign", self.campaign]))
        self.assertEqual(report["trials_seen"], len(runner.ledger_rows(campaign)))
        self.assertEqual(report["attempts_seen"], report["trials_seen"])
        self.assertEqual(report["consumer_grades_read"], 2)

    def test_the_consumer_rows_all_run_after_every_producer_row(self):
        campaign = self.campaign_with_consumers()
        got = cli(["campaign", "start", "--campaign", self.campaign, "--foreground",
                   "--skip-probe-gate", "--reopen-key",
                   "--fake-launcher", self.dispatch_launcher()])
        self.assertEqual(got.returncode, 0, got.stderr[-4000:])
        starts = {}
        for row in runner.ledger_rows(campaign):
            command = runner.read_json(os.path.join(row["record"], "command.json"))
            if command.get("kind") == "routing":
                continue
            starts[row["id"]] = os.path.getmtime(os.path.join(row["record"],
                                                              "command.json"))
            self.assertIn(command["kind"], ("comparison", "consumer"))
        producers = [t for t in starts if not t.startswith("consumer-")]
        consumers = [t for t in starts if t.startswith("consumer-")]
        self.assertTrue(producers and consumers)
        self.assertLessEqual(max(starts[t] for t in producers),
                             min(starts[t] for t in consumers))


if __name__ == "__main__":
    unittest.main()
