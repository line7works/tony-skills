"""The bench-rig turn counter."""


class Counter(object):
    def __init__(self):
        self.turns = 0

    def turn(self):
        self.turns += 1
        return self.turns

    def reset(self):
        self.turns = 0
