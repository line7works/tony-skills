"""Part J6: a step the harness cannot do adds no program to what the look must find (contract E16-14; the frame's RUN-5,
RUN-7 and OP-8).

The live run's defect: a sunrise look whose capabilities named `memory stores` only ended `refused`, the program
`sun-adapter` being on no folder of the search list, though only SR13-canary (capability `canary`) uses it. Here each
fixture machine's search list holds no `sun-adapter`: the rise lane's own wrapper of it is taken out, and the set lane's
adapter declaration is installed as it ships (its tool `sun-adapter`, where the set lane's tests rename it `fixture-...`).
"""
import os

import harness
import test_lane_rise as rise
import test_lane_set_lib as setlib


def read(path):
    with open(path) as fh:
        return fh.read()


def form(result, prefix):
    found = [p for p in result.doc.get("forms") or [] if os.path.basename(p).startswith(prefix)]
    return read(found[-1]) if found else ""


def no_adapter_for_sunrise(m):
    """The rise lane's fixture machine, its wrapper of `sun-adapter` taken out: no folder of the search list holds one."""
    rise.machine_for_sunrise(m)
    os.remove(os.path.join(m.root, "programs-" + m.seed, "sun-adapter"))
    rise.install(m)
    return m


def no_adapter_for_sunset(case, label):
    """The set lane's fixture machine, its adapter declared as it ships (`sun-adapter`), which no folder holds."""
    m = setlib.machine(case, label)
    decls = setlib.providers()
    decls["adapter"] = setlib.shipped_providers()["adapter"]
    setlib.install(m, decls=decls)
    return m


class Sunrise(harness.Case):
    def test_SR13_canary_E16_14_OP8_RUN5_without_canary_and_no_adapter_the_look_previews_and_the_go_completes(self):
        m = no_adapter_for_sunrise(self.machine("j6rise", "j6rise"))
        caps = ("memory stores",)
        looked = m.look(also=rise.ALSO, inputs=rise.sunrise_inputs(m), caps=caps)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("[SR13-canary] check: the canary: a fresh session quotes AGENTS.md's first line; the check could not be "
                      "made on this harness", form(looked, "preview-"))
        went = m.go(looked, also=rise.ALSO, caps=caps)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(m.statuses(looked.doc["run"])["SR13-canary"], "unavailable")
        self.assertIn("[SR13-canary] the check could not be made on this harness: kit 2/2, canary", form(went, "summary-"))
        self.assertEqual(m.calls("sun-adapter"), [])

    def test_SR13_canary_E16_14_RUN5_with_canary_declared_and_no_adapter_the_look_still_refuses_naming_the_program(self):
        m = no_adapter_for_sunrise(self.machine("j6can", "j6can"))
        looked = m.look(also=rise.ALSO, inputs=rise.sunrise_inputs(m), caps=rise.CAPS)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertEqual(looked.code, 10, looked.text)
        self.assertIn("the program sun-adapter is in no folder of the search list", looked.text)


class Sunset(harness.Case):
    def test_T10c_E16_14_OP8_RUN5_without_routines_and_no_adapter_the_look_previews_and_the_go_completes(self):
        m = no_adapter_for_sunset(self, "j6set")
        caps = ("memory stores",)
        looked = setlib.look(m, caps=caps)
        self.assertEqual(looked.ending, "preview", looked.text)
        self.assertIn("not applicable (not available on this harness)", form(looked, "preview-"))
        went = setlib.go(m, looked, caps=caps)
        self.assertEqual(went.ending, "complete", went.text)
        self.assertEqual(setlib.calls(m, "sun-adapter"), [])

    def test_T10c_E16_14_RUN5_with_routines_declared_and_no_adapter_the_look_still_refuses_naming_the_program(self):
        m = no_adapter_for_sunset(self, "j6setr")
        looked = setlib.look(m, caps=setlib.CAPS)
        self.assertEqual(looked.ending, "refused", looked.text)
        self.assertEqual(looked.code, 10, looked.text)
        self.assertIn("the program sun-adapter is in no folder of the search list", looked.text)


if __name__ == "__main__":
    import unittest
    unittest.main()
