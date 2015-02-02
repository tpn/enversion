class DummyStream:
    def __nonzero__(self):
        return False
    def write(self, data):
        pass
stream = DummyStream()

def dot(d=None):
    if not d:
        d = '.'
    stream.write(d)

def dash():
    dot('-')
